import datetime
import functools
import hashlib
import string
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

from prefect.variables import Variable

import marvin

T = TypeVar("T")


def _int_to_base(num: int, base: int = 36) -> str:
    """Convert an integer to a string in the specified base using ALPHABET."""
    # Define the allowed alphabet (base36: digits + lowercase letters)
    ALPHABET = (
        string.digits + string.ascii_lowercase
    )  # '0123456789abcdefghijklmnopqrstuvwxyz'
    if num == 0:
        return ALPHABET[0]
    digits = []
    while num:
        num, rem = divmod(num, base)
        digits.append(ALPHABET[rem])
    return "".join(reversed(digits))


def _generate_key(s: str) -> str:
    """
    Generate a unique key for Prefect variables.
    This function:
      1. Removes whitespace and forces lowercase.
      2. Computes a SHA-256 hash of the cleaned string.
      3. Converts the hash to an integer.
      4. Encodes that integer in base36.
    """
    # Clean the string: remove whitespace and lowercase it
    cleaned = "".join(s.split()).lower()
    # Compute the SHA-256 hash
    hash_bytes = hashlib.sha256(cleaned.encode("utf-8")).digest()
    # Convert hash bytes to an integer
    hash_int = int.from_bytes(hash_bytes, byteorder="big")
    # Convert the integer to a base36 string
    return _int_to_base(hash_int, base=36)


def http_get(url: str) -> str:
    import requests

    response = requests.get(url)
    return response.text


PROMPT = """
Your job is to determine if a condition has been met since the last time you
checked. You will be provided with a description of the condition and a context object from your last check. 

<condition-criteria>
{condition}
</condition-criteria>

<context>
{context}
</context>

<last-run-time>
{last_run_time}
</last-run-time>

<current-run-time>
{current_run_time}
</current-run-time>
"""


@dataclass
class WhenContext(Generic[T]):
    condition_met: bool
    details: T | None = field(
        metadata={
            "description": "User-requested details about the condition, if it was met. These will be provided to the user."
        }
    )
    notes: str = field(
        metadata={
            "description": "Private notes about your last check. Use these to help track state and determine if the condition has been met."
        }
    )


def when(
    condition: str,
    details_type: type = str,
    agent: marvin.Agent | None = None,
    tools: list[Callable] | None = None,
    variable_key: str | None = None,
):
    """A decorator that executes a function when a specified condition is met during periodic checks.

    This decorator creates a Prefect flow that periodically monitors a condition and executes
    the decorated function when that condition is satisfied. The condition's state is persisted
    between checks using Prefect variables, allowing the flow to track changes over time.

    The decorated function can optionally receive details about the condition when it is met.
    If the function accepts an argument, it will be called with the details when the
    condition is met. If it accepts no arguments, it will be called directly.

    The flow should be deployed and scheduled to run at appropriate intervals using Prefect's
    scheduling capabilities. The check interval should be chosen based on the condition being
    monitored.

    Args:
        condition: A string describing the condition to monitor. This should be a clear,
            natural language description of what needs to happen for the function to execute.
        details_type: The type of details to return when the condition is met. Defaults to str.
            This type will be used to structure the information passed to the decorated function.
        agent: Optional custom agent to use for condition monitoring. If not provided,
            the default agent will be used.
        tools: Optional list of callable tools the agent can use to check the condition.
            Defaults to [http_get] if not specified.
        variable_key: Optional key for storing condition state in Prefect variables.
            Defaults to a hash of the condition, function name, and docstring.

    Returns:
        A Prefect flow that wraps the decorated function and executes it when the
        condition is met.

    Examples:
        >>> # Basic usage - check every minute
        >>> @when('a new clock minute started')
        ... def new_minute():
        ...     print('new minute!')
        >>> # Deploy with schedule
        >>> new_minute.serve(interval=60)

        >>> # Monitor GitHub issues hourly
        >>> @when('a new GitHub issue is created', details_type=dict)
        ... def handle_issue(issue_details: dict):
        ...     print(f"New issue: {issue_details['title']}")
        >>> # Deploy with schedule
        >>> handle_issue.serve(interval=3600)

        >>> # Check weather every 30 minutes
        >>> @when('the weather is sunny', tools=[get_weather])
        ... def go_outside():
        ...     print('Time for a walk!')
        >>> # Deploy with schedule
        >>> go_outside.serve(interval=1800)

    Notes:
        - Requires Prefect to be installed: `uv pip install "marvin[prefect]"`
        - The condition state is persisted between checks using Prefect variables
        - The decorated function becomes a Prefect flow that should be scheduled
        - Choose appropriate check intervals based on your condition requirements
        - The flow maintains context between runs to detect changes over time
    """
    try:
        import prefect
    except ImportError:
        raise ImportError(
            'Prefect is not installed. Please install Marvin with the Prefect extra: `uv pip install "marvin[prefect]"`.'
        )

    def wrapper(
        fn,
        condition=condition,
        details_type=details_type,
        variable_key=variable_key,
        agent=agent,
        tools=tools,
    ):
        if tools is None:
            tools = [http_get]

        if variable_key is None:
            variable_key = _generate_key(f"{condition}|{fn.__name__}|{fn.__doc__}")

        @prefect.flow(name=fn.__name__)
        def when_flow():
            last_variable = Variable.get(variable_key, default={})

            task = marvin.Task[WhenContext[details_type]](
                instructions=PROMPT.format(
                    condition=condition,
                    context=last_variable.get("context", "[no context found]"),
                    last_run_time=last_variable.get("run_time", "[no prior run found]"),
                    current_run_time=datetime.datetime.now(datetime.timezone.utc),
                ),
                result_type=WhenContext[details_type],
                agents=[agent] if agent else None,
                tools=tools,
            )

            run_time = datetime.datetime.now(datetime.timezone.utc)
            result = task.run()

            Variable.set(
                variable_key,
                {"context": result, "run_time": run_time},
                overwrite=True,
            )

            if result.condition_met:
                # if fn takes no args, call it directly
                if fn.__code__.co_argcount == 0:
                    return fn()
                # otherwise, call it with the details
                else:
                    return fn(result.details)
            else:
                return None

        return when_flow

    return functools.partial(
        wrapper,
        condition=condition,
        details_type=details_type,
        variable_key=variable_key,
        agent=agent,
        tools=tools,
    )
