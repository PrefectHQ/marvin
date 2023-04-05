import asyncio
from typing import Optional

import dotenv
import openai
from fastapi import HTTPException
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    Markdown,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option

import marvin
from marvin.config import ENV_FILE


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
    more than 3 words and summarize the user's intent in a recognizable way.
    The name should reflect the provided personality.
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
                    self.add_option(None)
                    if self.app.thread:
                        if t.id == self.app.thread.id:
                            self.highlighted = i

    async def on_mount(self) -> None:
        await self.refresh_threads()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        thread = await marvin.api.threads.get_thread(event.option.id)
        self.app.thread = thread
        self.post_message(self.ThreadSelected(thread))


class BotsOptionList(OptionList):
    bot: None

    class BotHighlighted(Message):
        """Bot selected."""

        def __init__(self, bot: marvin.Bot) -> None:
            self.bot = bot
            super().__init__()

    async def refresh_bots(self):
        bots = await marvin.api.bots.get_bot_configs()
        self.clear_options()
        for i, b in enumerate(bots):
            self.add_option(Option(b.name, id=b.name))
            self.add_option(None)
            if self.app.bot:
                if b.name == self.app.bot.name:
                    self.highlighted = i

    async def on_mount(self) -> None:
        await self.refresh_bots()

    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ):
        self.bot = await marvin.Bot.load(event.option.id)
        self.post_message(self.BotHighlighted(self.bot))


