import inspect
import xml.etree.ElementTree as ET
from typing import Literal, TypeVar

import anthropic
from anthropic.types import Message
from pydantic import BaseModel

import marvin
from marvin.types import Function, Tool
from marvin.utilities.jinja import Environment as jinja

T = TypeVar("T")

ANTHROPIC_FUNCTION_CALLING_PROMPT = inspect.cleandoc(
    """
    You have access to an additional set of one or more functions you can use to 
    answer the user's question.

    You may call them like this:
    <function_calls>
        <invoke>
            <tool_name>$TOOL_NAME</tool_name>
            <parameters>
                <$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>
                ...
            </parameters>
        </invoke>
    </function_calls>

    Here are the tools available:

    <tools>
    {% for tool in tools %}
        {{ tool }}
    {% endfor %}
    </tools>
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
    api_key = (
        key.get_secret_value() if (key := marvin.settings.anthropic.api_key) else key
    )
    client = anthropic.Anthropic(api_key=api_key)
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


def render_function_calling_prompt(
    tools: list[Tool],
    prompt_template: str = ANTHROPIC_FUNCTION_CALLING_PROMPT,
) -> str:
    return jinja.environment.from_string(ANTHROPIC_FUNCTION_CALLING_PROMPT).render(
        tools=[function_to_xml_string(tool.function) for tool in tools]
    )
