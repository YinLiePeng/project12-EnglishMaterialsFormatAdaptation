"""Hybrid Server 管理 API

提供 hybrid server 的状态查询、手动启动/停止等管理功能。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.pdf.hybrid_server import hybrid_server_manager

router = APIRouter()


class HybridStatusResponse(BaseModel):
    status: str
    available: bool
    server_url: str
    error: str | None
    pre_start_enabled: bool


class HybridActionResponse(BaseModel):
    success: bool
    message: str
    status: dict


@router.get("/status", response_model=HybridStatusResponse)
async def get_hybrid_status():
    """获取 Hybrid Server 当前状态"""
    status = hybrid_server_manager.get_status()
    return HybridStatusResponse(
        status=status["status"],
        available=status["available"],
        server_url=status["server_url"],
        error=status["error"],
        pre_start_enabled=status["pre_start_enabled"],
    )


@router.post("/start", response_model=HybridActionResponse)
async def start_hybrid_server():
    """手动启动 Hybrid Server"""
    success = hybrid_server_manager.start()
    status = hybrid_server_manager.get_status()

    if success:
        return HybridActionResponse(
            success=True,
            message="Hybrid server 启动成功",
            status=status,
        )
    else:
        error_msg = status.get("error", "启动失败")
        raise HTTPException(
            status_code=503,
            detail={
                "code": 6001,
                "message": f"Hybrid server 启动失败: {error_msg}",
                "status": status,
            },
        )


@router.post("/stop", response_model=HybridActionResponse)
async def stop_hybrid_server():
    """手动停止 Hybrid Server"""
    hybrid_server_manager.stop()
    status = hybrid_server_manager.get_status()

    return HybridActionResponse(
        success=True,
        message="Hybrid server 已停止",
        status=status,
    )
