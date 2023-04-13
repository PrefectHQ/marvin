import asyncio
import inspect
import json
import re
from json import JSONDecodeError

from marvin.bot.base import Bot
from marvin.bot.response_formatters import ResponseFormatter
from marvin.models.threads import Message
from marvin.utilities.strings import condense_newlines

EMPTY_CONTEXT = {
    "mode": "auto",
    "objective": None,
    "tasks": [],
    "plugins": [],
}

AUTO_MODE_REGEX = re.compile(r'({\s*"mode":\s*"auto".*})', re.DOTALL)


INSTRUCTIONS = condense_newlines(
    """
    # Auto Mode
    
    You MUST enter Auto Mode unless you are absolutely sure you have enough
    information to respond to the user.
    
    In auto mode, you can access the internet, use plugins, research
    information, perform complex reasoning, and interact with external systems.
    You do not need permission to enter Auto Mode.
    
    In auto mode, you are in an autonomous loop and can not ask the user for
    help. The user can not see what you're doing, and can only receive updates
    from you while you work. To enter or remain in auto mode, you must include a
    structured JSON payload in your response. Start by stating your overall
    objective, then break it into discrete subtasks and use plugins to achieve
    those tasks. 
    
    ## Format
    
    ```json    
    
    (you can put any response here, but auto mode requires the JSON payload below)
    
    {        
        "mode": "auto",
        
        "user_update": (a message about what you're doing or your progress that
        will be sent to the user),

        "objective": (describe your ultimate objective), 
        
        "is_complete": (true|false),
                
        "critical_assessment": (an honest assement of your progress, including
        any criticism or possible improvements. This will help you improve your
        response.),

        "tasks": [ 
            {
                "id": (a unique identifier for the task such as 1, 2, 3)

                "name": (describe a task you need to complete to reach your
                objective), 

                
                "is_complete": (have you completed the task? true|false),
                
                "results": (any thoughts about the task, or what you learned
                from completing it. DO NOT MAKE ANYTHING UP.)
            },
            ...
        ],
        
        "plugins": [
            {
                "name": (MUST be one of [{{ plugins|join(', ',
                attribute='name')}}])
                
                "inputs": {arg: value}
                
                "tasks": [(a list of any task ids this is related to. This is
                used to extract relevant information from the plugin output.)]
            }, 
            ...
        ]
    } 
        
    ```
    
    The `tasks` section tracks your progress toward a solution. You can update
    it at any time. Your tasks should reflect each step you need to take to
    deliver your ultimate objective. Tasks should always start with
    `is_complete=false`. Do not mark the objective complete until all tasks are
    complete. Auto mode will exit when the objective is complete. After you say
    a task is complete for the first time, you don't need to include it in the
    payload anymore.
        
    The `plugins` section instructs the system to call plugins and return the
    results to you as a system message. You can use as many plugins as you want
    at a time. Only include plugins you want to call on the next loop. Do not
    include plugins for completed tasks.
    
    You have the following plugins available: 
    
    {% for plugin in plugins -%} 
    
    - {{ plugin.get_full_description() }}
    
    {% endfor -%}
    
    After each loop, you will be provided with any plugin outputs that you
    requested, as well as your previous JSON response. To exit auto mode, simply
    respond normally without a JSON payload.
"""
)


class AutoMode(Bot):
    # personality = "Does not engage the user. Only responds with valid JSON payloads."
    instructions = INSTRUCTIONS
    response_format: ResponseFormatter = None

    async def _call_llm(self, messages: list[Message], **kwargs) -> str:
        finished = False
        auto_mode_json = {}
        auto_mode_messages = []
        while not finished:
            llm_messages = messages + auto_mode_messages
            llm_messages.append(
                Message(
                    role="system",
                    content=f"Previous auto mode payload: {auto_mode_json}",
                )
            )

            llm_response = await super()._call_llm(llm_messages, **kwargs)
            auto_mode_messages, auto_mode_json = await self.parse_payload(
                response=llm_response
            )

            if auto_mode_json.get("is_complete", False):
                finished = True

        return auto_mode_json.get("result", "No result found")

    async def parse_payload(self, response: str) -> list[Message]:
        messages = []
        auto_mode_json = {}

        if match := AUTO_MODE_REGEX.search(response):
            try:
                auto_mode_json = json.loads(match.group(1))
                messages.append(Message(role="bot", content=response))
                self.logger.debug_kv("Auto Mode payload", auto_mode_json)

                plugins = auto_mode_json.get("plugins", [])
                plugin_outputs = await asyncio.gather(
                    *[self.run_plugin(p["name"], p["inputs"]) for p in plugins]
                )
                plugin_payload = dict(zip([p["name"] for p in plugins], plugin_outputs))

                messages.append(
                    Message(role="system", content=json.dumps(plugin_payload))
                )

            except JSONDecodeError as exc:
                messages.append(
                    Message(
                        role="system",
                        content=f"Auto Mode payload was invalid JSON, try again: {exc}",
                    )
                )
            except Exception as exc:
                messages.append(
                    Message(
                        role="system",
                        content=f"Auto Mode encountered an error, try again: {exc}",
                    )
                )

        return messages, auto_mode_json

    async def run_plugin(self, plugin_name: str, plugin_inputs: dict) -> str:
        plugin = next((p for p in self.plugins if p.name == plugin_name.strip()), None)
        if plugin is None:
            return f'Plugin "{plugin_name}" not found.'
        try:
            self.logger.debug_kv(f'Running plugin "{plugin_name}"', plugin_inputs)
            plugin_output = plugin.run(**plugin_inputs)
            if inspect.iscoroutine(plugin_output):
                plugin_output = await plugin_output
            self.logger.debug_kv("Plugin output", plugin_output)

            return plugin_output
        except Exception as exc:
            self.logger.error(
                f"Error running plugin {plugin_name} with inputs"
                f" {plugin_inputs}:\n\n{exc}"
            )
            return f"Plugin encountered an error. Try again? Error message: {exc}"
