import sqlalchemy as sa
from sqlmodel import Field

from marvin.models.ids import TopicID
from marvin.utilities.models import MarvinSQLModel


class Topic(MarvinSQLModel):
    __table_args__ = (
        sa.Index("uq_topic__account_id_name", "account_id", "name", unique=True),
    )
    id: TopicID = Field(default_factory=TopicID.new, primary_key=True)
    name: str = Field(index=True)
    description: str = None
