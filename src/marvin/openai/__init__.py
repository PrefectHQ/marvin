import sys
import openai
from .ChatCompletion import ChatCompletion, Request
from .Function import openai_fn
from .Function.Registry import OpenAIFunctionRegistry

openai.ChatCompletion = ChatCompletion
openai.openai_fn = openai_fn
openai.OpenAIFunctionRegistry = OpenAIFunctionRegistry


# TODO: This is a hack to make the openai module available in the global namespace
sys.modules[__name__] = openai
