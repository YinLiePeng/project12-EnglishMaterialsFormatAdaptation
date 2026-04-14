import uuid
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Form,
    BackgroundTasks,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.core.config import settings
from app.core.database import get_db
from app.models.task import Task
from app.services import document_processor, testcase_service

router = APIRouter()


@router.post("")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    template: UploadFile = File(None),
    layout_mode: str = Form("none"),
    preset_style: str = Form("universal"),
    enable_cleaning: bool = Form(False),
    enable_correction: bool = Form(False),
    use_llm: bool = Form(False),
    marker_position: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """上传文件并创建处理任务

    支持上传原始资料(DOCX)和可选的模板文件(DOCX)
    """
    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 验证文件类型
    allowed_extensions = {".docx", ".pdf"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail={
                "code": 1002,
                "message": f"不支持的文件格式：{file_ext}，请上传DOCX文件",
            },
        )

    # 读取文件内容
    file_content = await file.read()

    # 验证文件大小
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail={
                "code": 1003,
                "message": f"文件大小超过限制(最大{settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB)",
            },
        )

    # PDF专用验证：页数限制 + 加密检测
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext == ".pdf":
        try:
            import fitz
            import io

            doc = fitz.open(stream=file_content, filetype="pdf")
            if doc.is_encrypted:
                doc.close()
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 2001,
                        "message": "PDF文件已加密，请解除密码保护后重新上传",
                        "suggestion": "请使用PDF工具打开文件，取消密码保护后重新上传",
                    },
                )
            page_count = len(doc)
            doc.close()
            if page_count > settings.PDF_MAX_PAGES:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 1005,
                        "message": f"PDF页数超过限制（最大{settings.PDF_MAX_PAGES}页，当前{page_count}页）",
                    },
                )
        except HTTPException:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "encrypt" in error_msg or "password" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 2001,
                        "message": "PDF文件已加密，请解除密码保护后重新上传",
                    },
                )

    # 保存文件到临时目录
    temp_dir = Path(settings.TEMP_STORAGE_PATH)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 生成安全文件名
    safe_filename = f"{task_id}{file_ext}"
    file_path = temp_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(file_content)

    # 处理模板文件(如果有)
    template_path = None
    template_filename = None
    if template:
        template_filename = template.filename
        template_content = await template.read()
        template_ext = (
            Path(template.filename).suffix.lower() if template.filename else ".docx"
        )
        template_safe_name = f"{task_id}_template{template_ext}"
        template_path = temp_dir / template_safe_name
        with open(template_path, "wb") as f:
            f.write(template_content)

    # 创建任务记录
    task = Task(
        task_id=task_id,
        status="pending",
        task_type="format_adaptation",
        input_filename=file.filename,
        input_file_path=str(file_path),
        input_file_size=len(file_content),
        input_expire_at=datetime.now() + timedelta(hours=settings.TEMP_EXPIRE_HOURS),
        template_filename=template_filename,
        template_file_path=str(template_path) if template_path else None,
        layout_mode=layout_mode,
        preset_style=preset_style,
        enable_cleaning=1 if enable_cleaning else 0,
        enable_correction=1 if enable_correction else 0,
        enable_llm=1 if use_llm else 0,
        marker_position=marker_position,
    )

    db.add(task)
    await db.commit()

    # 启动后台处理任务（启用LLM时由SSE端点驱动，不在这里启动）
    if not use_llm:
        background_tasks.add_task(
            process_task_background,
            task_id=task_id,
            input_file_path=str(file_path),
            layout_mode=layout_mode,
            preset_style=preset_style,
            template_file_path=str(template_path) if template_path else None,
            enable_cleaning=enable_cleaning,
            enable_correction=enable_correction,
            use_llm=use_llm,
            marker_position=marker_position,
        )

    pdf_detection = None
    if file_ext == ".pdf":
        try:
            from app.services.pdf import PDFParser, detect_pdf_type

            with PDFParser(str(file_path)) as pdf_p:
                detection_result = detect_pdf_type(pdf_p)
            pdf_detection = {
                "type": detection_result.pdf_type.value,
                "type_name": detection_result.summary.get("type_name", ""),
                "confidence": detection_result.confidence,
                "processing_hint": detection_result.summary.get("processing_hint", ""),
                "total_pages": detection_result.summary.get("total_pages", 0),
            }
        except Exception:
            pass

    result_data = {
        "task_id": task_id,
        "input_filename": file.filename,
        "template_filename": template_filename,
        "file_size": len(file_content),
        "layout_mode": layout_mode,
        "preset_style": preset_style,
        "use_llm": use_llm,
        "is_pdf": file_ext == ".pdf",
    }
    if pdf_detection:
        result_data["pdf_detection"] = pdf_detection

    return {
        "code": 0,
        "message": "上传成功，任务已创建",
        "data": result_data,
    }


