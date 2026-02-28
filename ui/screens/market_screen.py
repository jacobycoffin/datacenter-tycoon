import json
from pathlib import Path
from textual.app import ComposeResult
from textual.widgets import Static, DataTable, Input, Button, Label
from textual.containers import Horizontal, Vertical
from ui.screens.dashboard import sparkline

COMPANIES = json.loads((Path(__file__).parent.parent.parent / "data" / "companies.json").read_text())


class MarketPane(Static):
    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]── MARKET ──[/]\n[dim]Select a row, enter quantity, then Buy or Sell[/]", id="market-title")
        yield DataTable(id="stock-table", cursor_type="row", zebra_stripes=True)
        with Horizontal():
            yield Label("Shares:")
            yield Input(placeholder="qty", id="shares-input", type="integer")
            yield Button("Buy", id="btn-buy", variant="success")
            yield Button("Sell", id="btn-sell", variant="error")
        yield Static("", id="market-status")
        yield Static("", id="portfolio-summary")

    def on_mount(self) -> None:
        self._build_table()
        self._refresh_portfolio()

    def _build_table(self) -> None:
        s = self.app.state
        table = self.query_one("#stock-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Ticker", "Company", "Price", "Change", "Chart", "Owned")
        for co in COMPANIES:
            ticker = co["ticker"]
            price = s.market_prices.get(ticker, co["base_price"])
            hist = s.price_history.get(ticker, [price])
            prev = hist[-2] if len(hist) >= 2 else price
            chg_pct = ((price - prev) / prev * 100) if prev else 0
            chg_color = "green" if chg_pct >= 0 else "red"
            chg_str = f"[{chg_color}]{chg_pct:+.2f}%[/]"
            chart = sparkline(hist, width=12)
            holding = s.portfolio.get(ticker, {})
            owned = holding.get("shares", 0) if isinstance(holding, dict) else 0
            table.add_row(ticker, co["name"], f"${price:.2f}", chg_str, chart, str(owned), key=ticker)

    def _refresh_portfolio(self) -> None:
        from game.market import portfolio_value
        s = self.app.state
        val = portfolio_value(s.portfolio, s.market_prices)
        lines = [f"[bold cyan]── PORTFOLIO (${val:,.2f}) ──[/]"]
        for ticker, holding in s.portfolio.items():
            if isinstance(holding, dict) and holding.get("shares", 0) > 0:
                price = s.market_prices.get(ticker, 0)
                cost = holding.get("avg_cost", 0)
                gain = (price - cost) / cost * 100 if cost else 0
                color = "green" if gain >= 0 else "red"
                lines.append(f"  {ticker}: {holding['shares']} shares @ ${price:.2f}  [{color}]{gain:+.1f}%[/]")
        self.query_one("#portfolio-summary", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        table = self.query_one("#stock-table", DataTable)
        row_key = table.cursor_row
        if row_key is None:
            self.query_one("#market-status", Static).update("[red]Select a stock row first[/]")
            return

        # Get ticker from the selected row
        ticker_list = [co["ticker"] for co in COMPANIES]
        if row_key >= len(ticker_list):
            return
        ticker = ticker_list[row_key]

        qty_str = self.query_one("#shares-input", Input).value.strip()
        if not qty_str.isdigit() or int(qty_str) <= 0:
            self.query_one("#market-status", Static).update("[red]Enter a valid share quantity[/]")
            return
        qty = int(qty_str)

        s = self.app.state
        price = s.market_prices.get(ticker, 0)

        if event.button.id == "btn-buy":
            cost = price * qty
            if s.cash < cost:
                self.query_one("#market-status", Static).update(f"[red]Need ${cost:,.2f}, have ${s.cash:,.2f}[/]")
                return
            s.cash -= cost
            holding = s.portfolio.setdefault(ticker, {"shares": 0, "avg_cost": 0.0})
            total = holding["shares"] + qty
            holding["avg_cost"] = (holding["avg_cost"] * holding["shares"] + cost) / total
            holding["shares"] = total
            self.query_one("#market-status", Static).update(f"[green]Bought {qty} {ticker} @ ${price:.2f}[/]")
        elif event.button.id == "btn-sell":
            holding = s.portfolio.get(ticker, {"shares": 0})
            if holding.get("shares", 0) < qty:
                self.query_one("#market-status", Static).update(f"[red]Only own {holding.get('shares',0)} shares[/]")
                return
            s.cash += price * qty
            holding["shares"] -= qty
            self.query_one("#market-status", Static).update(f"[green]Sold {qty} {ticker} @ ${price:.2f}[/]")

        self._build_table()
        self._refresh_portfolio()
