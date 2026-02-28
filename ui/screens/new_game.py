from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static
from textual.containers import Center, Vertical

LOGO = r"""
  ____        _                      _
 |  _ \  __ _| |_ __ _  ___ ___ _ _| |_ ___ _ __
 | | | |/ _` | __/ _` |/ __/ _ \ '__| __/ _ \ '__|
 | |_| | (_| | || (_| | (_|  __/ |  | ||  __/ |
 |____/ \__,_|\__\__,_|\___\___|_|   \__\___|_|
  _____
 |_   _|   _  ___ ___   ___  _ __
   | || | | |/ __/ _ \ / _ \| '_ \
   | || |_| | (_| (_) | (_) | | | |
   |_| \__, |\___\___/ \___/|_| |_|
        |___/
"""


class NewGameScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Center(
            Vertical(
                Static(LOGO, id="logo"),
                Label("Company Name:"),
                Input(placeholder="e.g. Apex Data Solutions", id="company-name"),
                Label("Difficulty:"),
                Label("  [E] Easy — $75,000 starting cash", id="diff-easy"),
                Label("  [N] Normal — $50,000 starting cash (recommended)", id="diff-normal"),
                Label("  [H] Hard — $25,000 starting cash", id="diff-hard"),
                Button("Start — Normal ($50,000)", id="btn-normal", variant="success"),
                Button("Start — Easy ($75,000)", id="btn-easy", variant="default"),
                Button("Start — Hard ($25,000)", id="btn-hard", variant="error"),
                Button("Load Existing Game", id="btn-load", variant="primary"),
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from game.engine import initialize_new_game
        from game.save import load_game
        from ui.screens.main_screen import MainScreen

        name_input = self.query_one("#company-name", Input).value.strip()
        name = name_input or "My Data Center"

        difficulty_map = {
            "btn-normal": "normal",
            "btn-easy": "easy",
            "btn-hard": "hard",
        }

        if event.button.id in difficulty_map:
            difficulty = difficulty_map[event.button.id]
            state = initialize_new_game(name, difficulty)
            self.app.state = state
            self.app.switch_screen(MainScreen())

        elif event.button.id == "btn-load":
            if not name_input:
                self.notify("Enter your company name to load a save.", severity="warning")
                return
            state = load_game(name_input)
            if state:
                self.app.state = state
                self.app.switch_screen(MainScreen())
            else:
                self.notify(f"No save found for '{name_input}'.", severity="error")
