from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane, Footer, RichLog, Static, Input
from textual.containers import Vertical
from textual.binding import Binding
from game.engine import advance_day
from game.save import save_game


class MainScreen(Screen):
    BINDINGS = [
        Binding("space", "advance_day", "Advance Day"),
        Binding("1", "tab_1", "Dashboard"),
        Binding("2", "tab_2", "Datacenter"),
        Binding("3", "tab_3", "Market"),
        Binding("4", "tab_4", "Banking"),
        Binding("5", "tab_5", "Contracts"),
        Binding("6", "tab_6", "Glossary"),
    ]

    def compose(self) -> ComposeResult:
        from ui.screens.dashboard import DashboardPane
        from ui.screens.datacenter_screen import DatacenterPane
        from ui.screens.market_screen import MarketPane
        from ui.screens.banking_screen import BankingPane
        from ui.screens.contracts_screen import ContractsPane
        from ui.screens.glossary_screen import GlossaryPane

        yield Static("", id="game-header")
        with TabbedContent(id="main-tabs"):
            with TabPane("Dashboard [1]", id="tab-dashboard"):
                yield DashboardPane()
            with TabPane("Datacenter [2]", id="tab-datacenter"):
                yield DatacenterPane()
            with TabPane("Market [3]", id="tab-market"):
                yield MarketPane()
            with TabPane("Banking [4]", id="tab-banking"):
                yield BankingPane()
            with TabPane("Contracts [5]", id="tab-contracts"):
                yield ContractsPane()
            with TabPane("Glossary [6]", id="tab-glossary"):
                yield GlossaryPane()
        yield RichLog(id="event-log", max_lines=3, markup=True)
        yield Static("", id="cmd-feedback")
        yield Input(placeholder="> type a command (help for list)", id="cmd-input")
        yield Footer()

    def on_mount(self):
        self._update_header()
        self.query_one("#cmd-input", Input).focus()

    def _update_header(self) -> str:
        s = self.app.state
        from game.market import portfolio_value
        net = s.cash + s.savings + portfolio_value(s.portfolio, s.market_prices)
        text = (
            f"[bold cyan]{s.company_name}[/]  │  Day {s.day}  │  "
            f"Cash: [green]${s.cash:,.2f}[/]  │  Net Worth: [yellow]${net:,.2f}[/]  │  "
            f"Rep: {s.reputation}  │  Credit: {s.credit_score}"
        )
        self.query_one("#game-header", Static).update(text)
        return text

    def refresh_ui(self):
        self._update_header()
        log = self.query_one("#event-log", RichLog)
        log.clear()
        for entry in self.app.state.event_log[-3:]:
            log.write(entry)
        tabs = self.query_one("#main-tabs", TabbedContent)
        active = tabs.active
        try:
            if active == "tab-dashboard":
                self.query_one("DashboardPane").refresh_content()
            elif active == "tab-market":
                pane = self.query_one("MarketPane")
                pane._refresh()
            elif active == "tab-contracts":
                self.query_one("ContractsPane")._refresh()
            elif active == "tab-banking":
                self.query_one("BankingPane")._refresh()
            elif active == "tab-datacenter":
                self.query_one("DatacenterPane")._refresh()
        except Exception as e:
            self.log.error(f"Tab refresh failed: {e}")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self.refresh_ui()

    # ── Key bindings ───────────────────────────────────────────────
    def action_advance_day(self):
        self._run_command("day", [])

    def action_tab_1(self): self.query_one("#main-tabs", TabbedContent).active = "tab-dashboard"
    def action_tab_2(self): self.query_one("#main-tabs", TabbedContent).active = "tab-datacenter"
    def action_tab_3(self): self.query_one("#main-tabs", TabbedContent).active = "tab-market"
    def action_tab_4(self): self.query_one("#main-tabs", TabbedContent).active = "tab-banking"
    def action_tab_5(self): self.query_one("#main-tabs", TabbedContent).active = "tab-contracts"
    def action_tab_6(self): self.query_one("#main-tabs", TabbedContent).active = "tab-glossary"

    # ── Command bar ────────────────────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "cmd-input":
            return
        raw = event.value.strip()
        event.input.value = ""
        if not raw:
            return
        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]
        self._run_command(cmd, args)

    def _run_command(self, cmd: str, args: list[str]) -> None:
        handlers = {
            "day":       self._cmd_day,
            "save":      self._cmd_save,
            "help":      self._cmd_help,
            "tab":       self._cmd_tab,
            "buy":       self._cmd_buy,
            "sell":      self._cmd_sell,
            "transfer":  self._cmd_transfer,
            "loan":      self._cmd_loan,
            "bond":      self._cmd_bond,
            "sellbond":  self._cmd_sellbond,
            "accept":    self._cmd_accept,
            "decline":   self._cmd_decline,
            "negotiate": self._cmd_negotiate,
            "assign":    self._cmd_assign,
            "gig":       self._cmd_gig,
            "buyhw":     self._cmd_buyhw,
            "assemble":  self._cmd_assemble,
            "install":   self._cmd_install,
            "repair":    self._cmd_repair,
            "rent":      self._cmd_rent,
        }
        handler = handlers.get(cmd)
        feedback = self.query_one("#cmd-feedback", Static)
        if handler is None:
            feedback.update(f"[red]Unknown command '{cmd}'. Type 'help' for list.[/]")
            return
        try:
            success, msg = handler(args)
        except Exception as e:
            feedback.update(f"[red]Error: {e}[/]")
            return
        color = "green" if success else "red"
        feedback.update(f"[{color}]{msg}[/]")
        if success:
            save_game(self.app.state)
            self.refresh_ui()
            if self.app.state.cash < 0:
                self._show_game_over()

    def _show_game_over(self):
        self.notify("BANKRUPTCY — Game Over! Restart with 'new' or quit.", severity="error", timeout=10)

    # ── Global commands ────────────────────────────────────────────
    def _cmd_day(self, args):
        self.app.state = advance_day(self.app.state)
        return True, f"Day {self.app.state.day} — market moved, billing processed."

    def _cmd_save(self, args):
        save_game(self.app.state)
        return True, "Game saved."

    def _cmd_tab(self, args):
        tab_map = {"1": "tab-dashboard", "2": "tab-datacenter", "3": "tab-market",
                   "4": "tab-banking", "5": "tab-contracts", "6": "tab-glossary"}
        if not args or args[0] not in tab_map:
            return False, "Usage: tab <1-6>"
        self.query_one("#main-tabs", TabbedContent).active = tab_map[args[0]]
        return True, f"Switched to tab {args[0]}."

    def _cmd_help(self, args):
        help_text = (
            "[bold cyan]COMMANDS[/]\n"
            "  [cyan]day[/]                         Advance one day\n"
            "  [cyan]tab <1-6>[/]                   Switch tab\n"
            "  [cyan]save[/]                        Save game\n"
            "  [cyan]buy <qty> <ticker>[/]           Buy stocks\n"
            "  [cyan]sell <qty> <ticker>[/]          Sell stocks\n"
            "  [cyan]transfer <amt> savings|checking[/]  Move money\n"
            "  [cyan]loan <amt> <months>[/]          Take loan (6/12/24 months)\n"
            "  [cyan]bond <amt>[/]                  Buy 30-day bond (15%/yr)\n"
            "  [cyan]sellbond <n>[/]                Sell bond #n early\n"
            "  [cyan]accept <n>[/]                  Accept contract offer #n\n"
            "  [cyan]decline <n>[/]                 Decline contract offer #n\n"
            "  [cyan]negotiate <n>[/]               Counter-offer +15%\n"
            "  [cyan]assign <n> <server>[/]         Assign server to active contract #n\n"
            "  [cyan]gig <n>[/]                     Collect gig #n\n"
            "  [cyan]buyhw <hw_id>[/]               Buy hardware component\n"
            "  [cyan]assemble <name> <ids...>[/]     Build server from components\n"
            "  [cyan]install <server> <rack_n>[/]    Install server in rack #n\n"
            "  [cyan]repair <server>[/]             Repair server ($500)\n"
            "  [cyan]rent[/]                        Rent another rack"
        )
        self.query_one("#cmd-feedback", Static).update(help_text)
        return True, ""

    # ── Placeholder stubs (implemented in Tasks 5-8) ──────────────
    def _cmd_buy(self, args):      return False, "Not yet implemented"
    def _cmd_sell(self, args):     return False, "Not yet implemented"
    def _cmd_transfer(self, args): return False, "Not yet implemented"
    def _cmd_loan(self, args):     return False, "Not yet implemented"
    def _cmd_bond(self, args):     return False, "Not yet implemented"
    def _cmd_sellbond(self, args): return False, "Not yet implemented"
    def _cmd_accept(self, args):   return False, "Not yet implemented"
    def _cmd_decline(self, args):  return False, "Not yet implemented"
    def _cmd_negotiate(self, args):return False, "Not yet implemented"
    def _cmd_assign(self, args):   return False, "Not yet implemented"
    def _cmd_gig(self, args):      return False, "Not yet implemented"
    def _cmd_buyhw(self, args):    return False, "Not yet implemented"
    def _cmd_assemble(self, args): return False, "Not yet implemented"
    def _cmd_install(self, args):  return False, "Not yet implemented"
    def _cmd_repair(self, args):   return False, "Not yet implemented"
    def _cmd_rent(self, args):     return False, "Not yet implemented"
