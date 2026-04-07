from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
import uuid
from ..core.database import Base


class Template(Base):
    """模板模型

    存储策略：持久化存储，公共模板(V2将按用户区分)
    """

    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # 文件信息(持久化存储)
    file_path = Column(String(500))
    file_hash = Column(String(64))
    file_size = Column(Integer)
    thumbnail_path = Column(String(500))

    # 样式参数(JSON字符串)
    style_params = Column(Text)

    # 使用统计
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)

    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Template(template_id='{self.template_id}', name='{self.name}')>"
