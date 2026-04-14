"""processing_time改为Float精度

Revision ID: add3dde15fb8
Revises: cb69e180ad8e
Create Date: 2026-04-12 09:30:40.934860

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "add3dde15fb8"
down_revision: Union[str, None] = "cb69e180ad8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "processing_time",
            existing_type=sa.INTEGER(),
            type_=sa.Float(),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "processing_time",
            existing_type=sa.Float(),
            type_=sa.INTEGER(),
            existing_nullable=True,
        )
