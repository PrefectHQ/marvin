import sys
import types
from typing import Any, Type

from graphviz import Digraph
from marvin import ai_fn
from prefect import flow, task
from prefect.tasks import task_input_hash
from pydantic import BaseModel, create_model
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine, inspect
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from typing_extensions import TypedDict

Base = declarative_base()


class MyCompanyDataModel:
    colors = {"lightblue2", "lightgreen", "lightpink"}

    class DepartmentModel(Base):
        __tablename__ = "department"
        id = Column(Integer, primary_key=True)
        name = Column(String)
        employees = relationship("EmployeeModel", backref="department")

    class EmployeeModel(Base):
        __tablename__ = "employee"
        id = Column(Integer, primary_key=True)
        name = Column(String)
        department_id = Column(Integer, ForeignKey("department.id"))
        project_id = Column(Integer, ForeignKey("project.id"))
        project = relationship("ProjectModel", backref="employees")

    class ProjectModel(Base):
        __tablename__ = "project"
        id = Column(Integer, primary_key=True)
        name = Column(String)

    color_map = {
        model.__name__: color
        for model, color in zip(vars(), colors)
        if isinstance(model, type) and issubclass(model, Base)
    }

    @classmethod
    def register_models(cls):
        for name, model in vars(cls).items():
            if isinstance(model, type) and issubclass(model, Base):
                model.__table__.metadata = Base.metadata


MyCompanyDataModel.register_models()
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)


def create_typed_dict_from_table(model: Type[Base]) -> dict[str, Any]:
    """Dynamically create a Pydantic Field from a SQLAlchemy model."""
    fields = {}
    annotations = {}
    for column in inspect(model).c:
        python_type = column.type.python_type
        field_name = column.name
        fields[field_name] = (python_type, ...)
        annotations[field_name] = python_type

    return types.new_class(
        f"{model.__name__}Data",
        bases=(TypedDict,),
        exec_body=lambda ns: ns.update(__annotations__=annotations, **fields),
    )


@flow
def create_entities(
    data_model_name: str, description: str, how_many: int, refresh: bool = False
) -> list[BaseModel]:
    data_model = getattr(sys.modules[__name__], data_model_name)
    model_refs = [
        name
        for name, cls in vars(data_model).items()
        if isinstance(cls, type) and issubclass(cls, Base)
    ]

    DictDataModel: Type[BaseModel] = create_model(
        data_model_name,
        **{
            model_ref: (
                list[create_typed_dict_from_table(getattr(data_model, model_ref))],
                ...,
            )
            for model_ref in model_refs
        },
    )

    def _make_entities(description: str, n: int) -> DictDataModel:
        @ai_fn
        def make_entities(description: str, n: int) -> DictDataModel:
            """Generate a total of `n` entities based on the provided `description`.

            Use a sensible proportion of each model type based on the provided `description`.
            """

        return make_entities(description, n)

    settings = dict(
        cache_key_fn=task_input_hash,
        refresh_cache=refresh,
    )

    entities = task(**settings)(_make_entities)(description, how_many)
    session = sessionmaker(bind=engine)()

    for model_name, model_data in entities:
        if model_data:
            model_class = getattr(data_model, model_name)
            for row in model_data:
                session.add(model_class(**row))
    session.commit()
    return entities


entities = create_entities(
    "MyCompanyDataModel",
    description=(
        "Projects and Employees would each belong to a Department in a Diverse London"
        " startup"
    ),
    how_many=20,
    # refresh=True,
)


dot = Digraph(comment="The Company Database Schema")
dot.attr(rankdir="LR", size="8,5")

session = sessionmaker(bind=engine)()

model_colors = MyCompanyDataModel.color_map

for model_name, color in model_colors.items():
    model_class = getattr(MyCompanyDataModel, model_name)
    instances = session.query(model_class).all()
    for instance in instances:
        instance_label = f"{model_name}: {instance.id}"
        dot.node(
            f"{model_name}{instance.id}", instance_label, style="filled", color=color
        )

for model_name in model_colors.keys():
    model_class = getattr(MyCompanyDataModel, model_name)
    mapper = inspect(model_class)
    for instance in session.query(model_class).all():
        for rel in mapper.relationships:
            related_instances = getattr(instance, rel.key)
            if isinstance(related_instances, list):
                for related_instance in related_instances:
                    dot.edge(
                        f"{model_name}{instance.id}",
                        f"{rel.mapper.class_.__name__}{related_instance.id}",
                    )
            else:
                if related_instances:
                    dot.edge(
                        f"{model_name}{instance.id}",
                        f"{rel.mapper.class_.__name__}{related_instances.id}",
                    )


dot.render("output/company_db_schema", cleanup=True)
