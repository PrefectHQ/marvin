import asyncio
import inspect
import json
import logging
import re
import warnings
from functools import partial
from typing import Optional

import dotenv
import openai
import pendulum
import pyperclip
from fastapi import HTTPException
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.events import Enter, Leave
from textual.logging import TextualHandler
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
from marvin.models.ids import MessageID, ThreadID
from marvin.utilities.strings import jinja_env

logging.basicConfig(
    level="NOTSET",
    handlers=[TextualHandler()],
)

PLUGIN_REGEX = re.compile(r'({\s*"mode":\s*"plugins")', re.DOTALL)
PLUGIN_TASKS_REGEX = re.compile(r'"tasks":\s*(\[.*?\])', re.DOTALL)


@marvin.ai_fn(llm_model_name="gpt-3.5-turbo", llm_model_temperature=1)
async def name_thread(history: str, personality: str, current_name: str = None) -> str:
    """
    This function generates a short, relevant name for the provided thread
    `history`. The name should be fewer than five words and must reflect the
    user's intent or objective in a clear, fun way. Return only the name, no
    other commentary. It can include emojis and use sentence capitalization, but
    should not end with a period. The name itself should be entirely based on
    the provided `history`, but the tone should reflect the provided
    `personality`. If the thread has a `current_name` already, it is provided
    and you can choose to keep it unchanged.
    """


class Threads(OptionList):
    lock = asyncio.Lock()
    threads = []

    class ThreadSelected(Message):
        """Thread selected."""

        def __init__(self, thread_id: ThreadID) -> None:
            self.thread_id = thread_id
            super().__init__()

    async def refresh_threads(self):
        async with self.lock:
            self.highlighted = None
            self.clear_options()

            if self.app.bot:
                self.threads = await marvin.api.threads.get_threads_by_bot(
                    bot_name=self.app.bot.name
                )
                for i, t in enumerate(self.threads):
                    self.add_option(Option(t.name or "New conversation", id=t.id))
                    self.add_option(None)
                    if t.id == self.app.thread_id:
                        self.highlighted = i

    async def on_mount(self) -> None:
        await self.refresh_threads()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        self.post_message(self.ThreadSelected(thread_id=event.option.id))


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
        self.show_vertical_scrollbar = True
        self.scroll_to_highlight()

    async def on_mount(self) -> None:
        await self.refresh_bots()

    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ):
        self.bot = await marvin.Bot.load(event.option.id)
        self.post_message(self.BotHighlighted(self.bot))


