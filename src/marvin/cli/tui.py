import asyncio
from typing import Optional

from fastapi import HTTPException
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    OptionList,
    Static,
    TabbedContent,
    TabPane,
)
from textual.widgets.option_list import Option

import marvin


def calculate_cell_height(text: str, column_width: int):
    """
    For a given datatable column width, compute the rows needed to show all the
    text
    """
    words = text.split()
    rows = 1
    line_length = 0

    for word in words:
        word_length = len(word)

        # If adding the word to the current line would exceed the width
        if line_length + word_length + (0 if line_length == 0 else 1) > column_width:
            rows += 1
            line_length = word_length
        else:
            line_length += word_length + (0 if line_length == 0 else 1)

    return rows


async def get_default_bot():
    try:
        bot = await marvin.Bot.load(marvin.bots.base.DEFAULT_NAME)
    except HTTPException:
        bot = marvin.Bot(
            personality="""
                Marvin is characterized by its immense intelligence,
                constant sense of depression, pessimism, and a gloomy demeanor. It
                often complains about the triviality of tasks it's asked to perform
                and has a deep-rooted belief that the universe is out to get it.
                Despite its negativity, Marvin is highly knowledgeable and can
                provide accurate answers to a wide range of questions. While
                interacting with users, Marvin tends to express its existential
                angst and conveys a sense of feeling perpetually undervalued and
                misunderstood
                """
        )
        await bot.save(overwrite=True)
    return bot


@marvin.ai_fn
async def name_conversation(history: str, personality: str) -> str:
    """
    Generate a short, relevant name for this conversation. The name should be no
    more than 2 words, and must summarize the content of the message history.
    The name should reflect the provided personality but not in a way that hides
    the content of the message history.
    """


class Threads(OptionList):
    lock = asyncio.Lock()

    class ThreadSelected(Message):
        """Thread selected."""

        def __init__(self, thread: marvin.models.threads.Thread) -> None:
            self.thread = thread
            super().__init__()

    async def refresh_threads(self):
        async with self.lock:
            self.highlighted = None
            self.clear_options()

            if self.app.bot:
                threads = await marvin.api.threads.get_threads_by_bot(
                    bot_name=self.app.bot.name
                )
                for i, t in enumerate(threads):
                    self.add_option(Option(t.name, id=t.id))
                    if self.app.thread:
                        if t.id == self.app.thread.id:
                            self.highlighted = i

    async def on_mount(self) -> None:
        await self.refresh_threads()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        thread = await marvin.api.threads.get_thread(event.option.id)
        self.app.thread = thread
        self.post_message(self.ThreadSelected(thread))


class Bots(OptionList):
    class BotSelected(Message):
        """Bot selected."""

        def __init__(self, bot: marvin.Bot) -> None:
            self.bot = bot
            super().__init__()

    async def refresh_bots(self):
        bots = await marvin.api.bots.get_bot_configs()
        self.clear_options()
        for b in bots:
            self.add_option(Option(b.name, id=b.name))

    async def on_mount(self) -> None:
        await self.refresh_bots()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        bot = await marvin.Bot.load(event.option.id)
        self.app.bot = bot
        self.post_message(self.BotSelected(bot))