class BotsInfo(Static):
    bot = reactive(None)

    def __init__(self, bot: marvin.models.bots.BotConfig = None, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot

    def compose(self):
        yield TextTable()

    def watch_bot(self, bot: marvin.models.bots.BotConfig):
        if bot:
            data = {
                "Name": bot.name,
                "Description": bot.description or "",
                "Personality": bot.personality or "",
                "Instructions": bot.instructions or "",
            }
        else:
            data = {
                "Name": "",
                "Description": "",
                "Personality": "",
                "Instructions": "",
            }
        try:
            text_table = self.query_one("TextTable", TextTable)
            text_table.data = data
        except NoMatches:
            pass


class Sidebar(VerticalScroll):
    def compose(self) -> ComposeResult:
        with Horizontal(id="bot-name-container"):
            yield Label("Bot: ", id="bot-name-label")
            yield Label(
                self.app.bot.name if self.app.bot else "No bot selected", id="bot-name"
            )
        yield Label("All threads", classes="sidebar-title")
        yield Threads(id="threads")
        yield Button("Bots", variant="success", id="show-bots")
        yield Button("New thread", id="create-new-thread", variant="primary")
        yield Button("Delete thread", id="delete-thread", variant="error")
        yield Button("Settings", variant="primary", id="show-settings")


class ResponseBody(Markdown):
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
        input = Input(placeholder="Your message", id="message-input")
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

        if count == 1:
            empty.add_class("hidden")
        elif count == 0:
            empty.remove_class("hidden")

    async def add_response(self, response: Response, scroll: bool = True) -> None:
        messages = self.query_one("Conversation #messages", VerticalScroll)
        messages.mount(response)
        if scroll:
            await asyncio.sleep(0.05)
            messages.scroll_end(duration=0.1)
        self.response_count += 1

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
                    await self.add_response(UserResponse(message.content), scroll=False)
                elif message.role == "bot":
                    await self.add_response(BotResponse(message.content), scroll=False)

        messages = self.query_one("Conversation #messages", VerticalScroll)
        # sleep to ensure it scrolls - otherwise doesn't always work
        await asyncio.sleep(0.05)
        messages.scroll_end(animate=False)


class LabeledText(Static):
    def __init__(self, label, text):
        super().__init__()
        self.label = label
        self.text = text

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(f"{self.label}:", classes="label")
            yield Static(self.text, classes="text")


class TextTable(Static):
    data = reactive(dict, layout=True)
    DEFAULT_CSS = """
        TextTable {
            padding: 1 2 1 2;
        }
        
        TextTable .row {
            margin-bottom: 1;
            height: auto;
            width: 100%;
        }

        TextTable .label {
            width: auto;
            height: auto;
            text-align: right;            
            color: gray;
            margin-right: 2;
        }

        TextTable .text {
            width: 1fr;
            height: auto;
        }
       """

    def __init__(self, data: dict = None):
        super().__init__()
        if data is not None:
            self.data = data

    def compose(self):
        for label, text in self.data.items():
            with Horizontal(classes="row"):
                yield Label(f"{label}:", classes="label")
                yield Static(text, classes="text")

    def watch_data(self, data: dict):
        self.query().remove()

        width = 0
        if data:
            for label, text in data.items():
                print(label)
                width = max(width, len(label) + 2)
                self.mount(
                    Horizontal(
                        Label(f"{label}:", classes="label"),
                        Static(text, classes="text"),
                        classes="row",
                    )
                )
            for label in self.query("Label"):
                label.styles.width = width


class SettingsDialogue(Container):
    def compose(self) -> ComposeResult:
        if marvin.settings.openai_api_key.get_secret_value():
            openai.api_key = marvin.settings.openai_api_key.get_secret_value()
            try:
                # see if we can load models from the API
                openai.Model.list()
                info_message = "Status: ✅\n\nYou have a valid OpenAI API key."
            except Exception as exc:
                info_message = f"Status: ❌\n\n{repr(exc)}"
        else:
            info_message = "Status: ❔\n\nYou have not set an OpenAI API key."

        with Container(
            classes="settings-container", id="openai-settings-container"
        ) as c:
            c.border_title = "OpenAI settings"
            yield Input(
                placeholder="OpenAI API Key",
                id="settings-openai-api-key",
                password=True,
            )
            yield Label(info_message, classes="api-key-info")
        yield Button("OK", variant="success", id="settings-ok")

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "settings-ok":
            api_key_input = self.query_one("#settings-openai-api-key", Input)
            api_key = api_key_input.value
            if api_key:
                try:
                    openai.api_key = api_key
                    # see if we can load models from the API
                    openai.Model.list()
                    marvin.settings.openai_api_key = api_key
                    dotenv.set_key(str(ENV_FILE), "MARVIN_OPENAI_API_KEY", api_key)
                    self.app.pop_screen()
                except Exception as exc:
                    api_key_input.value = ""
                    error = self.query_one(".api-key-info")
                    error.update(f"Status: ❌\n\n{repr(exc)}")
                    error.add_class("error")
            else:
                self.app.pop_screen()


class SettingsScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def compose(self) -> ComposeResult:
        yield SettingsDialogue()

    def action_dismiss(self) -> None:
        self.app.pop_screen()


class BotsDialogue(Container):
    def compose(self) -> ComposeResult:
        yield Label("[b]Choose a bot[/]")
        with Container(id="bots-info-container"):
            yield BotsOptionList(id="bots-option-list")
            yield BotsInfo(self.app.bot, id="bots-info")
        yield Button("OK", variant="success", id="bots-ok")

    def on_bots_option_list_bot_highlighted(self, event: BotsOptionList.BotHighlighted):
        self.query_one("#bots-info", BotsInfo).bot = event.bot


class BotsScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def compose(self) -> ComposeResult:
        # yield BotsList()
        yield BotsDialogue()

    def action_dismiss(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "bots-ok":
            self.app.bot = self.query_one("#bots-option-list", BotsOptionList).bot
            self.app.pop_screen()
            self.app.query_one("#message-input", Input).focus()


class MainScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Sidebar(id="sidebar")
        yield Conversation(id="conversation")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.value = ""
        conversation = self.query_one("Conversation", Conversation)
        await conversation.add_response(UserResponse(event.value))
        self.get_bot_response(event)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "show-settings":
            self.app.push_screen(SettingsScreen())
        elif event.button.id == "show-bots":
            self.app.push_screen(BotsScreen())

    @work
    async def get_bot_response(self, event: Input.Submitted) -> str:
        bot = self.app.bot
        conversation = self.query_one("Conversation", Conversation)
        response = await bot.say(event.value)
        await conversation.add_response(BotResponse(response.content))


class MarvinApp(App):
    CSS_PATH = ["marvin.css", "bots_settings.css"]
    bot: Optional[marvin.Bot] = reactive(None, always_update=True)
    thread: Optional[marvin.models.threads.Thread] = reactive(None, always_update=True)
    mounted = False

    async def on_ready(self) -> None:
        self.push_screen(MainScreen())
        self.bot = await get_default_bot()
        self.mounted = True

    async def watch_bot(self, bot: marvin.Bot) -> None:
        if bot:
            self.thread = None
            self.log.info(f"Bot changed to {bot.name}")
            await self.query_one("#threads", Threads).refresh_threads()
            self.query_one("#bot-name", Label).update(bot.name)

    async def watch_thread(
        self,
        old_thread: Optional[marvin.models.threads.Thread],
        new_thread: Optional[marvin.models.threads.Thread],
    ) -> None:
        if not self.mounted:
            return
        self.log.info(f"Thread changed to {new_thread.id if new_thread else None}")

        if self.bot:
            if new_thread:
                await self.bot.set_thread(thread_id=new_thread.id)
            else:
                await self.bot.reset_thread()

        # refresh threads
        await self.query_one("#threads", Threads).refresh_threads()
        # refresh conversation
        await self.query_one("Conversation", Conversation).refresh_messages()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-new-thread":
            self.thread = None
            self.app.query_one("#message-input", Input).focus()
        elif event.button.id == "delete-thread":
            if self.thread:
                threads = self.query_one("#threads", Threads)
                current_highlight = threads.highlighted
                await marvin.api.threads.update_thread(
                    thread_id=self.thread.id,
                    thread=marvin.models.threads.ThreadUpdate(is_visible=False),
                )
                await threads.refresh_threads()
                if threads.option_count > 0:
                    threads.highlighted = min(
                        max(0, current_highlight - 1), threads.option_count - 1
                    )
                    threads.action_select()
                else:
                    self.thread = None
                self.app.query_one("#message-input", Input).focus()


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
