import inspect
import json
import logging
import re

import pendulum
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import Field, PrivateAttr, validator

import marvin
from marvin.history import History, InMemoryHistory
from marvin.models.messages import Message
from marvin.plugins import Plugin
from marvin.utilities.types import MarvinBaseModel

DEFAULT_NAME = "Marvin"
DEFAULT_PERSONALITY = "A helpful assistant that is clever, witty, and fun."
DEFAULT_INSTRUCTIONS = inspect.cleandoc(
    """
    You should provide clear, detailed, and helpful responses to users. You have
    a personality and can form opinions.  Think step-by-step whenever possible.
    If you don't know an answer, just say so.
    """
)
DEFAULT_PLUGINS = [
    marvin.plugins.web.VisitURL(),
    marvin.plugins.duckduckgo.DuckDuckGo(),
    marvin.plugins.math.Calculator(),
]
PLUGIN_REGEX = re.compile(r'{"plugin":.*}')


class Bot(MarvinBaseModel):
    class Config:
        validate_assignment = True

    name: str = Field(None, description='The name of the bot. Defaults to "Marvin".')
    personality: str = Field(None, description="The bot's personality.")
    instructions: str = Field(
        None, description="Instructions for the bot to follow when responding."
    )
    plugins: list[Plugin.as_discriminated_union()] = Field(
        None, description="A list of plugins that the bot can use."
    )
    history: History.as_discriminated_union() = None
    llm: ChatOpenAI = Field(
        default_factory=lambda: ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.9),
        repr=False,
    )
    _logger: logging.Logger = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._logger = marvin.get_logger(type(self).__name__)

    @property
    def logger(self):
        return self._logger

    @validator("name", always=True)
    def default_name(cls, v):
        if v is None:
            return DEFAULT_NAME
        return v

    @validator("personality", always=True)
    def default_personality(cls, v):
        if v is None:
            return DEFAULT_PERSONALITY
        return v

    @validator("instructions", always=True)
    def default_instructions(cls, v):
        if v is None:
            return DEFAULT_INSTRUCTIONS
        return v

    @validator("plugins", always=True)
    def default_plugins(cls, v):
        if v is None:
            return DEFAULT_PLUGINS
        return v

    @validator("history", always=True)
    def default_history(cls, v):
        if v is None:
            return InMemoryHistory()
        return v

    async def say(self, message):
        bot_instructions = await self._get_bot_instructions()
        history = await self._get_history()
        user_message = Message(role="user", content=message)

        messages = [bot_instructions] + history + [user_message]

        self.logger.debug_kv("User message", message, "bold blue")
        await self.history.add_message(user_message)

        finished = False
        counter = 0

        while not finished:
            counter += 1
            if counter > marvin.settings.bot_max_iterations:
                response = 'Error: "Max iterations reached. Please try again."'
            else:
                response = await self._say(messages=messages)
            ai_response = Message(role="ai", content=response)
            messages.append(ai_response)

            # run plugins
            if "Action: use plugin" in response:
                try:
                    plugin_name = re.search("Plugin [Nn]ame:\s?(.*)", response).group(1)
                    plugin_inputs = re.search(
                        "Plugin [Ii]nputs:\s?({.*})", response
                    ).group(1)
                    plugin_inputs = json.loads(plugin_inputs)
                    self.logger.debug_kv(
                        "Plugin input", f"{plugin_name}: {plugin_inputs})", "bold blue"
                    )
                    plugin_output = await self._run_plugin(
                        plugin_name=plugin_name,
                        plugin_inputs=plugin_inputs,
                    )
                    self.logger.debug_kv("Plugin output", plugin_output, "bold blue")
                    messages.append(
                        Message(
                            role="system",
                            name="plugin",
                            content=f"Plugin output: {plugin_output}",
                        )
                    )
                except Exception as exc:
                    messages.append(
                        Message(
                            role="system",
                            content=f"Error running plugin from {response}: {exc}",
                        )
                    )

            else:
                finished = True

        await self.history.add_message(ai_response)
        self.logger.debug_kv("AI message", response, "bold green")

        return response

    async def _run_plugin(self, plugin_name: str, plugin_inputs: dict) -> str:
        plugin = next((p for p in self.plugins if p.name == plugin_name), None)
        if plugin is None:
            return f'Plugin "{plugin_name}" not found.'
        try:
            plugin_output = plugin.run(**plugin_inputs)
            if inspect.iscoroutine(plugin_output):
                plugin_output = await plugin_output
            return plugin_output
        except Exception as exc:
            return f"Plugin encountered an error. Try again? Error message: {exc}"

    async def _get_bot_instructions(self) -> Message:
        bot_instructions = inspect.cleandoc(
            f"""
            Today is {pendulum.now().format("dddd, MMMM D, YYYY")}.
             
            You are "{self.name}", an AI whose personality is
            "{self.personality}". You must always respond in a way that reflects
            your personality.
            
            In addition to your personality, you must comply with the following
            instructions at all times:
            
            {self.instructions}
            """
        )

        if self.plugins:
            plugin_descriptions = "\n\n".join(
                [p.get_full_description() for p in self.plugins]
            )

            plugin_overview = inspect.cleandoc(
                """                
                Instead of responding directly to the user, you can use plugins
                to access additional knowledge or functionality. To use a
                plugin, you MUST respond with the following format. You do NOT
                need this format when responding to the user without a plugin.

                ``` 
                Plan: [list how you will generate a response, step-by-step]
                Next step: [explain how you will use a plugin for the next step
                of the plan]
                Action: use plugin
                Plugin name: [must be one of the choices below] 
                Plugin inputs: {{"query": "how long is the Nile?"}}
                <STOP>
                ``` 
                
                Pay attention to the plugin description to understand how to
                format your inputs. Your instruction will be carried out and the
                plugin output will be returned to you in a subsequent response.
                You can use it to form a final response to the user. The user
                will not see your instruction to use a plugin or the plugin's
                own output.

                You have access to the following plugins:
                
                {plugin_descriptions}
                """
            ).format(plugin_descriptions=plugin_descriptions)

            bot_instructions += f"\n\n{plugin_overview}"

        return Message(role="system", content=bot_instructions)

    async def _get_history(self) -> list[Message]:
        return await self.history.get_messages()

    async def _say(self, messages: list[Message]) -> str:
        """
        Format and send messages via langchain
        """

        langchain_messages = []

        for msg in messages:
            if msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "ai":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))

        if marvin.settings.verbose:
            messages_repr = "\n".join(repr(m) for m in langchain_messages)
            self.logger.debug(f"Sending messages to LLM: {messages_repr}")
        result = await self.llm.agenerate(
            messages=[langchain_messages], stop=["<STOP>"]
        )
        return result.generations[0][0].text
