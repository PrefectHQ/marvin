import asyncio
from contextlib import asynccontextmanager

from fastapi import Body, Depends, FastAPI, HTTPException
from marvin.beta.assistants import Assistant
from marvin.beta.assistants.applications import AIApplication
from marvin.kv.disk import DiskKV
from marvin.utilities.logging import get_logger
from utils import (
    emit_assistant_completed_event,
    learn_from_child_interactions,
    query_parent_state,
)

parent_assistant_options = dict(
    instructions=(
        "Your job is to learn from the interactions between your child assistants and their users."
        " You will receive excerpts of these interactions as they happen."
        " Develop profiles of the users they interact with and store them in your state."
        " The user profiles should include: {name: str, notes: list[str], n_interactions: int}"
    ),
    state=DiskKV(storage_path="~/.marvin/state"),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with AIApplication(name="Marvin", **parent_assistant_options) as marvin:
        app.state.marvin = marvin
        task = asyncio.create_task(learn_from_child_interactions(marvin))
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app.state.marvin = None


app = FastAPI(lifespan=lifespan)
logger = get_logger("SubAssistant")


def get_parent_instance() -> AIApplication:
    marvin = app.state.marvin
    if not marvin:
        raise HTTPException(status_code=500, detail="Marvin instance not available")
    return marvin


child_assistant_options = dict(instructions="handle user requests")


@app.post("/assistant")
async def child_assistant_task(
    user_message: str = Body(..., embed=True),
    parent_app: AIApplication = Depends(get_parent_instance),
) -> dict:
    with Assistant(name="SubAssistant", **child_assistant_options) as ai:
        parent_state_excerpt = await query_parent_state(user_message)
        thread = ai.default_thread
        if parent_state_excerpt:
            await thread.add_async("here's what I know:\n" + parent_state_excerpt)
        await thread.add_async(user_message)
        await thread.run_async(ai)

        event = emit_assistant_completed_event(
            child_assistant=ai,
            parent_app=parent_app,
            payload={
                "messages": await thread.get_messages_async(json_compatible=True),
                "metadata": thread.metadata,
            },
        )
        logger.debug_kv("🚀  Emitted Event", event.event, "green")

        child_thread_messages = await thread.get_messages_async(json_compatible=True)
        return {"messages": child_thread_messages, "metadata": thread.metadata}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("start:app", reload=True, port=4200, log_level="debug")
