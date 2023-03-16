from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static


class Marvin(App):
    CSS_PATH = "tui.css"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header("hi")
        yield Static("Hello Worlasdfd")
        yield Static("Sidebar", id="sidebar")
        yield Static("hi" * 10, id="body")
        yield Footer()
