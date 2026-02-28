from textual.app import ComposeResult
from textual.widgets import Static
from ui.screens.dashboard import sparkline
import json
from pathlib import Path

COMPANIES = json.loads((Path(__file__).parent.parent.parent / "data" / "companies.json").read_text())
CMD_HINT = "[dim]cmd:[/] [cyan]buy <qty> <ticker>[/]  [dim]|[/]  [cyan]sell <qty> <ticker>[/]"


class MarketPane(Static):
    def compose(self) -> ComposeResult:
        yield Static(CMD_HINT, id="market-cmd")
        yield Static("", id="market-content")

    def on_mount(self):
        self._refresh()

    def _refresh(self):
        s = self.app.state
        lines = ["[bold cyan]── MARKET ──[/]", ""]
        header = f"  {'#':<3} {'Ticker':<6} {'Company':<22} {'Price':>8} {'Chg%':>7}  {'Chart':<16} {'Owned':>5}"
        lines.append(f"[bold]{header}[/]")
        lines.append("  " + "─" * 72)
        for i, co in enumerate(COMPANIES, 1):
            ticker = co["ticker"]
            price = s.market_prices.get(ticker, co["base_price"])
            hist = s.price_history.get(ticker, [price])
            prev = hist[-2] if len(hist) >= 2 else price
            chg = (price - prev) / prev * 100 if prev else 0
            chg_color = "green" if chg >= 0 else "red"
            chart = sparkline(hist, width=15)
            owned = s.portfolio.get(ticker, {}).get("shares", 0)
            lines.append(
                f"  [{i:<2}] [bold]{ticker:<6}[/] {co['name']:<22} "
                f"${price:>7.2f} [{chg_color}]{chg:>+6.2f}%[/]  {chart}  {owned:>5}"
            )

        from game.market import portfolio_value
        val = portfolio_value(s.portfolio, s.market_prices)
        lines += ["", f"[bold cyan]── PORTFOLIO (${val:,.2f}) ──[/]"]
        has_holdings = False
        for ticker, holding in s.portfolio.items():
            if holding.get("shares", 0) > 0:
                has_holdings = True
                price = s.market_prices.get(ticker, 0)
                cost = holding["avg_cost"]
                gain = (price - cost) / cost * 100 if cost else 0
                color = "green" if gain >= 0 else "red"
                lines.append(f"  {ticker}: {holding['shares']} shares @ ${price:.2f}  [{color}]{gain:+.1f}%[/]")
        if not has_holdings:
            lines.append("  [dim]No holdings[/]")

        self.query_one("#market-content", Static).update("\n".join(lines))
