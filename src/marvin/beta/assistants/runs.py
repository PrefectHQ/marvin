import asyncio
from typing import Any, Callable, Optional, Union

from openai.types.beta.threads.run import Run as OpenAIRun
from openai.types.beta.threads.runs import RunStep as OpenAIRunStep
from pydantic import BaseModel, Field, PrivateAttr, field_validator

import marvin.utilities.tools
from marvin.requests import Tool
from marvin.tools.assistants import AssistantTool, CancelRun
from marvin.utilities.asyncio import ExposeSyncMethodsMixin, expose_sync_method
from marvin.utilities.logging import get_logger
from marvin.utilities.openai import get_client

from .assistants import Assistant
from .threads import Thread

logger = get_logger("Runs")


class Run(BaseModel, ExposeSyncMethodsMixin):
    thread: Thread
    assistant: Assistant
    instructions: Optional[str] = Field(
        None, description="Replacement instructions to use for the run."
    )
    additional_instructions: Optional[str] = Field(
        None,
        description=(
            "Additional instructions to append to the assistant's instructions."
        ),
    )
    tools: Optional[list[Union[AssistantTool, Callable]]] = Field(
        None, description="Replacement tools to use for the run."
    )
    additional_tools: Optional[list[AssistantTool]] = Field(
        None,
        description="Additional tools to append to the assistant's tools. ",
    )
    run: OpenAIRun = None
    data: Any = None

    @field_validator("tools", "additional_tools", mode="before")
    def format_tools(cls, tools: Union[None, list[Union[Tool, Callable]]]):
        if tools is not None:
            return [
                (
                    tool
                    if isinstance(tool, Tool)
                    else marvin.utilities.tools.tool_from_function(tool)
                )
                for tool in tools
            ]

    @expose_sync_method("refresh")
    async def refresh_async(self):
        client = get_client()
        self.run = await client.beta.threads.runs.retrieve(
            run_id=self.run.id, thread_id=self.thread.id
        )

    @expose_sync_method("cancel")
    async def cancel_async(self):
        client = get_client()
        await client.beta.threads.runs.cancel(
            run_id=self.run.id, thread_id=self.thread.id
        )

    async def _handle_step_requires_action(self):
        client = get_client()
        if self.run.status != "requires_action":
            return
        if self.run.required_action.type == "submit_tool_outputs":
            tool_outputs = []
            tools = self.get_tools()

            for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
                try:
                    output = marvin.utilities.tools.call_function_tool(
                        tools=tools,
                        function_name=tool_call.function.name,
                        function_arguments_json=tool_call.function.arguments,
                    )
                except CancelRun as exc:
                    logger.debug(f"Ending run with data: {exc.data}")
                    raise
                except Exception as exc:
                    output = f"Error calling function {tool_call.function.name}: {exc}"
                    logger.error(output)
                tool_outputs.append(
                    dict(tool_call_id=tool_call.id, output=output or "")
                )

            await client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.thread.id, run_id=self.run.id, tool_outputs=tool_outputs
            )

    def get_instructions(self) -> str:
        if self.instructions is None:
            instructions = self.assistant.get_instructions() or ""
        else:
            instructions = self.instructions

        if self.additional_instructions is not None:
            instructions = "\n\n".join([instructions, self.additional_instructions])

        return instructions

    def get_tools(self) -> list[AssistantTool]:
        tools = []
        if self.tools is None:
            tools.extend(self.assistant.get_tools())
        else:
            tools.extend(self.tools)
        if self.additional_tools is not None:
            tools.extend(self.additional_tools)
        return tools

    async def run_async(self) -> "Run":
        client = get_client()

        create_kwargs = {}

        if self.instructions is not None or self.additional_instructions is not None:
            create_kwargs["instructions"] = self.get_instructions()

        if self.tools is not None or self.additional_tools is not None:
            create_kwargs["tools"] = self.get_tools()

        self.run = await client.beta.threads.runs.create(
            thread_id=self.thread.id, assistant_id=self.assistant.id, **create_kwargs
        )

        self.assistant.pre_run_hook(run=self)

        try:
            while self.run.status in ("queued", "in_progress", "requires_action"):
                if self.run.status == "requires_action":
                    await self._handle_step_requires_action()
                await asyncio.sleep(0.1)
                await self.refresh_async()
        except CancelRun as exc:
            logger.debug(f"`CancelRun` raised; ending run with data: {exc.data}")
            await client.beta.threads.runs.cancel(
                run_id=self.run.id, thread_id=self.thread.id
            )
            self.data = exc.data
            await self.refresh_async()

        if self.run.status == "failed":
            logger.debug(f"Run failed. Last error was: {self.run.last_error}")

        self.assistant.post_run_hook(run=self)
        return self


class RunMonitor(BaseModel):
    run_id: str
    thread_id: str
    _run: Run = PrivateAttr()
    _thread: Thread = PrivateAttr()
    steps: list[OpenAIRunStep] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._thread = Thread(**kwargs["thread_id"])
        self._run = Run(**kwargs["run_id"], thread=self.thread)

    @property
    def thread(self):
        return self._thread

    @property
    def run(self):
        return self._run

    async def refresh_run_steps_async(self):
        """
        Asynchronously refreshes and updates the run steps list.

        This function fetches the latest run steps up to a specified limit and
        checks if the latest run step in the current run steps list
        (`self.steps`) is included in the new batch. If the latest run step is
        missing, it continues to fetch additional run steps in batches, up to a
        maximum count, using pagination. The function then updates
        `self.steps` with these new run steps, ensuring any existing run steps
        are updated with their latest versions and new run steps are appended in
        their original order.
        """
        # fetch up to 100 run steps
        max_fetched = 100
        limit = 50
        max_attempts = max_fetched / limit + 2

        # Fetch the latest run steps
        client = get_client()

        response = await client.beta.threads.runs.steps.list(
            run_id=self.run.id,
            thread_id=self.thread.id,
            limit=limit,
        )
        run_steps = list(reversed(response.data))

        if not run_steps:
            return

        # Check if the latest run step in self.steps is in the new run steps
        latest_step_id = self.steps[-1].id if self.steps else None
        missing_latest = (
            latest_step_id not in {rs.id for rs in run_steps}
            if latest_step_id
            else True
        )

        # If the latest run step is missing, fetch additional run steps
        total_fetched = len(run_steps)
        attempts = 0
        while (
            run_steps
            and missing_latest
            and total_fetched < max_fetched
            and attempts < max_attempts
        ):
            attempts += 1
            response = await client.beta.threads.runs.steps.list(
                run_id=self.run.id,
                thread_id=self.thread.id,
                limit=limit,
                # because this is a raw API call, "after" refers to pagination
                # in descnding chronological order
                after=run_steps[0].id,
            )
            paginated_steps = list(reversed(response.data))

            total_fetched += len(paginated_steps)
            # prepend run steps
            run_steps = paginated_steps + run_steps
            if any(rs.id == latest_step_id for rs in paginated_steps):
                missing_latest = False

        # Update self.steps with the latest data
        new_steps_dict = {rs.id: rs for rs in run_steps}
        for i in range(len(self.steps) - 1, -1, -1):
            if self.steps[i].id in new_steps_dict:
                self.steps[i] = new_steps_dict.pop(self.steps[i].id)
            else:
                break
        # Append remaining new run steps at the end in their original order
        self.steps.extend(new_steps_dict.values())
