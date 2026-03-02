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
        self._pinned_metrics: dict[str, bool] = {}   # metric name → True (just a set of names)
        self._open_target: str | None = None         # current open panel target, or None

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

    @staticmethod
    def _ga(obj, attr: str, default=0):
        """Get attribute from a dataclass instance or a plain dict (after JSON load)."""
        return obj.get(attr, default) if isinstance(obj, dict) else getattr(obj, attr, default)

    def _refresh_pin_panel(self) -> None:
        if not self._pinned_metrics:
            return
        s = self.app.state
        if not s:
            return
        lines = []
        if "cash" in self._pinned_metrics:
            lines.append(f"Cash  [#00ff41]${s.cash:,.0f}[/]")
        if "day" in self._pinned_metrics:
            lines.append(f"Day   [#00ff41]{s.day}[/]")
        if "income" in self._pinned_metrics or "net" in self._pinned_metrics:
            income = sum(self._ga(c, "monthly_revenue") for c in s.active_contracts)
        if "income" in self._pinned_metrics:
            lines.append(f"Inc   [#00ff41]+${income:,.0f}/mo[/]")
        if "rep" in self._pinned_metrics:
            lines.append(f"Rep   [#00ff41]{s.reputation}[/]")
        if "credit" in self._pinned_metrics:
            lines.append(f"Cred  [#00ff41]{s.credit_score}[/]")
        if "net" in self._pinned_metrics:
            rent = sum(self._ga(r, "monthly_rent") for r in s.racks)
            loans = sum(self._ga(l, "monthly_payment") for l in s.loans)
            net = income - rent - loans
            color = "green" if net >= 0 else "red"
            sign = "+" if net >= 0 else ""
            lines.append(f"Net   [{color}]{sign}${net:,.0f}/mo[/]")
        self.query_one("#pin-panel", Static).update("\n".join(lines))

    def _update_visibility(self) -> None:
        top_area = self.query_one("#top-area", Horizontal)
        pin_panel = self.query_one("#pin-panel", Static)

        has_pin = bool(self._pinned_metrics)
        has_open = self._open_target is not None

        # Show/hide top-area
        if has_pin or has_open:
            top_area.add_class("visible")
        else:
            top_area.remove_class("visible")

        # Show/hide pin-panel
        if has_pin:
            pin_panel.add_class("visible")
        else:
            pin_panel.remove_class("visible")

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
        valid = {"cash", "day", "income", "rep", "credit", "net"}
        if not args:
            self._log("[red]Usage: pin <metric>  or  pin clear[/]")
            self._log(f"  Valid metrics: {', '.join(sorted(valid))}")
            return
        if args[0].lower() == "clear":
            self._pinned_metrics.clear()
            self._update_visibility()
            self._log("Pin panel cleared.")
            return
        metric = args[0].lower()
        if metric not in valid:
            self._log(f"[red]Unknown metric '{metric}'. Valid: {', '.join(sorted(valid))}[/]")
            return
        self._pinned_metrics[metric] = True
        self._update_visibility()
        self._refresh_pin_panel()
        self._log(f"Pinned [#9d4edd]{metric}[/].")

    def _cmd_unpin(self, args: list[str]) -> None:
        if not args:
            self._log("[red]Usage: unpin <metric>[/]")
            return
        metric = args[0].lower()
        if metric not in self._pinned_metrics:
            self._log(f"[yellow]{metric} is not pinned.[/]")
            return
        del self._pinned_metrics[metric]
        self._update_visibility()
        self._refresh_pin_panel()
        self._log(f"Unpinned {metric}.")

    def _cmd_open(self, args: list[str]) -> None:
        valid = {"store", "contracts", "market", "servers", "racks", "gigs", "banking"}
        if not args:
            self._log(f"[red]Usage: open <target>  Valid: {', '.join(sorted(valid))}[/]")
            return
        target = args[0].lower()
        if target not in valid:
            self._log(f"[red]Unknown target '{target}'. Valid: {', '.join(sorted(valid))}[/]")
            return
        self._open_target = target
        self._update_visibility()
        self._render_open_panel()  # stub until Task 6
        self._log(f"Opened [#9d4edd]{target}[/]. Type 'close' to dismiss.")

    def _cmd_close(self, args: list[str]) -> None:
        if self._open_target is None:
            self._log("[yellow]No panel is open.[/]")
            return
        old = self._open_target
        self._open_target = None
        self.query_one("#open-panel", Static).update("")
        self._update_visibility()
        self._log(f"Closed {old} panel.")

    def _render_open_panel(self) -> None:
        """Renders content into #open-panel. Full implementation in Task 6."""
        if self._open_target is None:
            return
        self.query_one("#open-panel", Static).update(
            f"[#9d4edd]── {self._open_target.upper()} ──[/]\n[dim]Panel content coming in Task 6[/]"
        )

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
