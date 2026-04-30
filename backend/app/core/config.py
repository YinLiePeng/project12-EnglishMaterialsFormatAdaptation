from pydantic_settings import BaseSettings
from pathlib import Path
import yaml


class Settings(BaseSettings):
    """应用配置"""

    # 应用信息
    APP_NAME: str = "英语教学资料格式适配工具"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/english_tool.db"

    # 大模型配置
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen-max"
    LLM_PROMPTS_FILE: str = "./prompts.yaml"

    # 百度OCR配置
    BAIDU_OCR_API_KEY: str = ""
    BAIDU_OCR_SECRET_KEY: str = ""

    # OCR引擎选择：llm_vision（默认，零成本启动）| baidu（百度OCR）
    OCR_BACKEND: str = "llm_vision"

    # 文件存储配置
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    TEMP_STORAGE_PATH: str = "./tmp"
    TEMPLATE_STORAGE_PATH: str = "./templates"
    TEMP_EXPIRE_HOURS: int = 24

    # 文档限制配置
    DOCX_MAX_PAGES: int = 30
    PDF_MAX_PAGES: int = 50
    MAX_REVISIONS: int = 500
    LLM_MAX_TOKENS: int = 20000

    # Hybrid PDF解析配置
    HYBRID_SERVER_ENABLED: bool = True  # 是否启用hybrid server
    HYBRID_SERVER_PORT: int = 5002  # hybrid server端口
    HYBRID_SERVER_HOST: str = "127.0.0.1"  # hybrid server主机
    HYBRID_SERVER_TIMEOUT: int = 300  # hybrid server启动超时(秒)
    HYBRID_SERVER_LOG_LEVEL: str = "error"  # hybrid server日志级别
    HYBRID_PARSE_TIMEOUT: int = 600  # PDF解析超时(秒)
    HYBRID_FALLBACK_ON_FAILURE: bool = True  # 失败时是否回退到标准模式

    class Config:
        # 从项目根目录加载 .env
        env_file = Path(__file__).parent.parent.parent / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def ensure_directories(self):
        """确保必要的目录存在"""
        Path(self.TEMP_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
        Path(self.TEMPLATE_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
        Path("./data").mkdir(parents=True, exist_ok=True)

    def load_prompts(self) -> dict:
        """加载LLM提示词配置"""
        try:
            # 获取相对于config.py文件的路径
            config_dir = Path(__file__).parent.parent.parent
            prompts_file = config_dir / self.LLM_PROMPTS_FILE

            if not prompts_file.exists():
                print(f"警告: Prompt配置文件不存在: {prompts_file}")
                return {}

            with open(prompts_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"加载Prompt配置失败: {e}")
            return {}


# 全局配置实例
settings = Settings()

# 全局Prompt配置（延迟加载）
_prompts_cache: dict = None


def get_prompts() -> dict:
    """获取Prompt配置（带缓存）"""
    global _prompts_cache
    if _prompts_cache is None:
        _prompts_cache = settings.load_prompts()
    return _prompts_cache
