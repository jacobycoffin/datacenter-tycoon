from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label

class DatacenterApp(App):
    CSS = """
    Screen { background: #0d1117; }
    """
    TITLE = "DATACENTER TYCOON"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Loading...", id="placeholder")
        yield Footer()
