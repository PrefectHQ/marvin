from pydantic import BaseModel, Field, validator


class LanguageModel(BaseModel):
    name: str = None
    model: str = Field(default="gpt-3.5-turbo-0613")
    max_tokens: int = Field(default=4000)
    temperature: float = Field(default=0.8)
    stream: bool = Field(default=False)

    @validator("name", always=True)
    def default_name(cls, v):
        if v is None:
            v = cls.__name__
        return v
