from __future__ import annotations

from textual.app import App, ComposeResult
from game.models import GameState
from game.save import save_game


class DatacenterApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "Datacenter Tycoon"

    def __init__(self) -> None:
        super().__init__()
        self.state: GameState | None = None

    def on_mount(self) -> None:
        from ui.screens.boot_screen import BootScreen
        self.push_screen(BootScreen())
