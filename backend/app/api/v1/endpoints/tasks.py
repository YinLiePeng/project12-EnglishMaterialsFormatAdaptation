from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_, or_
from sqlalchemy.sql import Select
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
import copy
from app.core.database import get_db
from app.models.task import Task
from app.services.processor import document_processor
from app.services.structure_formatter import structure_formatter
from app.services.docx import DocxParser, DocxGenerator
from app.core.presets.styles import get_preset_style, get_style_mapping

router = APIRouter()


@router.get("/{task_id}")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    """查询任务状态"""
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "任务不存在"}
        )

    # 解析结构分析数据
    structure_analysis = None
    if task.structure_analysis:
        try:
            structure_analysis = json.loads(task.structure_analysis)
        except json.JSONDecodeError:
            structure_analysis = None

    return {
        "code": 0,
        "data": {
            "task_id": task.task_id,
            "status": task.status,
            "layout_mode": task.layout_mode,
            "preset_style": task.preset_style,
            "input_filename": task.input_filename,
            "output_filename": task.output_filename,
            "processing_time": task.processing_time,
            "error_message": task.error_message,
            "error_code": task.error_code,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat()
            if task.completed_at
            else None,
            "structure_analysis": structure_analysis,
        },
    }


@router.get("/{task_id}/download")
async def download_result(task_id: str, db: AsyncSession = Depends(get_db)):
    """下载处理结果"""
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "任务不存在"}
        )

    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "message": f"任务状态为{task.status}，无法下载"},
        )

    if not task.output_file_path or not Path(task.output_file_path).exists():
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "输出文件不存在或已过期"}
        )

    return FileResponse(
        path=task.output_file_path,
        filename=task.output_filename or "output.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.delete("/{task_id}")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """取消任务"""
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "任务不存在"}
        )

    if task.status in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "message": f"任务已{task.status}，无法取消"},
        )

    task.status = "failed"
    task.error_message = "任务已取消"
    await db.commit()

    return {"code": 0, "message": "任务已取消"}


@router.get("")
async def list_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    status: Optional[str] = Query(None, description="任务状态"),
    filename: Optional[str] = Query(None, description="文件名（模糊搜索）"),
    layout_mode: Optional[str] = Query(None, description="排版模式"),
    start_date: Optional[str] = Query(None, description="开始日期（YYYY-MM-DD）"),
    end_date: Optional[str] = Query(None, description="结束日期（YYYY-MM-DD）"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向（asc/desc）"),
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表（支持多条件筛选和排序）"""
    query = select(Task)

    # 筛选条件
    conditions = []

    if status:
        conditions.append(Task.status == status)

    if filename:
        conditions.append(Task.input_filename.like(f"%{filename}%"))

    if layout_mode:
        conditions.append(Task.layout_mode == layout_mode)

    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            conditions.append(Task.created_at >= start_datetime)
        except ValueError:
            pass

    if end_date:
        try:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            conditions.append(Task.created_at < end_datetime)
        except ValueError:
            pass

    if conditions:
        query = query.where(and_(*conditions))

    # 排序
    sort_column = getattr(Task, sort_by, Task.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # 获取总数
    count_query = select(func.count(Task.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "status": task.status,
                    "layout_mode": task.layout_mode,
                    "preset_style": task.preset_style,
                    "input_filename": task.input_filename,
                    "output_filename": task.output_filename,
                    "processing_time": task.processing_time,
                    "error_message": task.error_message,
                    "error_code": task.error_code,
                    "created_at": task.created_at.isoformat()
                    if task.created_at
                    else None,
                    "started_at": task.started_at.isoformat()
                    if task.started_at
                    else None,
                    "completed_at": task.completed_at.isoformat()
                    if task.completed_at
                    else None,
                }
                for task in tasks
            ],
        },
    }


@router.post("/delete-batch")
async def delete_tasks_batch(
    task_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """批量删除任务（支持删除所有状态的任务）

    Args:
        task_ids: 任务ID列表

    Returns:
        删除结果统计
    """
    if not task_ids:
        raise HTTPException(
            status_code=400, detail={"code": 400, "message": "任务ID列表不能为空"}
        )

    # 查询所有任务
    result = await db.execute(select(Task).where(Task.task_id.in_(task_ids)))
    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "未找到任何任务"}
        )

    # 删除文件
    deleted_files = 0
    for task in tasks:
        # 删除输入文件
        if task.input_file_path and Path(task.input_file_path).exists():
            try:
                os.remove(task.input_file_path)
                deleted_files += 1
            except Exception:
                pass

        # 删除输出文件
        if task.output_file_path and Path(task.output_file_path).exists():
            try:
                os.remove(task.output_file_path)
                deleted_files += 1
            except Exception:
                pass

    # 从数据库删除任务
    await db.execute(delete(Task).where(Task.task_id.in_(task_ids)))
    await db.commit()

    return {
        "code": 0,
        "message": f"成功删除{len(tasks)}个任务，清理{deleted_files}个文件",
        "data": {"deleted_count": len(tasks), "deleted_files": deleted_files},
    }


