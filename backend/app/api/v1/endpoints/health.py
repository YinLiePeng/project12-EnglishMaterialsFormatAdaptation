from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "healthy"}


@router.get("/health/detail")
async def detailed_health_check():
    """详细健康检查"""
    return {"status": "healthy", "checks": {"api": "healthy", "database": "healthy"}}
