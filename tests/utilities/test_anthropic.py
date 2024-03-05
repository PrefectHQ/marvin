import pytest
from marvin.utilities.claude import (
    ChatRequest,
    ClientSideMessage,
    FunctionCall,
    function_to_xml_string,
    generate_chat,
    get_function_messages,
    parse_function_calls,
)
from marvin.utilities.pydantic import parse_as
from marvin.utilities.tools import tool_from_function


@pytest.fixture
def sample_function_calls_str():
    return """
    <function_calls>
    <invoke>
    <tool_name>function_name</tool_name>
    <parameters>
    <param1>value1</param1>
    <param2>value2</param2>
    </parameters>
    </invoke>
    </function_calls>
    """


@pytest.fixture
def sample_python_fn():
    def foo(a: int, b: str, c: bool = False) -> str:
        """Do the foo."""
        return f"{a} {b} {c}"

    return foo


@pytest.mark.no_llm
class TestFunctionToXml:
    def test_tool_from_function(self, sample_python_fn):
        tool = tool_from_function(sample_python_fn)

        assert tool.model_dump() == {
            "type": "function",
            "function": {
                "name": "foo",
                "description": "Do the foo.",
                "parameters": {
                    "additionalProperties": False,
                    "properties": {
                        "a": {"title": "A", "type": "integer"},
                        "b": {"title": "B", "type": "string"},
                        "c": {"title": "C", "type": "boolean", "default": False},
                    },
                    "required": ["a", "b"],
                    "type": "object",
                },
            },
        }

    def test_function_to_xml_string(self, sample_python_fn):
        tool = tool_from_function(sample_python_fn)
        xml_str = function_to_xml_string(tool.function)

        assert xml_str == (
            "<tool_description>"
            "<name>foo</name>"
            "<description>Do the foo.</description>"
            "<parameters>"
            "<parameter>"
            "<name>a</name>"
            "<type>integer</type>"
            "<description>None</description>"
            "</parameter>"
            "<parameter>"
            "<name>b</name>"
            "<type>string</type>"
            "<description>None</description>"
            "</parameter>"
            "<parameter>"
            "<name>c</name>"
            "<type>boolean</type>"
            "<description>None</description>"
            "</parameter>"
            "</parameters>"
            "</tool_description>"
        )


@pytest.mark.no_llm
class TestXmlParsing:
    def test_parsing_function_calls(self, sample_function_calls_str):
        function_calls = parse_function_calls(sample_function_calls_str)

        assert all(isinstance(call, FunctionCall) for call in function_calls)

        assert [c.model_dump() for c in function_calls] == [
            {
                "tool_name": "function_name",
                "parameters": {"param1": "value1", "param2": "value2"},
            }
        ]


class TestFunctionCalling:
    def test_basic(self):
        def get_schleeb() -> int:
            """returns the value of schleeb"""
            return 42

        tool = tool_from_function(get_schleeb)

        user_message = [{"role": "user", "content": "What is the value of schleeb?"}]

        messages = get_function_messages(tool.function)

        system_message = messages.pop(0)

        breakpoint()

        chat_request = ChatRequest(
            model="claude-3-opus-20240229",
            max_tokens=100,
            temperature=0.5,
            system=system_message.get("content"),
            messages=parse_as(list[ClientSideMessage], messages + user_message),
        )

        response = generate_chat(chat_request)

        print(response)

        breakpoint()