@router.get("/statistics/summary")
async def get_statistics(
    db: AsyncSession = Depends(get_db),
):
    """获取任务统计数据

    Returns:
        包含任务统计数据的字典
    """
    # 总任务数
    total_result = await db.execute(select(func.count(Task.id)))
    total = total_result.scalar()

    # 各状态任务数
    status_stats = {}
    for status in ["pending", "processing", "completed", "failed"]:
        result = await db.execute(
            select(func.count(Task.id)).where(Task.status == status)
        )
        status_stats[status] = result.scalar()

    # 今日新增任务
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(Task.id)).where(Task.created_at >= today)
    )
    today_count = today_result.scalar()

    # 完成成功率
    completed_count = status_stats.get("completed", 0)
    failed_count = status_stats.get("failed", 0)
    total_finished = completed_count + failed_count
    success_rate = (completed_count / total_finished * 100) if total_finished > 0 else 0

    # 平均处理时间（仅计算已完成的任务）
    avg_time_result = await db.execute(
        select(func.avg(Task.processing_time)).where(
            Task.status == "completed", Task.processing_time.isnot(None)
        )
    )
    avg_processing_time = avg_time_result.scalar()

    # 本周新增任务
    week_ago = datetime.now() - timedelta(days=7)
    week_result = await db.execute(
        select(func.count(Task.id)).where(Task.created_at >= week_ago)
    )
    week_count = week_result.scalar()

    return {
        "code": 0,
        "data": {
            "total": total,
            "status_stats": status_stats,
            "today_count": today_count,
            "week_count": week_count,
            "success_rate": round(success_rate, 2),
            "avg_processing_time": round(avg_processing_time, 2)
            if avg_processing_time
            else 0,
        },
    }


# ==================== 智能修正功能端点 ====================


@router.post("/{task_id}/quick-correction")
async def quick_correction(
    task_id: str,
    request_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """快速修正：直接更新用户指定的段落类型

    Args:
        task_id: 任务ID
        request_data: 包含paragraph_updates和user_feedback的字典

    Returns:
        更新后的结构分析数据
    """
    # 获取任务
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "任务不存在"}
        )

    if not task.structure_analysis:
        raise HTTPException(
            status_code=400, detail={"code": 400, "message": "没有结构分析数据"}
        )

    # 解析当前结构分析
    structure = json.loads(task.structure_analysis)
    updates = request_data.get("paragraph_updates", [])

    if not updates:
        raise HTTPException(
            status_code=400, detail={"code": 400, "message": "没有提供更新内容"}
        )

    # 内容类型名称映射
    CONTENT_TYPE_NAMES = {
        "title": "主标题",
        "heading": "子标题",
        "question_number": "题号",
        "option": "选项",
        "body": "正文",
        "answer": "答案",
        "analysis": "解析",
    }

    # 更新段落类型
    update_map = {u["index"]: u["content_type"] for u in updates}
    updated_count = 0

    for para in structure["paragraphs"]:
        if para["index"] in update_map:
            old_type = para["content_type"]
            new_type = update_map[para["index"]]

            # 更新类型
            para["content_type"] = new_type
            para["content_type_name"] = CONTENT_TYPE_NAMES.get(new_type, new_type)
            para["confidence"] = 1.0
            para["reason"] = f"用户手动修正（从{old_type}改为{new_type}）"

            # 更新applied_style
            style_key = document_processor._content_type_to_style_key(new_type)
            # 获取样式映射
            preset = get_preset_style(task.preset_style or "universal")
            style_mapping = get_style_mapping(preset)
            style_def = style_mapping.get(style_key, {})
            para["applied_style"] = structure_formatter._format_style_details(
                style_key, style_def
            )

            updated_count += 1

    # 重新计算整体置信度
    structure["overall_confidence"] = structure_formatter._calculate_overall_confidence(
        structure["paragraphs"]
    )

    # 保存到数据库
    task.structure_analysis = json.dumps(structure, ensure_ascii=False)
    await db.commit()

    return {
        "code": 0,
        "message": f"修正成功，已更新{updated_count}个段落",
        "data": {
            "updated_count": updated_count,
            "structure_analysis": structure,
        },
    }


