"""add instructions_template to Bot

Revision ID: 6c1c3f3dbb92
Revises: 38f0bc56a565
Create Date: 2023-04-04 11:53:40.587362

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "6c1c3f3dbb92"
down_revision = "38f0bc56a565"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bot_config",
        sa.Column(
            "instructions_template", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("bot_config", "instructions_template")
