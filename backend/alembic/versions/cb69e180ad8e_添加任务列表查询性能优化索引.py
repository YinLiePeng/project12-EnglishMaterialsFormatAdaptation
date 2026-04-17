"""添加任务列表查询性能优化索引

Revision ID: cb69e180ad8e
Revises: 9dced3b4a845
Create Date: 2026-04-03 23:25:36.813233

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cb69e180ad8e"
down_revision: Union[str, None] = "9dced3b4a845"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建复合索引：状态+创建时间（用于状态筛选和排序）
    op.create_index(
        "idx_tasks_status_created", "tasks", ["status", "created_at"], unique=False
    )

    # 创建索引：创建时间（用于时间范围查询和排序）
    op.create_index("idx_tasks_created_at", "tasks", ["created_at"], unique=False)

    # 创建索引：文件名（用于模糊搜索）
    op.create_index("idx_tasks_filename", "tasks", ["input_filename"], unique=False)

    # 创建索引：排版模式（用于筛选）
    op.create_index("idx_tasks_layout_mode", "tasks", ["layout_mode"], unique=False)

    # 创建索引：完成时间（用于已完成/失败任务的查询）
    op.create_index(
        "idx_tasks_completed_created",
        "tasks",
        ["completed_at", "created_at"],
        unique=False,
        postgresql_where="status IN ('completed', 'failed')",
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index("idx_tasks_completed_created", table_name="tasks")
    op.drop_index("idx_tasks_layout_mode", table_name="tasks")
    op.drop_index("idx_tasks_filename", table_name="tasks")
    op.drop_index("idx_tasks_created_at", table_name="tasks")
    op.drop_index("idx_tasks_status_created", table_name="tasks")
