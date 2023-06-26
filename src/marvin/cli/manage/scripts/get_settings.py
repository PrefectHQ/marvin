import os
import importlib
from pydantic import BaseSettings

def get_settings() -> BaseSettings:
    path =  os.path.join(os.getcwd(), 'config/settings.py')
    spec = importlib.util.spec_from_file_location('Config', path)
    settings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings)
    config = settings.Config()
    return config