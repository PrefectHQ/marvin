import inspect
from functools import partial
from typing import Callable

from pydantic import Field, PrivateAttr, validator

from marvin.utilities.strings import safe_format
from marvin.utilities.types import DiscriminatedUnionType

PLUGIN_INSTRUCTIONS = """
You can use the following plugins
"""


class Plugin(DiscriminatedUnionType):
    name: str = None
    description: str = Field(
        None,
        description=(
            "A description of the plugin that will be provided to the bot, in addition"
            " to the docstring for the run() method."
        ),
        repr=False,
    )
    _signature: str = PrivateAttr()

    def __repr__(self):
        return 'Plugin("{}")'.format(self.name)

    def __init__(self, **kwargs):
        if "signature" in kwargs:
            self._signature = kwargs.pop("signature")
        else:
            self._signature = inspect.signature(self.run)
        super().__init__(**kwargs)

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
        return v

    def get_full_description(self) -> str:
        description = safe_format(self.description, **self.dict()).strip()
        docstring = self.run.__doc__

        result = inspect.cleandoc(
            f"""
            Name: {self.name}
            Signature: {self._signature}
            """
        )
        if description:
            result += f"\n{description}"
        if docstring:
            result += f"\n{docstring}"
        return result

    def run(self, **kwargs):
        return None


def plugin(fn: Callable = None, *, name=None, description=None):
    """
    Converts a function into a plugin

    @plugin
    def random_number(min: float = 0, max: float = 1) -> float:
        '''Returns a random number between min and max'''
        return min + (max - min) * random.random()


    """
    # this allows the decorator to be used with or without calling it
    if fn is None:
        return partial(plugin, name=name, description=description)

    class DynamicPlugin(Plugin):
        _discriminator = fn.__name__

        def run(self, *args, **kwargs):
            return fn(*args, **kwargs)

    DynamicPlugin.__name__ = fn.__name__

    cls = DynamicPlugin(
        name=name or fn.__name__,
        description=description or fn.__doc__,
        signature=inspect.signature(fn),
    )
    return cls
