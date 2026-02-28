from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static
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
                RadioSet(
                    RadioButton("Easy — $75,000 starting cash", id="easy"),
                    RadioButton("Normal — $50,000 starting cash", id="normal", value=True),
                    RadioButton("Hard — $25,000 starting cash", id="hard"),
                    id="difficulty-radio",
                ),
                Button("Start Game", id="start", variant="success"),
                Button("Load Game", id="load", variant="default"),
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from game.engine import initialize_new_game
        from game.save import load_game
        from ui.screens.main_screen import MainScreen

        name_input = self.query_one("#company-name", Input).value.strip()
        name = name_input or "My Data Center"

        if event.button.id == "start":
            radio_set = self.query_one("#difficulty-radio", RadioSet)
            pressed = radio_set.pressed_button
            difficulty = pressed.id if pressed else "normal"
            state = initialize_new_game(name, difficulty)
            self.app.state = state
            self.app.switch_screen(MainScreen())

        elif event.button.id == "load":
            if not name_input:
                self.notify("Enter your company name to load a save.", severity="warning")
                return
            state = load_game(name_input)
            if state:
                self.app.state = state
                self.app.switch_screen(MainScreen())
            else:
                self.notify(f"No save found for '{name_input}'.", severity="error")
