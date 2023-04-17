"""remove old instruction templates

Revision ID: 62dbb6aaed4d
Revises: 6c1c3f3dbb92
Create Date: 2023-04-17 10:33:51.748873

"""
import asyncio

import sqlalchemy as sa
from marvin.infra.database import session_context
from marvin.models.bots import BotConfig

# revision identifiers, used by Alembic.
revision = "62dbb6aaed4d"
down_revision = "6c1c3f3dbb92"
branch_labels = None
depends_on = None


async def run_upgrade():
    async with session_context(begin_transaction=True) as session:
        query = sa.select(BotConfig)
        result = await session.execute(query)
        for bot_config in result.scalars().all():
            # check if default instructions template was used
            if "Your name is: {{ name }}" in bot_config.instructions_template:
                bot_config.instructions_template = None
                session.add(bot_config)


def upgrade() -> None:
    asyncio.run(run_upgrade())


def downgrade() -> None:
    # no downgraded needed
    pass
