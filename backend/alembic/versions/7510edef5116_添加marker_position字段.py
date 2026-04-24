"""添加marker_position字段

Revision ID: 7510edef5116
Revises: add3dde15fb8
Create Date: 2026-04-12 21:52:52.198569

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "7510edef5116"
down_revision: Union[str, None] = "add3dde15fb8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("marker_position", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "marker_position")
