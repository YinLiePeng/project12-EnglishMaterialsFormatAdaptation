"""添加structure_analysis字段

Revision ID: 9dced3b4a845
Revises: 4053cc466253
Create Date: 2026-04-01 23:46:46.940275

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9dced3b4a845"
down_revision: Union[str, None] = "4053cc466253"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 structure_analysis 列
    op.add_column("tasks", sa.Column("structure_analysis", sa.Text(), nullable=True))


def downgrade() -> None:
    # 删除 structure_analysis 列
    op.drop_column("tasks", "structure_analysis")
