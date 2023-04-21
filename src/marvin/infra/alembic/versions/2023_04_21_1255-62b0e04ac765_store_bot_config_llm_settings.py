"""store bot config LLM settings

Revision ID: 62b0e04ac765
Revises: 62dbb6aaed4d
Create Date: 2023-04-21 12:55:59.689423

"""
import sqlalchemy as sa
from alembic import op
from marvin.infra.database import JSONType

# revision identifiers, used by Alembic.
revision = "62b0e04ac765"
down_revision = "62dbb6aaed4d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bot_config",
        sa.Column("llm_settings", JSONType(), server_default="{}", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("bot_config", "llm_settings")
