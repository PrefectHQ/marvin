import multiprocessing
import socket
import threading
import time
import webbrowser
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

import uvicorn
from fastapi import Body, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from marvin.beta.assistants.threads import Thread, ThreadMessage


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def create_app(thread_id: str, message_queue: multiprocessing.Queue):
    app = FastAPI()

    # Mount static files
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    async def get_chat_ui():
        with open(Path(__file__).parent / "static/chat.html", "r") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content)

    @app.post("/api/messages/")
    async def post_message(content: str = Body(..., embed=True)) -> None:
        thread = Thread(id=thread_id)
        await thread.add_async(content)
        message_queue.put(content)
        # return message

    @app.get("/api/messages/")
    async def get_messages() -> list[ThreadMessage]:
        thread = Thread(id=thread_id)
        return await thread.get_messages_async(limit=20)

    return app


def server_process(host, port, thread_id, message_queue):
    app = create_app(thread_id, message_queue)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


class InteractiveChat:
    def __init__(self, thread_id: str, callback: Callable = None):
        self.thread_id = thread_id
        self.callback = callback
        self.server_process = None
        self.port = None
        self.message_queue = multiprocessing.Queue()

    def start(self):
        self.port = find_free_port()
        self.server_process = multiprocessing.Process(
            target=server_process,
            args=("127.0.0.1", self.port, self.thread_id, self.message_queue),
        )
        self.server_process.daemon = True  # Set the process as a daemon
        self.server_process.start()

        # Start the message processing thread
        self.message_processing_thread = threading.Thread(target=self.process_messages)
        self.message_processing_thread.start()

        url = f"http://127.0.0.1:{self.port}?thread_id={self.thread_id}"
        print(f"Server started on {url}")
        time.sleep(1)
        webbrowser.open(url)

    def process_messages(self):
        while True:
            message = self.message_queue.get()
            if message is None:  # Signal to stop processing
                break
            if self.callback:
                self.callback(message)

    def stop(self):
        if self.server_process and self.server_process.is_alive():
            self.server_process.terminate()
            self.server_process.join()
            print("Server shut down.")

        # Signal the message processing thread to stop
        self.message_queue.put(None)
        self.message_processing_thread.join()
        print("Message processing thread shut down.")


@contextmanager
def interactive_chat(thread_id: str, message_callback: Callable = None):
    chat = InteractiveChat(thread_id, message_callback)
    try:
        chat.start()
        yield chat
    finally:
        chat.stop()
