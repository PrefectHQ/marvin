"""add binary content

Revision ID: 15e5aca7994f
Revises: 06f7fae3efce
Create Date: 2025-03-04 00:21:09.056569

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "15e5aca7994f"
down_revision = "06f7fae3efce"
branch_labels = None
depends_on = None


def upgrade():
    # Create binary_contents table
    op.create_table(
        "binary_contents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("part_index", sa.Integer(), nullable=False),
        sa.Column("content_index", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], name="fk_binary_contents_message_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_binary_contents_message_id", "binary_contents", ["message_id"], unique=False
    )


def downgrade():
    # Drop binary_contents table
    op.drop_index("ix_binary_contents_message_id", table_name="binary_contents")
    op.drop_table("binary_contents")
