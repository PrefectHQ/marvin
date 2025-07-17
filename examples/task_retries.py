"""Example showing how to control retries for Tasks with pydantic output."""

from pydantic import BaseModel, Field, field_validator

import marvin


class SpecialCode(BaseModel):
    """A model with a custom validation rule that requires learning from errors."""

    code: str = Field(description="The special code")

    @field_validator("code")
    def validate_code(cls, v):
        # This validator has a special requirement: the code must end with "-42X"
        # The agent won't know this initially and will learn from the error
        if not v.endswith("-42X"):
            raise ValueError("Code must end with '-42X' (company policy)")
        return v


# Set custom retry limit (default is 10)
marvin.settings.agent_retries = 3

# Use a thread to maintain conversation history across retries
thread = marvin.Thread()

# Create a task that will likely fail on first attempt
task = marvin.Task[SpecialCode](
    instructions="Generate a special code for project ALPHA",
    result_type=SpecialCode,
)

print(f"Running task with retry limit of {marvin.settings.agent_retries}...")
result = task.run(thread=thread)
print(f"Successfully generated: {result}")
