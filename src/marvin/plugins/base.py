import inspect

from pydantic import validator

from marvin.utilities.types import TaggedModel

PLUGIN_INSTRUCTIONS = """
You can use the following plugins
"""


class Plugin(TaggedModel):
    name: str = None
    description: str

    @validator("name", always=True)
    def default_name_from_cls(cls, v):
        if v is None:
            return cls.__name__
        return v

    def get_instructions(self) -> str:
        signature = str(inspect.signature(self.run))
        description = self.description.format(**self.dict())
        return str(dict(name=self.name, signature=signature, description=description))

    def run(self, **kwargs):
        raise NotImplementedError("Plugin subclass must implement this method")