async def process_task_background(
    task_id: str,
    input_file_path: str,
    layout_mode: str,
    preset_style: str,
    template_file_path: Optional[str] = None,
    enable_cleaning: bool = False,
    enable_correction: bool = False,
    use_llm: bool = False,
    marker_position: Optional[str] = None,
):
    """后台处理任务"""
    from app.core.database import AsyncSessionLocal
    from app.services.cleaner import content_cleaner
    from app.services.correction import content_corrector
    from app.services.revision import TrackedDocument

    async with AsyncSessionLocal() as db:
        # 更新任务状态
        result = await db.execute(select(Task).where(Task.task_id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            return

        # 更新状态为处理中
        task.status = "processing"
        task.started_at = datetime.now()
        await db.commit()

        try:
            file_ext = Path(input_file_path).suffix.lower()
            pre_extracted_elements = None

            if file_ext == ".pdf":
                from app.services.pdf import PDFParser, detect_pdf_type

                pdf_parser = PDFParser(input_file_path)
                detection_result = detect_pdf_type(pdf_parser)

                if detection_result.pdf_type.value == "scanned":
                    pdf_parser.close()
                    from app.services.ocr.pipeline import process_scanned_pdf

                    pre_extracted_elements = await process_scanned_pdf(
                        input_file_path, detection_result
                    )
                    if not pre_extracted_elements:
                        raise ValueError(
                            "扫描版PDF需要OCR识别，但OCR服务返回了空结果。"
                            "请确认LLM API密钥配置正确（LLM_API_KEY），"
                            "或尝试上传原生可复制PDF。"
                        )
                elif detection_result.pdf_type.value == "mixed":
                    from app.services.ocr.pipeline import process_scanned_pdf

                    ocr_elements = await process_scanned_pdf(
                        input_file_path, detection_result
                    )
                    native_elements = pdf_parser.convert_to_content_elements()
                    pdf_parser.close()

                    native_set = set()
                    for e in native_elements:
                        if hasattr(e, "paragraph") and e.paragraph:
                            native_set.add(e.paragraph.text[:50])

                    pre_extracted_elements = native_elements[:]
                    for e in ocr_elements:
                        if hasattr(e, "paragraph") and e.paragraph:
                            if e.paragraph.text[:50] not in native_set:
                                pre_extracted_elements.append(e)
                else:
                    pre_extracted_elements = pdf_parser.convert_to_content_elements()
                    pdf_parser.close()

                paragraphs_info = [
                    {
                        "index": i,
                        "text": e.paragraph.text,
                        "font": {
                            "name": e.paragraph.font.name,
                            "size": e.paragraph.font.size,
                            "bold": e.paragraph.font.bold,
                        },
                        "format": {
                            "alignment": e.paragraph.format.alignment,
                        },
                    }
                    for i, e in enumerate(pre_extracted_elements)
                    if e.element_type.value == "paragraph" and e.paragraph
                ]
            else:
                from app.services.docx import DocxParser

                docx_parser = DocxParser(input_file_path)
                paragraphs = docx_parser.extract_paragraphs()
                paragraphs_info = [
                    {
                        "index": p.index,
                        "text": p.text,
                        "font": {
                            "name": p.font.name,
                            "size": p.font.size,
                            "bold": p.font.bold,
                        },
                        "format": {
                            "alignment": p.format.alignment,
                            "line_spacing": p.format.line_spacing,
                        },
                        "level": p.level,
                    }
                    for p in paragraphs
                ]

            # 2. 内容清洗（可选）
            if enable_cleaning:
                from app.services.llm import deepseek_client

                llm_client = deepseek_client if use_llm else None
                clean_results = await content_cleaner.clean_with_llm(
                    paragraphs_info, llm_client
                )
                paragraphs_info = content_cleaner.apply_cleaning(
                    paragraphs_info, clean_results
                )

            # 3. 内容纠错（可选）
            correction_result = None
            if enable_correction:
                from app.services.llm import deepseek_client

                llm_client = deepseek_client if use_llm else None
                correction_result = await content_corrector.correct_with_llm(
                    paragraphs_info, llm_client
                )

            # 4. 格式适配与排版
            result = await document_processor.process_document(
                input_file_path=input_file_path,
                layout_mode=layout_mode,
                preset_style=preset_style,
                template_file_path=template_file_path,
                marker_position_str=marker_position,
                use_llm=use_llm,
                task_id=task_id,
                original_filename=task.input_filename,
                elements=pre_extracted_elements,
            )

            # 5. 应用纠错结果（添加修订和批注）
            if (
                correction_result
                and correction_result.corrections
                and result.get("success")
            ):
                tracked_doc = TrackedDocument(result["output_path"])
                corrections_dict = [
                    {
                        "paragraph_index": c.paragraph_index,
                        "old_text": c.original_text,
                        "new_text": c.corrected_text,
                        "reason": c.reason,
                        "action": c.action.value,
                        "correction_type": c.correction_type.value,
                    }
                    for c in correction_result.corrections
                ]
                tracked_doc.apply_corrections(corrections_dict)
                tracked_doc.save(result["output_path"])

            if result.get("success"):
                # 处理成功
                task.status = "completed"
                task.output_file_path = result["output_path"]
                task.output_filename = Path(result["output_path"]).name
                task.processing_time = round(result.get("processing_time", 0), 1)
                task.output_expire_at = datetime.now() + timedelta(
                    hours=settings.TEMP_EXPIRE_HOURS
                )
            else:
                # 处理失败
                task.status = "failed"
                task.error_message = result.get("message", "处理失败")
                task.error_code = result.get("error_code", "UNKNOWN_ERROR")

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.error_code = "UNKNOWN_ERROR"

        task.completed_at = datetime.now()
        await db.commit()


@router.post("/template-preview")
async def template_preview(template: UploadFile = File(...)):
    """上传空模板并返回可交互的HTML预览（用于标记位选择）

    返回:
        - html: 带data-*属性的HTML预览
        - elements: 模板结构概要
        - auto_detected_area: 自动检测的主内容区
    """
    if not template.filename:
        raise HTTPException(
            status_code=400,
            detail={"code": 1002, "message": "请提供模板文件名"},
        )

    template_ext = Path(template.filename).suffix.lower()
    if template_ext not in {".docx"}:
        raise HTTPException(
            status_code=400,
            detail={
                "code": 1002,
                "message": f"模板仅支持DOCX格式，当前文件: {template_ext}",
            },
        )

    template_content = await template.read()
    if len(template_content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail={"code": 1003, "message": "模板文件大小超过50MB限制"},
        )

    if len(template_content) == 0:
        raise HTTPException(
            status_code=400,
            detail={"code": 1002, "message": "模板文件为空"},
        )

    temp_dir = Path(settings.TEMP_STORAGE_PATH)
    temp_dir.mkdir(parents=True, exist_ok=True)
    preview_id = str(uuid.uuid4())
    temp_path = temp_dir / f"_preview_{preview_id}{template_ext}"

    try:
        with open(temp_path, "wb") as f:
            f.write(template_content)

        try:
            from app.services.docx import DocxParser, docx_html_renderer

            parser = DocxParser(str(temp_path))
            elements = parser.extract_content()
        except Exception as e:
            error_msg = str(e).lower()
            if "encrypted" in error_msg or "password" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 2001,
                        "message": "模板文件已加密，请解除密码保护后重新上传",
                        "suggestion": "请使用Word打开文件，点击「文件」→「信息」→「保护文档」→清除密码",
                    },
                )
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 2002,
                    "message": f"模板文件解析失败: {str(e)[:100]}",
                    "suggestion": "请确认模板是有效的DOCX文件",
                },
            )

        if not elements:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 2003,
                    "message": "模板内容为空或无法解析",
                    "suggestion": "请上传包含内容的模板文件",
                },
            )

        result = docx_html_renderer.render_template_for_marking(elements)
        result["filename"] = template.filename

        return {"code": 0, "data": result}

    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


@router.get("/presets")
async def get_preset_styles():
    """获取预设排版样式列表（包含完整配置）"""
    from app.core.presets.styles import PRESET_STYLES

    preset_list = []
    for style_id, style_config in PRESET_STYLES.items():
        preset_list.append(
            {
                "id": style_id,
                "name": style_config["name"],
                "description": style_config["description"],
                "config": style_config,
            }
        )

    return {"code": 0, "data": preset_list}
