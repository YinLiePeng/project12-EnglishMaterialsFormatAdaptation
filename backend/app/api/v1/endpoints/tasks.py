from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_, or_
from sqlalchemy.sql import Select
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import json
import os
import copy
from app.core.database import get_db
from app.models.task import Task
from app.services.processor import document_processor
from app.services.structure_formatter import structure_formatter

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
