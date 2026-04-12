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
        )

    return {
        "code": 0,
        "message": "上传成功，任务已创建",
        "data": {
            "task_id": task_id,
            "input_filename": file.filename,
            "template_filename": template_filename,
            "file_size": len(file_content),
            "layout_mode": layout_mode,
            "preset_style": preset_style,
            "use_llm": use_llm,
        },
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
            # 1. 解析文档
            from app.services.docx import DocxParser

            file_ext = Path(input_file_path).suffix.lower()

            if file_ext == ".pdf":
                # PDF文件解析
                from app.services.pdf import PDFParser

                pdf_parser = PDFParser(input_file_path)
                paragraphs_info = pdf_parser.convert_to_paragraph_info_list()
            else:
                # DOCX文件解析
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
                use_llm=use_llm,
                task_id=task_id,
                original_filename=task.input_filename,
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
