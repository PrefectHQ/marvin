import atexit
import multiprocessing
import threading
import time
import webbrowser
from contextlib import contextmanager
from pathlib import Path

import uvicorn
from fastapi import Body, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from marvin.beta.assistants.threads import Thread, ThreadMessage

app = FastAPI()

# Global event to signal the server to shut down
shutdown_event = threading.Event()

# Mount static files, assuming your HTML and JS are in a directory named 'static'

app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)


@app.get("/", response_class=HTMLResponse)
async def get_chat_ui():
    # Serve your HTML file
    with open(Path(__file__).parent / "static/chat.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)


@app.post("/api/messages/")
async def post_message(
    thread_id: str = Body(...), content: str = Body(...)
) -> ThreadMessage:
    thread = Thread(id=thread_id)
    message = await thread.add_async(content)
    return message


@app.get("/api/messages/{thread_id}")
async def get_messages(thread_id: str) -> list[ThreadMessage]:
    thread = Thread(id=thread_id)
    messages = await thread.get_messages_async()
    return messages


# Define a function to run the server
def run_server():
    # Uvicorn configuration
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)

    # Function to be called upon exit to ensure the server shuts down
    def on_exit():
        print("Stopping server...")
        server.should_exit = True
        server.force_exit = True
        print("Server stopped.")

    # Register the exit function
    atexit.register(on_exit)

    # Start and run server
    server.run()


@contextmanager
def interactive_chat_server(thread_id: str):
    # Start the server as a subprocess
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    url_with_thread_id = f"http://127.0.0.1:8000?thread_id={thread_id}"
    print(f"Server started on {url_with_thread_id}")
    time.sleep(2)

    try:
        # run_server()
        webbrowser.open(url_with_thread_id)
        yield
    finally:
        # Terminate the server process
        server_process.terminate()
        server_process.join()
        print("Server shut down.")
