from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane, Footer, Static, RichLog
from textual.binding import Binding


class MainScreen(Screen):
    BINDINGS = [
        Binding("space", "advance_day", "Advance Day"),
        Binding("1", "tab_dashboard", "Dashboard"),
        Binding("2", "tab_datacenter", "Datacenter"),
        Binding("3", "tab_market", "Market"),
        Binding("4", "tab_banking", "Banking"),
        Binding("5", "tab_contracts", "Contracts"),
        Binding("6", "tab_glossary", "Glossary"),
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
        yield Footer()

    def on_mount(self) -> None:
        self._update_header()

    def _update_header(self) -> None:
        s = self.app.state
        from game.market import portfolio_value
        net = s.cash + s.savings + portfolio_value(s.portfolio, s.market_prices)
        header_text = (
            f"[bold cyan]{s.company_name}[/]  │  "
            f"Day {s.day}  │  "
            f"Cash: [green]${s.cash:,.2f}[/]  │  "
            f"Net Worth: [yellow]${net:,.2f}[/]  │  "
            f"Rep: {s.reputation}"
        )
        self.query_one("#game-header", Static).update(header_text)

    def refresh_ui(self) -> None:
        self._update_header()
        log = self.query_one("#event-log", RichLog)
        log.clear()
        for entry in self.app.state.event_log[-3:]:
            log.write(entry)
        tabs = self.query_one("#main-tabs", TabbedContent)
        active = tabs.active
        pane_map = {
            "tab-dashboard": "DashboardPane",
            "tab-datacenter": "DatacenterPane",
            "tab-market": "MarketPane",
            "tab-banking": "BankingPane",
            "tab-contracts": "ContractsPane",
        }
        if active in pane_map:
            try:
                pane_class_name = pane_map[active]
                for widget in self.query("*"):
                    if type(widget).__name__ == pane_class_name:
                        if hasattr(widget, "refresh_content"):
                            widget.refresh_content()
                        elif hasattr(widget, "_refresh"):
                            widget._refresh()
                        break
            except Exception:
                pass

    def action_advance_day(self) -> None:
        from game.engine import advance_day
        from game.save import save_game
        self.app.state = advance_day(self.app.state)
        save_game(self.app.state)
        self.refresh_ui()
        if self.app.state.cash < 0:
            self.notify("BANKRUPTCY! Game Over.", severity="error", timeout=10)

    def action_tab_dashboard(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-dashboard"

    def action_tab_datacenter(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-datacenter"

    def action_tab_market(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-market"

    def action_tab_banking(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-banking"

    def action_tab_contracts(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-contracts"

    def action_tab_glossary(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-glossary"
