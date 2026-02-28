from textual.app import App, ComposeResult
from textual.binding import Binding
from game.models import GameState
from game.save import save_game


class DatacenterApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "DATACENTER TYCOON"
    BINDINGS = [
        Binding("ctrl+q", "quit_and_save", "Save & Quit"),
        Binding("s", "save_game_action", "Save"),
        Binding("?", "goto_glossary", "Glossary"),
    ]

    def __init__(self):
        super().__init__()
        self.state: GameState | None = None

    def on_mount(self) -> None:
        from ui.screens.new_game import NewGameScreen
        self.push_screen(NewGameScreen())

    def action_quit_and_save(self) -> None:
        if self.state:
            save_game(self.state)
        self.exit()

    def action_save_game_action(self) -> None:
        if self.state:
            save_game(self.state)
            self.notify("Game saved!", timeout=2)

    def action_goto_glossary(self) -> None:
        from textual.widgets import TabbedContent
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            tabs.active = "tab-glossary"
        except Exception:
            pass
