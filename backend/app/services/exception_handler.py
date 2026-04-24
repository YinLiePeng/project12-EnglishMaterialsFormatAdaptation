"""异常处理器"""

from enum import Enum
from typing import Dict, Any, Optional


class ExceptionType(Enum):
    """异常类型"""

    # 文件相关
    FILE_FORMAT_UNSUPPORTED = "FILE_FORMAT_UNSUPPORTED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    FILE_ENCRYPTED = "FILE_ENCRYPTED"
    PAGE_LIMIT_EXCEEDED = "PAGE_LIMIT_EXCEEDED"

    # 模板相关
    TEMPLATE_PARSE_FAILED = "TEMPLATE_PARSE_FAILED"
    TEMPLATE_STYLE_MESSY = "TEMPLATE_STYLE_MESSY"
    TEMPLATE_NO_MAIN_AREA = "TEMPLATE_NO_MAIN_AREA"
    MARKER_NOT_INSERTED = "MARKER_NOT_INSERTED"

    # 格式应用相关
    FORMAT_APPLY_FAILED = "FORMAT_APPLY_FAILED"
    CONTENT_OVERFLOW = "CONTENT_OVERFLOW"

    # 未知异常
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class AppException(Exception):
    """应用异常基类"""

    def __init__(
        self,
        exception_type: ExceptionType,
        message: str = "",
        suggestion: str = "",
        error_code: str = "",
    ):
        self.exception_type = exception_type
        self.message = message
        self.suggestion = suggestion
        self.error_code = error_code or exception_type.value
        super().__init__(self.message)


class ExceptionHandler:
    """统一异常处理器"""

    # 异常 -> 用户友好提示 映射
    EXCEPTION_MESSAGES = {
        ExceptionType.FILE_FORMAT_UNSUPPORTED: "不支持的文件格式，请上传DOCX或PDF文件",
        ExceptionType.FILE_TOO_LARGE: "文件大小超过50MB限制，请压缩后重试",
        ExceptionType.FILE_CORRUPTED: "文件已损坏或无法打开，请检查文件完整性",
        ExceptionType.FILE_ENCRYPTED: "文件已加密，请解除密码保护后重新上传",
        ExceptionType.PAGE_LIMIT_EXCEEDED: "文件页数超过限制（DOCX最大30页，PDF最大50页）",
        ExceptionType.TEMPLATE_PARSE_FAILED: "模板文件解析失败，请检查模板格式是否正确",
        ExceptionType.TEMPLATE_STYLE_MESSY: "模板样式层级不规范，可能导致适配效果不佳",
        ExceptionType.TEMPLATE_NO_MAIN_AREA: "无法识别模板的主内容区域",
        ExceptionType.MARKER_NOT_INSERTED: "请先在模板中标记内容插入位置",
        ExceptionType.FORMAT_APPLY_FAILED: "格式应用失败，请尝试使用其他排版模式",
        ExceptionType.CONTENT_OVERFLOW: "内容超出模板空间",
        ExceptionType.UNKNOWN_ERROR: "处理过程中出现未知错误，请重试",
    }

    # 解决建议映射
    EXCEPTION_SUGGESTIONS = {
        ExceptionType.FILE_FORMAT_UNSUPPORTED: "请将文件转换为DOCX或PDF格式后重新上传",
        ExceptionType.FILE_TOO_LARGE: "请压缩文件或将内容拆分为多个文件",
        ExceptionType.FILE_CORRUPTED: "请检查文件是否可以正常打开，或重新下载原始文件",
        ExceptionType.FILE_ENCRYPTED: "请使用Word打开文件，点击「文件」→「信息」→「保护文档」→清除密码",
        ExceptionType.PAGE_LIMIT_EXCEEDED: "请将文件拆分为多个部分处理",
        ExceptionType.TEMPLATE_PARSE_FAILED: "请确认模板是有效的DOCX文件",
        ExceptionType.TEMPLATE_STYLE_MESSY: "建议选择「无模板排版」模式，使用系统预设的标准化排版方案",
        ExceptionType.TEMPLATE_NO_MAIN_AREA: "请确认模板包含可编辑的正文区域",
        ExceptionType.MARKER_NOT_INSERTED: "请在模板中插入 {{CONTENT}} 标记",
        ExceptionType.FORMAT_APPLY_FAILED: "请尝试使用其他排版模式或检查输入文件格式",
        ExceptionType.CONTENT_OVERFLOW: "请尝试调整模板边距或减少内容",
        ExceptionType.UNKNOWN_ERROR: "请稍后重试，如问题持续请联系技术支持",
    }

    def handle(
        self, exception: Exception, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """处理异常并返回用户友好的提示"""
        exception_type = self._classify_exception(exception)

        return {
            "error_type": exception_type.value,
            "error_code": exception_type.value,
            "message": self.EXCEPTION_MESSAGES.get(
                exception_type, "处理过程中出现未知错误，请重试"
            ),
            "suggestion": self.EXCEPTION_SUGGESTIONS.get(exception_type, ""),
            "technical_detail": str(exception),
            "retryable": self._is_retryable(exception_type),
            "context": context or {},
        }

    def _classify_exception(self, exception: Exception) -> ExceptionType:
        """将异常分类为异常类型"""
        # 如果是AppException，直接返回类型
        if isinstance(exception, AppException):
            return exception.exception_type

        exception_message = str(exception).lower()

        # 文件相关异常
        if "encrypted" in exception_message or "password" in exception_message:
            return ExceptionType.FILE_ENCRYPTED
        if "corrupted" in exception_message or "损坏" in exception_message:
            return ExceptionType.FILE_CORRUPTED
        if "format" in exception_message and "unsupported" in exception_message:
            return ExceptionType.FILE_FORMAT_UNSUPPORTED

        # 模板相关异常
        if "template" in exception_message:
            if "parse" in exception_message:
                return ExceptionType.TEMPLATE_PARSE_FAILED
            if "style" in exception_message:
                return ExceptionType.TEMPLATE_STYLE_MESSY

        # 标记位相关
        if "marker" in exception_message or "标记" in exception_message:
            return ExceptionType.MARKER_NOT_INSERTED

        # 默认未知错误
        return ExceptionType.UNKNOWN_ERROR

    def _is_retryable(self, exception_type: ExceptionType) -> bool:
        """判断异常是否可重试"""
        retryable_types = {
            ExceptionType.UNKNOWN_ERROR,
            ExceptionType.FORMAT_APPLY_FAILED,
        }
        return exception_type in retryable_types


# 全局异常处理器实例
exception_handler = ExceptionHandler()
