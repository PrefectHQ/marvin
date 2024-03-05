import inspect
import xml.etree.ElementTree as ET
from typing import Literal, TypeVar

import anthropic
from anthropic.types import Message
from pydantic import BaseModel

from marvin.types import Function
from marvin.utilities.jinja import Transcript

T = TypeVar("T")

ANTHROPIC_FUNCTION_PROMPT = inspect.cleandoc(
    """
    SYSTEM: Your job is to generate likely outputs for a Python function with the
    following definition:

    {{ fn_definition }}

    The user will provide function inputs (if any) and you must respond with
    the most likely result.
    
    USER: 
    
    ## Function inputs
    
    {% if bound_parameters -%}
    The function was called with the following inputs:
    {%for (arg, value) in bound_parameters.items()%}
    - {{ arg }}: {{ value }}
    {% endfor %}
    {% else %}
    The function was not called with any inputs.
    {% endif %}
    
    {% if return_value -%}
    ## Additional Context
    
    I also preprocessed some of the data and have this additional context for you to consider:
    
    {{return_value}}
    {% endif %}

    What is the function's output?
    
    ASSISTANT: The output is
    """
)


class ClientSideMessage(BaseModel):
    role: Literal["assistant", "user"]
    content: str


class FunctionCall(BaseModel):
    tool_name: str
    parameters: dict[str, str]


class ChatRequest(BaseModel):
    model_config = dict(extra="allow")

    messages: list[ClientSideMessage]

    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 1_000
    temperature: float = 0.0
    system: str = "You are a helpful assistant."


def generate_chat(chat_request: ChatRequest) -> Message:
    client = anthropic.Anthropic()
    return client.messages.create(**chat_request.model_dump())


def parse_function_calls(xml_str: str) -> list[FunctionCall]:
    return [
        FunctionCall(
            tool_name=invoke.find("tool_name").text,
            parameters={param.tag: param.text for param in invoke.find("parameters")},
        )
        for invoke in ET.fromstring(xml_str).findall("invoke")
    ]


def function_to_xml_string(function: Function[T]) -> str:
    root = ET.Element("tool_description")

    ET.SubElement(root, "name").text = function.name

    if function.description:
        ET.SubElement(root, "description").text = function.description

    parameters_element = ET.SubElement(root, "parameters")

    for param_name in function.parameters.get("properties", {}).keys():
        parameter_element = ET.SubElement(parameters_element, "parameter")
        ET.SubElement(parameter_element, "name").text = param_name
        ET.SubElement(parameter_element, "type").text = function.parameters[
            "properties"
        ][param_name]["type"]
        ET.SubElement(parameter_element, "description").text = function.parameters[
            "properties"
        ][param_name].get("description", "None")

    return ET.tostring(root, "unicode")


def get_function_messages(function: Function[T]) -> list[dict]:
    messages = Transcript(content=ANTHROPIC_FUNCTION_PROMPT).render_to_messages(
        fn_definition=function_to_xml_string(function),
        bound_parameters={},
        return_value=None,
    )

    return [m.model_dump() for m in messages]
