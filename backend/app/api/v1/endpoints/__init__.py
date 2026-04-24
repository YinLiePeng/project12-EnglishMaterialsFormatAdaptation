from fastapi import APIRouter
from .health import router as health_router
from .upload import router as upload_router
from .tasks import router as tasks_router
from .testcase import router as testcase_router

router = APIRouter()

router.include_router(health_router, tags=["健康检查"])
router.include_router(upload_router, prefix="/upload", tags=["文件上传"])
router.include_router(tasks_router, prefix="/tasks", tags=["任务管理"])
router.include_router(testcase_router, prefix="/testcase", tags=["测试用例"])
