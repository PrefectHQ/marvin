"""Add llmcall-message tracking

Revision ID: 06f7fae3efce
Revises: 73129c5b1859
Create Date: 2025-03-02 13:51:01.981648

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "06f7fae3efce"
down_revision = "73129c5b1859"
branch_labels = None
depends_on = None


def upgrade():
    # Create the llm_call_messages table
    op.create_table(
        "llm_call_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("llm_call_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("in_initial_prompt", sa.Boolean(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["llm_call_id"],
            ["llm_calls.id"],
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_llm_call_messages_llm_call_id", "llm_call_messages", ["llm_call_id"]
    )
    op.create_index(
        "ix_llm_call_messages_message_id", "llm_call_messages", ["message_id"]
    )


def downgrade():
    # Drop table and indexes
    op.drop_table("llm_call_messages")
