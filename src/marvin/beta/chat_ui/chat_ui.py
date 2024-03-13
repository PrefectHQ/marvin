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

from marvin.beta.assistants.threads import Message, Thread


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def server_process(host, port, message_queue):
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
    async def post_message(
        thread_id: str, content: str = Body(..., embed=True)
    ) -> None:
        thread = Thread(id=thread_id)
        await thread.add_async(content)
        message_queue.put(dict(thread_id=thread_id, message=content))

    @app.get("/api/messages/")
    async def get_messages(thread_id: str) -> list[Message]:
        thread = Thread(id=thread_id)
        return await thread.get_messages_async(limit=100)

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


class InteractiveChat:
    def __init__(self, callback: Callable = None):
        self.callback = callback
        self.server_process = None
        self.port = None
        self.message_queue = multiprocessing.Queue()

    def start(self, thread_id: str):
        self.port = find_free_port()
        self.server_process = multiprocessing.Process(
            target=server_process,
            args=("127.0.0.1", self.port, self.message_queue),
        )
        self.server_process.daemon = True
        self.server_process.start()

        self.message_processing_thread = threading.Thread(target=self.process_messages)
        self.message_processing_thread.start()

        url = f"http://127.0.0.1:{self.port}?thread_id={thread_id}"
        print(f"Server started on {url}")
        time.sleep(1)
        webbrowser.open(url)

    def process_messages(self):
        while True:
            details = self.message_queue.get()
            if details is None:
                break
            if self.callback:
                self.callback(
                    thread_id=details["thread_id"], message=details["message"]
                )

    def stop(self):
        if self.server_process and self.server_process.is_alive():
            self.server_process.terminate()
            self.server_process.join()
            print("Server shut down.")

        self.message_queue.put(None)
        self.message_processing_thread.join()
        print("Message processing thread shut down.")


@contextmanager
def interactive_chat(thread_id: str, message_callback: Callable = None):
    chat = InteractiveChat(message_callback)
    try:
        chat.start(thread_id=thread_id)
        yield chat
    finally:
        chat.stop()
