from rich.panel import Panel
from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Input,
    TextLog,
)

import marvin


def chat_message(speaker: str, message: str, color: str = "gray50"):
    return Panel(message, title=speaker, border_style=color)


class ChatHistory(TextLog):
    pass


class HTTPApp(App):
    CSS_PATH = "tui.css"
    TITLE = "Marvin"
    dark = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield ChatHistory(id="chat_history")
        yield Input(placeholder="Your message", id="input_message", value=None)

    def on_mount(self) -> None:
        self.method = "GET"
        self.query_one("#input_message", Input).focus()
        self.content_type = ""
        self.bot = marvin.Bot()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self.submit()

    async def submit(self):
        input = self.query_one("#input_message", Input)
        message = input.value
        input.value = ""
        text_log = self.query_one(TextLog)
        text_log.write(
            Panel(message, title="You", title_align="right", border_style="gray50")
        )

        response = await self.bot.say(message)
        text_log.write(
            Panel(
                response.content,
                title=self.bot.name,
                title_align="left",
                border_style="blue",
            )
        )
