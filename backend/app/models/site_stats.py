from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from ..core.database import Base


class SiteStats(Base):
    """全站统计模型

    按日统计，不区分用户
    """

    __tablename__ = "site_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stat_date = Column(
        String(10), unique=True, nullable=False, index=True
    )  # 'YYYY-MM-DD'

    # 任务统计
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)

    # 功能使用统计
    cleaning_used = Column(Integer, default=0)
    correction_used = Column(Integer, default=0)
    pdf_used = Column(Integer, default=0)
    ocr_used = Column(Integer, default=0)

    # 时间戳
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return (
            f"<SiteStats(stat_date='{self.stat_date}', total_tasks={self.total_tasks})>"
        )