@router.post("/{task_id}/ai-recognize")
async def ai_recognize(
    task_id: str,
    request_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """AI重新识别：基于用户意见重新运行结构识别

    Args:
        task_id: 任务ID
        request_data: 包含user_feedback和mode的字典

    Returns:
        preview模式: changes列表 + 新的structure_analysis
        apply模式: 应用结果 + 新的structure_analysis
    """
    # 获取任务
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "任务不存在"}
        )

    if task.enable_llm != 1:
        raise HTTPException(
            status_code=400, detail={"code": 400, "message": "该任务未启用AI识别功能"}
        )

    user_feedback = request_data.get("user_feedback", "")
    mode = request_data.get("mode", "preview")

    # 重新解析文档
    try:
        parser = DocxParser(task.input_file_path)
        elements = parser.extract_content()
        para_dicts = document_processor._extract_para_dicts(elements)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail={"code": 500, "message": f"文档解析失败: {str(e)}"}
        )

    # 构建增强的Prompt
    base_prompt = """请基于以下段落识别文档结构，特别关注用户反馈的内容。"""
    if user_feedback:
        enhanced_prompt = f"""{base_prompt}

【用户反馈】
{user_feedback}

请基于用户反馈进行识别，特别注意用户提到的段落或模式。"""
    else:
        enhanced_prompt = base_prompt

    # 调用混合识别器（强制使用LLM）
    try:
        from app.services.llm.hybrid_recognizer import hybrid_recognizer

        structures = await hybrid_recognizer.recognize(
            para_dicts, use_llm=True, custom_prompt=enhanced_prompt
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail={"code": 500, "message": f"AI识别失败: {str(e)}"}
        )

    # 格式化结果
    style_mapping = get_style_mapping(
        get_preset_style(task.preset_style or "universal")
    )

    # 提取段落信息
    paragraphs = []
    from app.services.docx.parser import ParagraphInfo, FontInfo, ParagraphFormat

    for i, pd in enumerate(para_dicts):
        paragraphs.append(
            ParagraphInfo(
                index=i,
                text=pd.get("text", ""),
                style_name="Normal",
                font=FontInfo(
                    size=pd.get("font_size", 12.0), bold=pd.get("font_bold", False)
                ),
                format=ParagraphFormat(alignment=pd.get("alignment", "left")),
            )
        )

    formatted = structure_formatter.format_rule_engine_results(
        structures, style_mapping, paragraphs
    )
    formatted["method"] = "llm"

    if mode == "preview":
        # 预览模式：对比变化
        current_structure = json.loads(task.structure_analysis)
        changes = structure_formatter.compare_structures(current_structure, formatted)

        return {
            "code": 0,
            "message": f"识别完成，{len(changes)}处变化，请确认",
            "data": {
                "mode": "preview",
                "changes": changes,
                "structure_analysis": formatted,  # 预览结果，未保存
            },
        }
    else:
        # 应用模式：直接保存
        task.structure_analysis = json.dumps(formatted, ensure_ascii=False)
        await db.commit()

        return {
            "code": 0,
            "message": "已应用AI识别结果",
            "data": {
                "mode": "apply",
                "applied_count": len(formatted["paragraphs"]),
                "structure_analysis": formatted,
            },
        }


@router.post("/{task_id}/regenerate")
async def regenerate_document(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """使用当前structure_analysis重新生成文档"""
    # 获取任务
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "任务不存在"}
        )

    if not task.structure_analysis:
        raise HTTPException(
            status_code=400, detail={"code": 400, "message": "没有结构分析数据"}
        )

    # 解析结构分析
    structure = json.loads(task.structure_analysis)

    # 重新生成文档
    try:
        # 解析原始文档
        parser = DocxParser(task.input_file_path)
        elements = parser.extract_content()

        # 构建新的style_keys
        style_keys = {}
        for para_info in structure["paragraphs"]:
            style_key = document_processor._content_type_to_style_key(
                para_info["content_type"]
            )
            style_keys[para_info["index"]] = style_key

        # 获取样式映射
        preset = get_preset_style(task.preset_style or "universal")
        style_mapping = get_style_mapping(preset)

        # 生成新文档
        output_path = document_processor._get_output_path(
            task.input_file_path, task.input_filename
        )

        generator = DocxGenerator()
        generator.generate_from_elements(elements, style_mapping, style_keys)
        generator.save(output_path)

        # 更新任务
        task.output_file_path = output_path
        task.output_filename = os.path.basename(output_path)
        await db.commit()

        return {
            "code": 0,
            "message": "文档重新生成成功",
            "data": {
                "output_filename": task.output_filename,
                "download_url": f"/api/v1/tasks/{task_id}/download",
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail={"code": 500, "message": f"重新生成失败: {str(e)}"}
        )
