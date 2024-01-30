import marvin
from marvin.settings import temporary_settings
from pydantic import BaseModel, field_validator


class DoesntMakeSense(BaseModel):
    a: int

    @field_validator("a")
    @classmethod
    def sabotage(cls, v):
        raise ValueError("This doesn't make sense")


RETRY_CONFIGS = [
    {"model_kwargs": {"model": "gpt-3.5-turbo", "temperature": 0.7}, "retries": 3},
    {"model_kwargs": {"model": "gpt-3.5-turbo", "temperature": 0.3}, "retries": 3},
    {"model_kwargs": {"model": "gpt-4", "temperature": 0.0}, "retries": 2},
]


@marvin.fn(model_kwargs=RETRY_CONFIGS)
def really_complex_madlib() -> DoesntMakeSense:
    """trying to get the llm to fill out a real complex schema"""


with temporary_settings(log_level="DEBUG"):
    print(really_complex_madlib())
