import inspect

from pydantic import Field, validator

from marvin.utilities.types import DiscriminatingTypeModel

PLUGIN_INSTRUCTIONS = """
You can use the following plugins
"""


class Plugin(DiscriminatingTypeModel):
    name: str = None
    description: str = Field(
        None,
        description=(
            "A description of the plugin that will be provided to the bot, in addition"
            " to the docstring for the run() method."
        ),
    )

    @validator("name", always=True)
    def default_name_from_cls(cls, v):
        if v is None:
            return cls.__name__
        return v

    @validator("description", always=True)
    def validate_description(cls, v):
        if v is None and cls.run.__doc__ is None:
            raise ValueError(
                "Either a description or a run() docstring must be provided for the"
                " plugin."
            )
        return v or cls.run.__doc__

    def get_full_description(self) -> str:
        signature = str(inspect.signature(self.run))
        description = self.description.format(**self.dict())
        docstring = self.run.__doc__
        return inspect.cleandoc(
            f"""
            {self.name}: {signature}
            {description}
            {docstring}
            """
        )

    def run(self, **kwargs):
        return None