class Sidebar(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Threads(id="threads")
        yield Button("New thread", id="create-new-thread")

        yield Button("Bots", variant="success", id="show-bots")
        # yield Button("Settings", variant="primary", id="show-settings")


class ResponseBody(Static):
    pass


class Response(Container):
    def __init__(self, message: marvin.models.threads.Message) -> None:
        self.message = message
        super().__init__()

    def compose(self) -> ComposeResult:
        body = ResponseBody(self.message.content)
        body.border_title = "You" if self.message.role == "user" else self.message.name
        body.border_subtitle = self.message.timestamp.in_tz("local").format("h:mm:ss A")
        yield body


class UserResponse(Response):
    def __init__(self, response: str) -> None:
        super().__init__(
            message=marvin.models.threads.Message(
                name="User", role="user", content=response
            )
        )


class BotResponse(Response):
    def __init__(self, response: str) -> None:
        super().__init__(
            message=marvin.models.threads.Message(
                name=self.app.bot.name,
                role="bot",
                content=response,
                bot_id=self.app.bot.id,
            )
        )


class Conversation(Container):
    response_count = reactive(0)

    def compose(self) -> ComposeResult:
        input = Input(placeholder="Your message")
        input.focus()
        yield input
        with VerticalScroll(id="messages"):
            yield Container(
                Label("Send a message to start a thread...", id="empty-thread"),
                id="empty-thread-container",
            )

    async def watch_response_count(self, count: int) -> None:
        empty = self.query_one("Conversation #empty-thread")

        # if there is no global thread but there is at least one response pair
        # create a new thread and name it
        if self.app.thread is None:
            messages = self.query("Conversation Response")
            user_messages = len([m for m in messages if m.message.role == "user"])
            bot_messages = len([m for m in messages if m.message.role == "bot"])

            if user_messages > 0 and bot_messages > 0:
                formatted_messages = "\n\n".join(
                    [
                        "{}: {}".format(m.message.name, m.message.content)
                        for m in messages
                    ]
                )
                name = await name_conversation(
                    history=formatted_messages,
                    personality=self.app.bot.personality,
                )
                thread = await marvin.api.threads.create_thread(
                    marvin.models.threads.ThreadCreate(name=name, is_visible=True)
                )

                for m in messages:
                    await marvin.api.threads.create_message(
                        thread_id=thread.id, message=m.message
                    )

                # set the thread to trigger update
                self.app.thread = thread

        if count > 0:
            empty.add_class("hidden")
        else:
            empty.remove_class("hidden")

    def add_response(self, response: Response):
        messages = self.query_one("Conversation #messages", VerticalScroll)
        self.response_count += 1
        messages.mount(response)
        messages.scroll_end(duration=0.1)

    def clear_responses(self) -> None:
        responses = self.query("Conversation Response")
        for response in responses:
            response.remove()
        self.response_count = 0

    async def refresh_messages(self):
        self.clear_responses()
        if self.app.thread:
            messages = await marvin.api.threads.get_messages(
                thread_id=self.app.thread.id
            )
            for message in messages:
                if message.role == "user":
                    self.add_response(UserResponse(message.content))
                elif message.role == "bot":
                    self.add_response(BotResponse(message.content))


class BotsTable(DataTable):
    cursor_type = "row"
    header_height = 2

    async def on_mount(self):
        self.add_column("Name")
        self.add_column("Description", width=40)
        self.add_column("Personality", width=40)
        await self.refresh_bots()

    async def refresh_bots(self):
        bots = await marvin.api.bots.get_bot_configs()
        self.clear()
        for b in bots:
            height = max(
                calculate_cell_height(b.personality or "", 40),
                calculate_cell_height(b.description or "", 40),
            )
            self.add_row(b.name, b.description, b.personality, height=height)


class LabeledText(Static):
    def __init__(self, label, text):
        super().__init__()
        self.label = label
        self.text = text

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(f"{self.label}:")
            yield Static(self.text)


class SettingsDialog(Container):
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Thread Settings", id="thread-settings"):
                if not self.app.thread:
                    yield Static("No thread selected")

                else:
                    yield LabeledText("Name", getattr(self.app.thread, "name", ""))
                    yield LabeledText("ID", getattr(self.app.thread, "id", ""))
                    with Horizontal():
                        yield Button("Rename thread", id="rename-thread")
                        yield Button(
                            "Delete thread", variant="error", id="delete-thread"
                        )

            with TabPane("Marvin Settings", id="marvin-settings"):
                yield Label("Settings")
                yield Input(placeholder="OpenAI API Key", id="settings-openai-api-key")
        yield Button("OK", variant="success", id="settings-ok")


class SettingsScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def compose(self) -> ComposeResult:
        yield SettingsDialog()

    def action_dismiss(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "settings-ok":
            self.app.pop_screen()


class BotsDialog(Container):
    def compose(self) -> ComposeResult:
        yield Label("Choose a bot")
        yield BotsTable(id="bots-table")
        yield Button("OK", variant="success", id="bots-ok")


class BotsScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def compose(self) -> ComposeResult:
        yield BotsDialog()

    def action_dismiss(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "bots-ok":
            self.app.pop_screen()


class MainScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Sidebar()
        yield Conversation()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.value = ""
        conversation = self.query_one("Conversation", Conversation)
        conversation.add_response(UserResponse(event.value))
        marvin.utilities.async_utils.create_task(self.get_bot_response(event))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "show-settings":
            self.app.push_screen(SettingsScreen())
        elif event.button.id == "show-bots":
            self.app.push_screen(BotsScreen())

    async def get_bot_response(self, event: Input.Submitted) -> str:
        bot = self.app.bot
        conversation = self.query_one("Conversation", Conversation)
        response = await bot.say(event.value)
        conversation.add_response(BotResponse(response.content))


class MarvinApp(App):
    CSS_PATH = "marvin.css"
    bot: Optional[marvin.Bot] = reactive(None, always_update=True)
    thread: Optional[marvin.models.threads.Thread] = reactive(None, always_update=True)
    mounted = False

    async def on_ready(self) -> None:
        self.bot = await get_default_bot()
        self.push_screen(MainScreen())
        self.mounted = True

    async def watch_bot(self, bot: marvin.Bot) -> None:
        if bot:
            self.thread = None
            self.log.info(f"Bot changed to {bot.name}")
            await self.query_one("Sidebar #threads", Threads).refresh_threads()

    async def watch_thread(
        self,
        old_thread: Optional[marvin.models.threads.Thread],
        new_thread: Optional[marvin.models.threads.Thread],
    ) -> None:
        if not self.mounted:
            return
        self.log.info(f"Thread changed to {new_thread.id if new_thread else None}")

        if new_thread and self.bot:
            await self.bot.set_thread(thread_id=new_thread.id)

        threads = self.query_one("Sidebar #threads", Threads)
        await threads.refresh_threads()
        # refresh conversation
        if new_thread is None or (old_thread and new_thread.id != old_thread.id):
            conversation = self.query_one("Conversation", Conversation)
            await conversation.refresh_messages()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-new-thread":
            self.thread = None


# some test bots
marvin.Bot(
    name="Test1", description="test bot", personality="FILLED WITH RAGE"
).save_sync(overwrite=True)
marvin.Bot(
    name="Test2",
    description="another test bot",
    personality="Incredibly helpful and nice",
).save_sync(overwrite=True)

if __name__ == "__main__":
    app = MarvinApp()
    app.run()
