from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Index
from datetime import datetime
import uuid
from ..core.database import Base


class Task(Base):
    """任务模型

    存储策略：原始资料和处理结果均为临时存储(24小时)
    """

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    status = Column(
        String(20), default="pending", index=True
    )  # pending/processing/completed/failed
    task_type = Column(String(50), nullable=False)

    # 文件信息(原始资料 - 临时存储)
    input_filename = Column(String(255))
    input_file_path = Column(String(500))
    input_file_hash = Column(String(64))
    input_file_size = Column(Integer)
    input_expire_at = Column(DateTime)

    # 模板信息(仅用于当前任务，不持久化)
    template_filename = Column(String(255))
    template_file_path = Column(String(500))

    # 处理选项
    layout_mode = Column(String(20))  # none/empty/complete
    preset_style = Column(String(100))
    enable_cleaning = Column(Integer, default=0)
    enable_correction = Column(Integer, default=0)
    enable_llm = Column(Integer, default=0)  # 是否启用大模型语义识别
    marker_position = Column(Text, nullable=True)  # 标记位位置(JSON)

    # 结构分析结果(JSON格式存储)
    structure_analysis = Column(Text, nullable=True)  # 存储文章结构识别结果

    # 处理结果(临时存储)
    output_filename = Column(String(255))
    output_file_path = Column(String(500))
    output_expire_at = Column(DateTime)
    processing_time = Column(Float)  # 处理时长(秒)

    # 错误信息
    error_message = Column(Text)
    error_code = Column(String(50))

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    def __repr__(self):
        return f"<Task(task_id='{self.task_id}', status='{self.status}')>"
