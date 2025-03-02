"""Improve message tracking

Revision ID: 73129c5b1859
Revises: e772a112ae87
Create Date: 2025-03-02 12:37:16.130192

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = "73129c5b1859"
down_revision = "e772a112ae87"
branch_labels = None
depends_on = None


def upgrade():
    # Rename timestamp column to created_at and add default UTC now
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column("timestamp", new_column_name="created_at")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "created_at", server_default=func.now(), existing_type=sa.DateTime()
        )


def downgrade():
    # Revert changes - rename created_at back to timestamp and remove default
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column("created_at", new_column_name="timestamp")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "timestamp", server_default=None, existing_type=sa.DateTime()
        )
