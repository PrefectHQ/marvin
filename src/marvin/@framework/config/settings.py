from pydantic import BaseSettings   

class Config(BaseSettings):
    project_name: str = "{{project_name}}"
    asgi: str = "main:app"