class BotInfo(Container):
    bot = reactive(None)

    def __init__(self, bot: marvin.models.bots.BotConfig = None, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot

    def compose(self):
        with Container(id="bot-info-outer-container"):
            with Container(
                id="bot-info-description-container", classes="bot-info-container"
            ):
                yield Label("Description", classes="bot-info label")
                yield Label("", classes="bot-info text", id="bot-info-description")

            with Container(
                id="bot-info-personality-container", classes="bot-info-container"
            ):
                yield Label("Personality", classes="bot-info label")
                yield Label("", classes="bot-info text", id="bot-info-personality")

    def watch_bot(self, bot: marvin.models.bots.BotConfig):
        if self.app.is_mounted(self):
            description = self.query_one("#bot-info-description", Label)
            personality = self.query_one("#bot-info-personality", Label)
            description.update(bot.description)
            personality.update(bot.personality)


class Sidebar(VerticalScroll):
    def compose(self) -> ComposeResult:
        with Horizontal(id="bot-name-container"):
            yield Label("Bot: ", id="bot-name-label")
            yield Label(
                self.app.bot.name if self.app.bot else "No bot selected", id="bot-name"
            )
        yield Label("[bold]Threads[/]", classes="sidebar-title")
        yield Threads(id="threads")
        yield Button("Bots \[b]", variant="success", id="show-bots")
        yield Button("New thread \[n]", id="create-new-thread", variant="primary")
        yield Button("Delete thread \[x]", id="delete-thread", variant="error")
        with Horizontal(id="meta-buttons-container"):
            yield Button("Settings \[s]", id="show-settings")
            yield Button("Quit \[ctrl-c]", id="quit")


class ResponseHover(Message):
    pass


class ResponseBody(Markdown):
    text: str = ""

    def update(self, markdown: str):
        self.text = markdown
        super().update(markdown)

    def on_enter(self):
        self.post_message(ResponseHover())


class Response(Container):
    body = None
    stream_finished: bool = False

    def __init__(self, message: marvin.models.threads.Message, **kwargs) -> None:
        classes = kwargs.setdefault("classes", "")
        kwargs["classes"] = f"{classes} response".strip()
        self.message = message
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        self.body = ResponseBody(self.message.content, classes="response-body markdown")
        self.body.border_title = (
            "You" if self.message.role == "user" else self.message.name
        )
        self.body.border_subtitle = (
            pendulum.instance(self.message.timestamp).in_tz("local").format("h:mm:ss A")
        )
        self.border_title = "Edit message"

        yield self.body
        with Horizontal(classes="edit-buttons-container hidden"):
            yield Button("Copy", variant="default", id="copy-message")
            yield Button("Delete", variant="error", id="delete-message")

    def on_click(self):
        self.action_toggle_buttons()

    def on_response_hover(self, event: ResponseHover):
        """
        This is an "enter" event bubbled up from the ResponseBody, since the
        default "Leave" is triggered when hovering on child widgets. This keeps
        the hover class even when hovering on the child widget.
        """
        self.add_class("response-hover")

    def on_enter(self, event: Enter):
        self.add_class("response-hover")

    def on_leave(self, event: Leave):
        self.remove_class("response-hover")

    def action_toggle_buttons(self):
        self.toggle_class("show-edit-buttons")
        self.body.toggle_class("show-edit-buttons")
        self.query_one(".edit-buttons-container").toggle_class("hidden")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "copy-message":
            pyperclip.copy(self.message.content)
            self.action_toggle_buttons()

        elif event.button.id == "delete-message":
            self.app.push_screen(ConfirmMessageDeleteScreen(self.message.id))


class UserResponse(Response):
    def __init__(self, message: marvin.models.threads.Message, **kwargs) -> None:
        classes = kwargs.setdefault("classes", "")
        kwargs["classes"] = f"{classes} user-response".strip()
        super().__init__(message=message, **kwargs)


class BotResponse(Response):
    def __init__(self, message: marvin.models.threads.Message, **kwargs) -> None:
        classes = kwargs.setdefault("classes", "")
        kwargs["classes"] = f"{classes} bot-response".strip()
        super().__init__(message=message, **kwargs)


class Conversation(Container):
    bot_name = reactive(None, layout=True)

    def watch_bot_name(self, bot_name: str):
        with self.app.batch_update():
            bot_name_label = self.query_one("#empty-thread-bot-name", Label)
            bot_description_label = self.query_one(
                "#empty-thread-bot-description", Label
            )

            if bot_name:
                bot_name_label.update(
                    f"Send a message to [bold green]{self.bot_name}[/]!"
                )
                if self.app.bot.description:
                    bot_description_label.update(f"{self.app.bot.description}")
                    bot_description_label.remove_class("hidden")
                else:
                    bot_description_label.add_class("hidden")

            else:
                bot_description_label.add_class("hidden")
                bot_name_label.update("Send a message to start a thread...")

    def compose(self) -> ComposeResult:
        input = Input(placeholder="Your message", id="message-input")
        input.focus()
        yield input
        with VerticalScroll(id="messages"):
            with Container(id="message-top"):
                with Container(id="empty-thread-container"):
                    yield Label("", id="empty-thread-bot-name")
                    yield Label("", id="empty-thread-bot-description")

    async def add_response(self, response: Response, scroll: bool = True) -> None:
        messages = self.query_one("Conversation #messages", VerticalScroll)
        # wait for the responses to be fully mounted before scrolling
        # to avoid issues with rendering Markdown
        await messages.mount(response)
        if scroll:
            messages.scroll_end(duration=0.2)

        # show / hide the empty thread message
        empty = self.query_one("Conversation #empty-thread-container")
        empty.add_class("hidden")

    def clear_responses(self) -> None:
        responses = self.query("Response")
        for response in responses:
            response.remove()
        self.bot_name = getattr(self.app.bot, "name")
        empty = self.query_one("Conversation #empty-thread-container")
        empty.remove_class("hidden")

    async def refresh_messages(self):
        if self.app.bot_responding:
            return
        with self.app.batch_update():
            self.clear_responses()
            messages = await marvin.api.threads.get_messages(
                thread_id=self.app.thread_id, limit=100
            )
            for message in messages:
                if message.role == "user":
                    await self.add_response(UserResponse(message), scroll=False)
                elif message.role == "bot":
                    await self.add_response(BotResponse(message), scroll=False)

            # scroll to bottom
            messages = self.query_one("Conversation #messages", VerticalScroll)
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
                yield Static(text or "", classes="text")

    def watch_data(self, data: dict):
        self.query().remove()

        width = 0
        if data:
            for label, text in data.items():
                width = max(width, len(label) + 2)
                self.mount(
                    Horizontal(
                        Label(f"{label}:", classes="label"),
                        Static(text or "", classes="text"),
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

    def action_ok(self):
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

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "settings-ok":
            self.action_ok()


class SettingsScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def compose(self) -> ComposeResult:
        yield SettingsDialogue()

    def action_dismiss(self) -> None:
        self.app.pop_screen()


class ConfirmMessageDeleteDialogue(Container):
    def __init__(self, message_id: MessageID, **kwargs):
        self.message_id = message_id
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Label(
            (
                "This will delete all the messages from here on, allowing you to"
                " restart the conversation from this point. Are you sure you want to"
                " continue?"
            ),
            classes="confirm-delete-message",
        )
        with Horizontal():
            yield Button("Cancel", variant="default", id="cancel")
            yield Button("Delete", variant="error", id="delete")

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "cancel":
            self.action_dismiss()
        elif event.button.id == "delete":
            await self.action_delete()

    def action_dismiss(self) -> None:
        self.app.pop_screen()

    async def action_delete(self) -> None:
        await marvin.api.threads.delete_message(
            message_id=self.message_id, delete_following_messages=True
        )
        self.action_dismiss()
        # refresh conversation
        conversation = self.app.query_one("Conversation", Conversation)
        await conversation.refresh_messages()


class ConfirmMessageDeleteScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def __init__(self, message_id: MessageID, **kwargs):
        self.message_id = message_id
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield ConfirmMessageDeleteDialogue(message_id=self.message_id)


class DatabaseUpgradeDialogue(Container):
    def compose(self) -> ComposeResult:
        yield Label(
            "Your database needs to be upgraded to the latest version. Please click"
            ' "Upgrade DB" to automatically upgrade it.'
        )
        yield Button("Upgrade DB", variant="warning", id="upgrade-db")

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "upgrade-db":
            event.button.label = "Upgrading..."
            marvin.infra.database.alembic_upgrade()
            self.app.database_ready = True
            self.app.pop_screen()


class DatabaseUpgradeScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def compose(self) -> ComposeResult:
        yield DatabaseUpgradeDialogue()

    def action_dismiss(self) -> None:
        self.app.pop_screen()


class BotsDialogue(Container):
    def compose(self) -> ComposeResult:
        yield Label("[b]Choose a bot[/]")
        with Container(id="bots-info-container"):
            options = BotsOptionList(id="bots-option-list")
            options.focus()
            yield options
            yield BotInfo(self.app.bot, id="bots-info")
        with Horizontal():
            yield Button("OK", variant="success", id="bots-ok")
            yield Button(
                "Install default bots",
                variant="default",
                id="install-default-bots",
            )

    def on_bots_option_list_bot_highlighted(self, event: BotsOptionList.BotHighlighted):
        self.query_one("#bots-info", BotInfo).bot = event.bot


class BotsScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def compose(self) -> ComposeResult:
        yield BotsDialogue()

    def action_dismiss(self) -> None:
        self.app.pop_screen()

    def action_ok(self) -> None:
        bot_list = self.query_one("#bots-option-list", BotsOptionList)
        if bot_list.bot:
            self.app.bot = bot_list.bot
        self.app.pop_screen()
        self.app.query_one("#message-input", Input).focus()

    async def action_install_default_bots(self) -> None:
        await marvin.bots.install_bots()
        await self.query_one("#bots-option-list", BotsOptionList).refresh_bots()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "bots-ok":
            self.action_ok()
        elif event.button.id == "install-default-bots":
            await self.action_install_default_bots()


class MainScreen(Screen):
    BINDINGS = [
        ("escape", "focus_threads", "Focus on Threads"),
        ("b", "show_bots_screen", "Show Bots"),
        ("n", "new_thread", "New Thread"),
        ("s", "show_settings_screen", "Show Settings"),
        ("x", "delete_thread", "Delete Thread"),
        ("k", "scroll_up_messages", "Scroll Up"),
        ("j", "scroll_down_messages", "Scroll Down"),
        ("u", "page_up_messages", "Page Up"),
        ("d", "page_down_messages", "Page Down"),
    ]

    def action_focus_threads(self) -> None:
        self.query_one("#threads", Threads).focus()

    def action_focus_message(self) -> None:
        self.query_one("#message-input", Input).focus()

    def action_show_bots_screen(self) -> None:
        self.app.push_screen(BotsScreen())

    def action_show_settings_screen(self) -> None:
        self.app.push_screen(SettingsScreen())

    def action_scroll_up_messages(self) -> None:
        messages = self.query_one("Conversation #messages", VerticalScroll)
        messages.scroll_up(duration=0.1)

    def action_scroll_down_messages(self) -> None:
        messages = self.query_one("Conversation #messages", VerticalScroll)
        messages.scroll_down(duration=0.1)

    def action_page_up_messages(self) -> None:
        messages = self.query_one("Conversation #messages", VerticalScroll)
        messages.scroll_page_up(duration=0.1)

    def action_page_down_messages(self) -> None:
        messages = self.query_one("Conversation #messages", VerticalScroll)
        messages.scroll_page_down(duration=0.1)

    def compose(self) -> ComposeResult:
        yield Sidebar(id="sidebar")
        yield Conversation(id="conversation")

    def on_mount(self):
        if not marvin.settings.openai_api_key.get_secret_value():
            self.set_timer(0.5, self.action_show_settings_screen)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.disabled:
            return
        elif not event.input.value:
            return
        conversation = self.query_one("Conversation", Conversation)
        await conversation.add_response(
            UserResponse(
                marvin.models.threads.Message(
                    name="User", role="user", content=event.value
                )
            )
        )
        self.get_bot_response(event)
        event.input.value = ""

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "show-settings":
            self.action_show_settings_screen()
        elif event.button.id == "show-bots":
            self.action_show_bots_screen()
        elif event.button.id == "create-new-thread":
            self.action_new_thread()
        elif event.button.id == "delete-thread":
            await self.action_delete_thread()
        elif event.button.id == "quit":
            self.app.exit()

    def stream_bot_response(self, token_buffer: list[str], response: BotResponse):
        streaming_response = "".join(token_buffer)

        if not self.app.is_mounted(response):
            conversation = self.query_one("Conversation", Conversation)
            asyncio.run(conversation.add_response(response))

        # the bot is going to use a plugin
        if PLUGIN_REGEX.search(streaming_response):
            try:
                if tasks_match := PLUGIN_TASKS_REGEX.search(streaming_response):
                    tasks = json.loads(tasks_match.group(1))
                    template = inspect.cleandoc(
                        """
                        Using plugins to complete tasks:
                        {% for task in tasks %}
                        - {{ task.name}}
                        {% endfor %}
                        """
                    )
                    response.body.update(
                        jinja_env.from_string(template).render(tasks=tasks)
                    )
                else:
                    response.body.update("Using plugins...")
            except json.JSONDecodeError:
                response.body.update("Using plugins...")

        else:
            response.message.content = streaming_response
            response.body.update(streaming_response)

            # scroll to bottom
            messages = self.query_one("Conversation #messages", VerticalScroll)
            messages.scroll_end(duration=0.1)

    @work
    async def get_bot_response(self, event: Input.Submitted) -> str:
        bot = self.app.bot
        self.app.bot_responding = True
        try:
            bot_response = BotResponse(
                marvin.models.threads.Message(
                    role="bot",
                    name=self.app.bot.name,
                    bot_id=self.app.bot.id,
                    content="",
                )
            )

            response = await bot.say(
                event.value,
                on_token_callback=partial(
                    self.stream_bot_response, response=bot_response
                ),
            )

            # call once to populate the response in case there was any trouble
            # streaming live
            self.stream_bot_response(
                token_buffer=[response.content], response=bot_response
            )

            # if this is one of the first few responses, rename the thread
            # appropriately
            bot_responses = self.query("BotResponse")
            if 1 <= len(bot_responses) <= 5:
                self.action_rename_thread()

            # update the bot response with the actual message id
            bot_response.message.id = response.id

            # update the last user response with the actual message id
            messages = await marvin.api.threads.get_messages(
                thread_id=self.app.thread_id, limit=5
            )
            last_user_message = next(
                (m for m in reversed(messages) if m.role == "user"), None
            )
            if last_user_message:
                self.query("UserResponse").last().message.id = last_user_message.id
        finally:
            self.app.bot_responding = False

    @work
    async def action_rename_thread(self):
        # first, make sure the thread exists
        try:
            thread = await marvin.api.threads.get_thread(thread_id=self.app.thread_id)
        except HTTPException:
            thread = await marvin.api.threads.create_thread(
                thread=marvin.models.threads.Thread(
                    id=self.app.thread_id, is_visible=True
                )
            )

        # generate a new thread from the thread history
        messages = await marvin.api.threads.get_messages(
            thread_id=self.app.thread_id, limit=10
        )
        name = await name_thread(
            history="\n\n".join(
                ["{}: {}".format(m.role.capitalize(), m.content) for m in messages]
            ),
            personality=getattr(self.app.bot, "personality", None),
            current_name=thread.name,
        )

        # update thead name
        await marvin.api.threads.update_thread(
            thread_id=self.app.thread_id,
            thread=marvin.models.threads.ThreadUpdate(name=name or "New convesation"),
        )

        # refresh the thread list
        await self.app.query_one("#threads", Threads).refresh_threads()

    def action_new_thread(self) -> None:
        self.post_message(Threads.ThreadSelected(thread_id=ThreadID.new()))

    async def action_delete_thread(self) -> None:
        threads = self.query_one("#threads", Threads)
        current_highlight = threads.highlighted

        if current_highlight is not None:
            thread = threads.threads[current_highlight]
            await marvin.api.threads.update_thread(
                thread_id=thread.id,
                thread=marvin.models.threads.ThreadUpdate(is_visible=False),
            )
            await threads.refresh_threads()
            if threads.option_count > 0:
                threads.highlighted = min(
                    max(0, current_highlight), threads.option_count - 1
                )
                threads.action_select()
            else:
                self.app.thread_id = ThreadID.new()

    def on_threads_thread_selected(self, event: Threads.ThreadSelected) -> None:
        self.action_focus_message()


class MarvinApp(App):
    CSS_PATH = ["tui.css"]
    bot: Optional[marvin.Bot] = reactive(None, always_update=True, layout=True)
    thread_id: ThreadID = reactive(ThreadID.new, always_update=True, layout=True)
    thread: Optional[marvin.models.threads.Thread] = reactive(
        None, always_update=True, layout=True
    )
    bot_responding: bool = reactive(False)
    is_ready: bool = False
    database_ready: bool = reactive(False)

    def __init__(self, default_bot: marvin.Bot = None, **kwargs):
        super().__init__(**kwargs)

        if default_bot is None:
            default_bot = marvin.bots.meta.marvin_bot
        default_bot.save_sync(if_exists="update")
        self._default_bot = default_bot

    async def check_database(self):
        # trap warnings as errors
        warnings.filterwarnings("error")

        try:
            await marvin.infra.database.check_alembic_version()
            self.database_ready = True
        except marvin.infra.database.DatabaseWarning as w:
            if "Database migrations are not up to date" in str(w):
                self.push_screen(DatabaseUpgradeScreen())
            else:
                raise ValueError("Unknown database warning: {}".format(w))

        # reset warning behavior
        warnings.resetwarnings()

    async def watch_database_ready(self, database_ready: bool) -> None:
        if database_ready:
            self.bot = self._default_bot
            await self.bot.set_thread(self.thread_id)
            self.is_ready = True

    async def on_ready(self) -> None:
        self.push_screen(MainScreen())
        await self.check_database()

    async def watch_bot(self, bot: marvin.Bot) -> None:
        if not self.is_ready:
            return

        if bot:
            self.thread_id = ThreadID.new()
            self.log.info(f"Bot changed to {bot.name}")
            await self.query_one("#threads", Threads).refresh_threads()
            self.query_one("#bot-name", Label).update(bot.name)

    async def watch_thread_id(self, thread_id: ThreadID) -> None:
        if not self.is_ready:
            return
        self.log.info(f"Thread changed to {thread_id}")

        if self.bot:
            await self.bot.set_thread(thread_id=thread_id)

        # refresh threads
        await self.query_one("#threads", Threads).refresh_threads()
        # refresh conversation
        conversation = self.query_one("Conversation", Conversation)
        await conversation.refresh_messages()

    def on_threads_thread_selected(self, event: Threads.ThreadSelected) -> None:
        self.thread_id = event.thread_id

    def watch_bot_responding(self, is_responding: bool) -> None:
        if not self.is_ready:
            return
        input_widget = self.query_one("#message-input", Input)
        if is_responding:
            input_widget.disabled = True
        else:
            input_widget.disabled = False


if __name__ == "__main__":
    app = MarvinApp()
    app.run()
