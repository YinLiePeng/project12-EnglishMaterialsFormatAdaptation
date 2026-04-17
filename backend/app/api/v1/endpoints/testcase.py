"""测试用例收集API"""

import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from typing import Optional
from pydantic import BaseModel
from app.core.config import settings
from app.services import testcase_service

router = APIRouter()


class StatusUpdateRequest(BaseModel):
    status: str
    admin_notes: Optional[str] = None


@router.post("/submit")
async def submit_testcase(
    original_file: UploadFile = File(...),
    feedback_description: str = Form(...),
    problem_types: str = Form(...),  # JSON数组字符串
    output_file: UploadFile = File(None),
    contact_info: str = Form(None),
    task_id: str = Form(None),
):
    """提交测试用例反馈"""
    import json

    # 验证原始文件类型
    allowed_extensions = {".docx", ".pdf"}
    file_ext = (
        Path(original_file.filename).suffix.lower() if original_file.filename else ""
    )
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail={"code": 1002, "message": "原始文件格式不支持，请上传DOCX或PDF文件"},
        )

    # 读取原始文件
    original_content = await original_file.read()

    # 保存原始文件
    temp_dir = Path(settings.TEMP_STORAGE_PATH)
    temp_dir.mkdir(parents=True, exist_ok=True)

    original_path = temp_dir / f"testcase_{uuid.uuid4()}{file_ext}"
    with open(original_path, "wb") as f:
        f.write(original_content)

    # 处理输出文件（如果有）
    output_path = None
    output_filename = None
    if output_file:
        output_content = await output_file.read()
        output_filename = output_file.filename
        output_ext = (
            Path(output_filename).suffix.lower() if output_filename else ".docx"
        )
        output_path = temp_dir / f"testcase_output_{uuid.uuid4()}{output_ext}"
        with open(output_path, "wb") as f:
            f.write(output_content)

    # 解析问题类型
    try:
        problem_types_list = json.loads(problem_types)
    except json.JSONDecodeError:
        problem_types_list = [problem_types]

    # 提交测试用例
    result = testcase_service.submit_testcase(
        original_file_path=str(original_path),
        original_filename=original_file.filename,
        feedback_description=feedback_description,
        problem_types=problem_types_list,
        output_file_path=str(output_path) if output_path else None,
        output_filename=output_filename,
        contact_info=contact_info,
        task_id=task_id,
    )

    return {"code": 0, "message": "反馈提交成功，感谢您的帮助！", "data": result}


@router.get("/list")
async def list_testcases(
    page: int = 1, page_size: int = 20, problem_type: str = None, status: str = None
):
    """获取测试用例列表"""
    result = testcase_service.get_testcase_list(
        page=page, page_size=page_size, problem_type=problem_type, status=status
    )

    return {"code": 0, "data": result}


@router.get("/{testcase_id}")
async def get_testcase_detail(testcase_id: str):
    """获取测试用例详情"""
    testcase = testcase_service.get_testcase_detail(testcase_id)

    if not testcase:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "测试用例不存在"}
        )

    return {"code": 0, "data": testcase}


@router.get("/{testcase_id}/original")
async def download_original_file(testcase_id: str):
    """下载测试用例原始文件"""
    file_path = testcase_service.get_testcase_file(testcase_id, "original")

    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "原始文件不存在"}
        )

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.get("/{testcase_id}/output")
async def download_output_file(testcase_id: str):
    """下载测试用例输出文件"""
    file_path = testcase_service.get_testcase_file(testcase_id, "output")

    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "输出文件不存在"}
        )

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.delete("/{testcase_id}")
async def delete_testcase(testcase_id: str):
    """删除测试用例"""
    success = testcase_service.delete_testcase(testcase_id)

    if not success:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "测试用例不存在"}
        )

    return {"code": 0, "message": "测试用例已删除"}


@router.put("/{testcase_id}/status")
async def update_testcase_status(testcase_id: str, body: StatusUpdateRequest):
    """更新测试用例状态"""
    if body.status not in ["待处理", "已处理", "已忽略"]:
        raise HTTPException(
            status_code=400, detail={"code": 400, "message": "无效的状态值"}
        )

    success = testcase_service.update_testcase_status(testcase_id, body.status)

    if not success:
        raise HTTPException(
            status_code=404, detail={"code": 404, "message": "测试用例不存在"}
        )

    return {"code": 0, "message": "状态已更新"}
