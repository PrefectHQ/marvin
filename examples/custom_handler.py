import marvin
from marvin.engine.events import UserMessageEvent
from marvin.handlers.print_handler import MessagePanel, PrintHandler


class ShowPromptHandler(PrintHandler):
    """
    Extends the default PrintHandler with a single override that
    prints the initial user prompt before the agent response.
    """

    def on_user_message(self, event: UserMessageEvent):
        raw = getattr(event.message, "content", event.message)
        content = (
            "\n".join(map(str, raw)) if isinstance(raw, (list, tuple)) else str(raw)
        )
        if not content:
            return

        panel_id = str(event.id)
        self.panels[panel_id] = MessagePanel(
            id=panel_id,
            agent_name="User",
            timestamp=self.format_timestamp(event.timestamp),
            content=content,
        )
        self.update_display()


if __name__ == "__main__":
    # run any marvin task with our custom handler
    marvin.summarize(
        "the entire kendrick-drake beef",
        handlers=[ShowPromptHandler()],
    )
