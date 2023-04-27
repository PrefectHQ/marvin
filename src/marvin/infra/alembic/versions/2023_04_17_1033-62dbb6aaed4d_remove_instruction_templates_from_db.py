"""remove instruction templates from db

Revision ID: 62dbb6aaed4d
Revises: 6c1c3f3dbb92
Create Date: 2023-04-17 10:33:51.748873

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "62dbb6aaed4d"
down_revision = "6c1c3f3dbb92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("bot_config") as batch_op:
        batch_op.drop_column("instructions_template")


def downgrade() -> None:
    op.add_column(
        "bot_config",
        sa.Column(
            "instructions_template", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
