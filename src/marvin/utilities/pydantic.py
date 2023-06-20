import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from datamodel_code_generator import InputFileType, generate
from pydantic import BaseModel, Field, validator

from marvin import ai_model


def create_model_from_schema(schema: dict):
    # create a temporary json file
    name_of_model = schema.get('title', 'Model')

    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            json.dump(schema, f)
            temp_json_file = f.name
            f.close()

        with tempfile.NamedTemporaryFile(mode='w+t', delete=False) as f:
            generate(
                input_=Path(temp_json_file),
                input_file_type=InputFileType.JsonSchema,
                output=Path(f.name + '.py'),
            )
            temp_python_file = f.name + '.py'
            f.close()

        with open(temp_python_file, 'r') as file:
            lines = file.readlines()[5:]
            file.close()

        with open(temp_python_file, 'w') as file:
            file.writelines(lines)
            file.close()
 
        spec = importlib.util.spec_from_file_location("temp_module", temp_python_file)

        # Create a module from the spec
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        import inspect

    finally:
        # Remove temporary files
        os.unlink(temp_json_file)
        os.unlink(temp_python_file)

    # return the generated model
    return getattr(module, name_of_model)


class DataSchema(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    properties: Optional[dict] = {}
    required: Optional[list[str]] = []
    additionalProperties: bool = False
    definitions: dict = {}
    description: Optional[str] = None

    @classmethod
    def from_description(cls, description:str):
        return(ai_model(cls)(description))
    
    def update_schema_from_description(self, description: str):
        prompt = (
            f'Given previous schema {self.to_model().schema_json(indent=2)}\n\n',
            f'Update with the following modifications: {description}'
        )
        return self.__class__.from_description(prompt)
    
    def to_model(self):
        return(create_model_from_schema(self.dict()))
        
    def eval(self, context: str):
        return ai_model(self.to_model())(context)