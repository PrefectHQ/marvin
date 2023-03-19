import sqlalchemy as sa
from sqlmodel import Field

from marvin.models.ids import TopicID
from marvin.utilities.models import MarvinSQLModel


class Topic(MarvinSQLModel):
    __table_args__ = (sa.Index("uq_topic__name", "name", unique=True),)
    id: TopicID = Field(default_factory=TopicID.new, primary_key=True)
    name: str
    description: str = None
