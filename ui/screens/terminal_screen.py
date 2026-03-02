from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, RichLog, Static
from textual.containers import Horizontal


class TerminalScreen(Screen):
    """Hacker-terminal style main game screen."""

    def __init__(self) -> None:
        super().__init__()
        self._prompt_text: str = "[user@datacenter ~]$ "

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-area"):
            yield Static("", id="pin-panel")
            yield Static("", id="open-panel")
        yield RichLog(id="terminal", markup=True, highlight=False, max_lines=500)
        with Horizontal(id="input-row"):
            yield Static(self._prompt_text, id="prompt-label")
            yield Input(id="cmd-input", placeholder="")

    def on_mount(self) -> None:
        self._prompt_text = self._prompt_str()
        self.query_one("#prompt-label", Static).update(self._prompt_text)
        self._log("Type [bold]'help'[/] to see available commands.")
        self.query_one("#cmd-input", Input).focus()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _prompt_str(self) -> str:
        name = self.app.state.company_name[:12].lower() if self.app.state else "user"
        return f"[{name}@datacenter ~]$ "

    def _log(self, text: str) -> None:
        self.query_one("#terminal", RichLog).write(text)

    def _refresh_pin_panel(self) -> None:
        pass  # implemented in Task 4

    def _update_visibility(self) -> None:
        pass  # implemented in Task 4

    # ------------------------------------------------------------------ #
    # Input handling
    # ------------------------------------------------------------------ #

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        inp = self.query_one("#cmd-input", Input)
        inp.clear()
        if not raw:
            return
        self._log(f"[bold #00ff41]{self._prompt_text}[/] {raw}")
        self._run_command(raw)
        inp.focus()

    def _run_command(self, raw: str) -> None:
        parts = raw.split()
        cmd = parts[0].lower() if parts else ""
        args = parts[1:]
        dispatch = {
            "help": self._cmd_help,
            "day": self._cmd_day,
            "save": self._cmd_save,
            "view": self._cmd_view,
            "pin": self._cmd_pin,
            "unpin": self._cmd_unpin,
            "open": self._cmd_open,
            "close": self._cmd_close,
            "buy": self._cmd_buy,
            "sell": self._cmd_sell,
            "transfer": self._cmd_transfer,
            "loan": self._cmd_loan,
            "bond": self._cmd_bond,
            "sellbond": self._cmd_sellbond,
            "accept": self._cmd_accept,
            "decline": self._cmd_decline,
            "negotiate": self._cmd_negotiate,
            "assign": self._cmd_assign,
            "gig": self._cmd_gig,
            "buyhw": self._cmd_buyhw,
            "assemble": self._cmd_assemble,
            "install": self._cmd_install,
            "repair": self._cmd_repair,
            "rent": self._cmd_rent,
        }
        handler = dispatch.get(cmd)
        if handler:
            handler(args)
        else:
            self._log(f"[red]Unknown command: '{cmd}'. Type 'help' for available commands.[/]")

    # ------------------------------------------------------------------ #
    # Fully implemented commands
    # ------------------------------------------------------------------ #

    def _cmd_help(self, args: list[str]) -> None:
        self._log(
            "Available commands:\n"
            "  view <target>     — Print a report (cash, contracts, servers, market, loans, bonds, inventory, racks, gigs, all)\n"
            "  pin <metric>      — Pin a metric to the top panel (cash, day, income, rep, credit, net)\n"
            "  unpin <metric>    — Remove a pinned metric\n"
            "  pin clear         — Clear all pinned metrics\n"
            "  open <target>     — Open a panel (store, contracts, market, servers, racks, gigs, banking)\n"
            "  close             — Close the open panel\n"
            "\n"
            "  day               — Advance one day\n"
            "  save              — Save game\n"
            "  buy <qty> <ticker>   — Buy stocks\n"
            "  sell <qty> <ticker>  — Sell stocks\n"
            "  transfer <to|from> savings <amount>  — Move money between checking/savings\n"
            "  loan <amount> [term]  — Take out a loan (term: 6, 12, or 24 months)\n"
            "  bond <amount> [days]  — Buy a bond (30, 60, 90, or 180 days)\n"
            "  sellbond <id>         — Sell a bond early\n"
            "  accept <n>            — Accept contract #n from pending list\n"
            "  decline <n>           — Decline contract #n\n"
            "  negotiate <n> <pct>   — Counter-offer (e.g. negotiate 1 15 for +15%)\n"
            "  assign <server_id> <contract_id>  — Assign server to contract\n"
            "  gig <n>               — Accept gig #n from gig board\n"
            "  buyhw <hw_id>         — Buy hardware component (e.g. buyhw cpu_mid)\n"
            "  assemble <name> <cpu> <ram[,ram]> <storage[,storage]> <nic>  — Assemble server\n"
            "  install <server_id> <rack_id>  — Install server in rack\n"
            "  repair <server_id>    — Repair degraded server\n"
            "  rent                  — Rent another rack"
        )

    def _cmd_day(self, args: list[str]) -> None:
        from game.engine import advance_day
        from game.save import save_game
        if not self.app.state:
            self._log("[red]No active game session.[/]")
            return
        state = advance_day(self.app.state)
        self.app.state = state
        save_game(state)
        self._log(f"[#9d4edd]Day {state.day}[/]")
        for entry in state.event_log[-3:]:
            self._log(f"  [#3a7a3a]{entry}[/]")
        self._refresh_pin_panel()
        if state.cash == -1.0:
            self._log("[bold red]GAME OVER — BANKRUPTCY. Your company has collapsed.[/]")
            self._log("[dim]Save file preserved. Start a new game to try again.[/]")
            self.query_one("#cmd-input", Input).disabled = True

    def _cmd_save(self, args: list[str]) -> None:
        from game.save import save_game
        if not self.app.state:
            self._log("[red]No active game session.[/]")
            return
        save_game(self.app.state)
        self._log("Game saved.")

    # ------------------------------------------------------------------ #
    # Stub commands (implemented in later tasks)
    # ------------------------------------------------------------------ #

    def _cmd_view(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_pin(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_unpin(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_open(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_close(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_buy(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_sell(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_transfer(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_loan(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_bond(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_sellbond(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_accept(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_decline(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_negotiate(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_assign(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_gig(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_buyhw(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_assemble(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_install(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_repair(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")

    def _cmd_rent(self, args: list[str]) -> None:
        self._log("[dim]Command registered — full implementation in next task.[/]")
