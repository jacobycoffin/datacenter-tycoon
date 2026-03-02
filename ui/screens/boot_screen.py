import asyncio
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import RichLog, Input, Static
from textual.containers import Horizontal
from game.save import _DEFAULT_SAVES_DIR


def _attr(obj, key, default=0):
    """Get an attribute from either a dataclass instance or a plain dict (after JSON load)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

BOOT_LINES = [
    "DATACENTER OS v2.0.0",
    "Copyright (C) 2026 Datacenter Tycoon Corp",
    "",
    "Initializing memory...             [bold green][ OK ][/]",
    "Loading kernel modules...          [bold green][ OK ][/]",
    "Mounting filesystems...            [bold green][ OK ][/]",
    "Starting network services...       [bold green][ OK ][/]",
    "[#9d4edd]──────────────────────────────────────────[/]",
    "[#9d4edd] DATACENTER TYCOON TERMINAL[/]",
    "[#9d4edd]──────────────────────────────────────────[/]",
]

class BootScreen(Screen):
    _stage: str = "animating"
    _company_name: str = ""

    def compose(self) -> ComposeResult:
        yield RichLog(id="boot-log", markup=True, highlight=False)
        with Horizontal(id="boot-input-row"):
            yield Static("", id="boot-prompt")
            yield Input(id="boot-input", placeholder="")

    def on_mount(self) -> None:
        self.query_one("#boot-input", Input).disabled = True
        self.run_worker(self._run_boot(), exclusive=True)

    async def _run_boot(self) -> None:
        log = self.query_one("#boot-log", RichLog)
        for line in BOOT_LINES:
            log.write(line)
            await asyncio.sleep(0.06)

        # Check for save files (use absolute path so CWD doesn't matter)
        saves = sorted(
            _DEFAULT_SAVES_DIR.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if saves:
            await self._returning_player(saves[0].stem)
        else:
            await self._new_player()

    async def _new_player(self) -> None:
        log = self.query_one("#boot-log", RichLog)
        log.write("")
        log.write("No existing session found.")
        log.write("")
        inp = self.query_one("#boot-input", Input)
        prompt = self.query_one("#boot-prompt", Static)
        prompt.update("Enter company name: ")
        inp.disabled = False
        inp.focus()
        self._stage = "name"

    async def _returning_player(self, company_name: str) -> None:
        from game.save import load_game
        log = self.query_one("#boot-log", RichLog)
        try:
            state = load_game(company_name)
        except Exception as e:
            log.write(f"[red]Save file could not be loaded: {e}[/]")
            log.write("[yellow]Starting new game...[/]")
            await self._new_player()
            return
        if state is None:
            await self._new_player()
            return
        self.app.state = state
        log.write("")

        monthly_revenue = sum(_attr(c, "monthly_revenue") for c in state.active_contracts)
        monthly_rent = sum(_attr(r, "monthly_rent") for r in state.racks)
        monthly_loans = sum(_attr(l, "monthly_payment") for l in state.loans)
        net_monthly = monthly_revenue - monthly_rent - monthly_loans
        net_color = "green" if net_monthly >= 0 else "red"
        net_sign = "+" if net_monthly >= 0 else ""

        log.write(f"Welcome back, [bold #00ff41]{state.company_name}[/].  Day {state.day}.")
        log.write("")
        log.write(f"  Cash:             [#00ff41]${state.cash:>12,.2f}[/]")
        log.write(f"  Active contracts: {len(state.active_contracts)}  ([#00ff41]+${monthly_revenue:,.2f}/mo[/])")
        log.write(f"  Rack rent:        [red]-${monthly_rent:,.2f}/mo[/]  ({len(state.racks)} rack{'s' if len(state.racks)!=1 else ''})")
        log.write(f"  Loan payments:    [red]-${monthly_loans:,.2f}/mo[/]")
        log.write(f"  [#3a7a3a]──────────────────────────[/]")
        log.write(f"  Net monthly:      [{net_color}]{net_sign}${net_monthly:,.2f}/mo[/]")
        log.write("")
        log.write("Type [bold #9d4edd]'help'[/] for available commands.")
        log.write("")

        await asyncio.sleep(0.5)
        await self._launch_terminal()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        inp = self.query_one("#boot-input", Input)
        log = self.query_one("#boot-log", RichLog)
        prompt = self.query_one("#boot-prompt", Static)

        if self._stage == "name":
            if not value:
                return
            self._company_name = value
            log.write(f"Enter company name: {value}")
            inp.clear()
            prompt.update("Select difficulty [easy/normal/hard]: ")
            self._stage = "difficulty"

        elif self._stage == "difficulty":
            diff = value.lower()
            if diff not in ("easy", "normal", "hard"):
                log.write("[red]Please enter easy, normal, or hard[/]")
                return
            log.write(f"Select difficulty [easy/normal/hard]: {diff}")
            inp.disabled = True
            prompt.update("")
            self._stage = "done"
            self.run_worker(self._finish_new_game(self._company_name, diff), exclusive=True)

    async def _finish_new_game(self, name: str, difficulty: str) -> None:
        from game.engine import initialize_new_game
        from game.save import save_game
        log = self.query_one("#boot-log", RichLog)
        await asyncio.sleep(0.1)
        log.write("")
        log.write("Creating session...                [bold green][ OK ][/]")
        await asyncio.sleep(0.06)
        log.write("Initializing accounts...           [bold green][ OK ][/]")
        await asyncio.sleep(0.06)
        log.write("Provisioning first rack...         [bold green][ OK ][/]")
        await asyncio.sleep(0.06)
        log.write("")

        state = initialize_new_game(name, difficulty)
        save_game(state)
        self.app.state = state

        log.write("Welcome to [bold #9d4edd]DATACENTER TYCOON[/].")
        log.write(f"You have been allocated [#00ff41]${state.cash:,.2f}[/] in seed funding.")
        log.write("")
        log.write("Type [bold #9d4edd]'help'[/] to begin.")
        log.write("")
        await asyncio.sleep(0.5)
        await self._launch_terminal()

    async def _launch_terminal(self) -> None:
        from ui.screens.terminal_screen import TerminalScreen
        self.app.push_screen(TerminalScreen())
