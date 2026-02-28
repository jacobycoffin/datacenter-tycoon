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
        self.query_one("#game-header", Static).update(self._update_header())

    def _update_header(self) -> str:
        s = self.app.state
        from game.market import portfolio_value
        net = s.cash + s.savings + portfolio_value(s.portfolio, s.market_prices)
        return (
            f"[bold cyan]{s.company_name}[/]  │  "
            f"Day {s.day}  │  "
            f"Cash: [green]${s.cash:,.2f}[/]  │  "
            f"Net Worth: [yellow]${net:,.2f}[/]  │  "
            f"Rep: {s.reputation}"
        )

    def refresh_ui(self) -> None:
        """Called after state change to update all panes."""
        self.query_one("#game-header", Static).update(self._update_header())
        log = self.query_one("#event-log", RichLog)
        log.clear()
        for entry in self.app.state.event_log[-3:]:
            log.write(entry)
        # Refresh active tab pane
        tabs = self.query_one("#main-tabs", TabbedContent)
        active = tabs.active
        if active == "tab-dashboard":
            try:
                self.query_one("DashboardPane").refresh_content()
            except Exception as e:
                self.log.error(f"Dashboard refresh failed: {e}")
        elif active == "tab-market":
            try:
                pane = self.query_one("MarketPane")
                pane._build_table()
                pane._refresh_portfolio()
            except Exception as e:
                self.log.error(f"Market refresh failed: {e}")
        elif active == "tab-contracts":
            try:
                self.query_one("ContractsPane")._refresh()
            except Exception as e:
                self.log.error(f"Contracts refresh failed: {e}")
        elif active == "tab-banking":
            try:
                self.query_one("BankingPane")._refresh()
            except Exception as e:
                self.log.error(f"Banking refresh failed: {e}")
        elif active == "tab-datacenter":
            try:
                self.query_one("DatacenterPane")._refresh()
            except Exception as e:
                self.log.error(f"Datacenter refresh failed: {e}")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Refresh the newly activated tab's pane."""
        active = self.query_one("#main-tabs", TabbedContent).active
        if active == "tab-dashboard":
            try:
                self.query_one("DashboardPane").refresh_content()
            except Exception as e:
                self.log.error(f"Dashboard tab refresh failed: {e}")
        elif active == "tab-market":
            try:
                pane = self.query_one("MarketPane")
                pane._build_table()
                pane._refresh_portfolio()
            except Exception as e:
                self.log.error(f"Market tab refresh failed: {e}")
        elif active == "tab-contracts":
            try:
                self.query_one("ContractsPane")._refresh()
            except Exception as e:
                self.log.error(f"Contracts tab refresh failed: {e}")
        elif active == "tab-banking":
            try:
                self.query_one("BankingPane")._refresh()
            except Exception as e:
                self.log.error(f"Banking tab refresh failed: {e}")
        elif active == "tab-datacenter":
            try:
                self.query_one("DatacenterPane")._refresh()
            except Exception as e:
                self.log.error(f"Datacenter tab refresh failed: {e}")

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
