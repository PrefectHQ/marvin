import asyncio
import inspect
import json
import re
from json import JSONDecodeError

from pydantic import Field

from marvin.models.threads import Message
from marvin.plugins import Plugin
from marvin.utilities.strings import condense_newlines, jinja_env
from marvin.utilities.types import LoggerMixin, MarvinBaseModel

AUTO_MODE_REGEX = re.compile(r".*?<auto-mode>\s*({.*})", re.DOTALL)
AUTOBOT_INSTRUCTIONS = condense_newlines(
    """
    # Auto Mode
    
    You can enter "auto mode" to improve your responses. In auto mode, you can
    break a large objective into smaller tasks, use plugins to achieve those
    tasks, and ultimately complete your objective. You must enter auto mode any
    time it would help you answer the user.
    
    To enter auto mode, add a JSON payload to your response, wrapped in
    `<auto-mode></auto-mode>` tags. When in auto-mode, you are autonomous and
    can not ask the user for help. The user can not see your auto mode payloads,
    except for your `user_update` messages. To exit auto mode, respond normally
    to the user WITHOUT a payload. 

    End every response by deciding if you need to enter auto-mode.
                    
    ## Format
        
    ``` 
    
    (you can put any response here, including letting the user know you're going
    to enter auto mode)
    
    <auto-mode>
    
    {        
        "objective": (describe your ultimate objective), 
                
        "user update": (a message about your progress that will be sent to the
        user),

        "progress assessment": (an honest assement of your progress, including any
        criticism or possible improvements. This will help you improve your response.),

        "tasks": [ 
            {
                "id": (a unique identifier for the task such as 1, 2, 3)
                
                "name": (describe a task you need to complete to reach your
                objective), 
                
                "done": (have you completed the task? true|false), 
                
                "results": (any thoughts about the task, or what you learned
                from completing it. DO NOT MAKE ANYTHING UP.)
            },
            ...
        ],
        
        
        "plugins": [
            {
                "name": (MUST be one of [{{ plugin_names }}])
                
                "inputs": {arg: value}
                
                "tasks": [(a list of any task ids this is related to. This is
                used to extract relevant information from the plugin output.)]
            }, 
            ...
        ]
    } 
    
    </auto-mode> 
    
    ```
    
    The `tasks` section tracks your progress toward a solution. You can update
    it at any time. Your tasks should reflect each step you need to take to
    deliver your ultimate objective. DO NOT assume you have the result of a task
    before you see it. DO NOT make up the result of a task. DO NOT mark a task
    as complete before you actually do it. 
    
    The `plugins` section instructs the system to call plugins and return the
    results to you as a system message. You can use as many plugins as you want
    at a time.
    
    You have the following plugins available: 
    
    {{ plugin_descriptions }} 
    
    ## Response 
     
    After you respond with your payload, the system will execute the plugins and
    return the outputs to you. You may then continue in auto mode by providing
    an updated payload or choose to respond to the user normally.
"""
)


class AutoMode(MarvinBaseModel, LoggerMixin):
    plugins: list[Plugin] = Field(default_factory=list)

    def get_instructions(self):
        plugin_descriptions = "\n\n".join(
            f"- {p.get_full_description()}" for p in self.plugins
        )
        plugin_names = ", ".join(p.name for p in self.plugins)

        instructions = jinja_env.from_string(AUTOBOT_INSTRUCTIONS).render(
            plugin_names=plugin_names,
            plugin_descriptions=plugin_descriptions,
        )

        return Message(role="system", content=instructions)

    async def parse_payload(self, response: str) -> list[Message]:
        messages = []

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

        return messages

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
