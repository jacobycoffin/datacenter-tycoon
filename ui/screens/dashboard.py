from textual.app import ComposeResult
from textual.widgets import Static


def sparkline(values: list[float], width: int = 20) -> str:
    if not values or len(values) < 2:
        return "─" * width
    bars = "▁▂▃▄▅▆▇█"
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    chars = [bars[int((v - mn) / rng * 7)] for v in values[-width:]]
    return "".join(chars)


class DashboardPane(Static):
    def compose(self) -> ComposeResult:
        yield Static("", id="dash-content")

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        s = self.app.state
        from game.market import portfolio_value
        port_val = portfolio_value(s.portfolio, s.market_prices)
        bond_val = sum(
            b["face_value"] if isinstance(b, dict) else b.face_value
            for b in s.bonds
        )
        loan_debt = sum(
            l["remaining_balance"] if isinstance(l, dict) else l.remaining_balance
            for l in s.loans
        )
        net_worth = s.cash + s.savings + port_val + bond_val - loan_debt
        monthly_revenue = sum(
            c["monthly_revenue"] if isinstance(c, dict) else c.monthly_revenue
            for c in s.active_contracts
        )
        monthly_costs = sum(
            r["monthly_rent"] if isinstance(r, dict) else r.monthly_rent
            for r in s.racks
        )
        monthly_pl = monthly_revenue - monthly_costs
        pl_color = "green" if monthly_pl >= 0 else "red"

        content = f"""[bold cyan]── FINANCIAL SUMMARY ──[/]

  Net Worth:       [yellow]${net_worth:>12,.2f}[/]
  Cash (checking): [green]${s.cash:>12,.2f}[/]
  Savings:         [green]${s.savings:>12,.2f}[/]
  Investments:     [yellow]${port_val + bond_val:>12,.2f}[/]
  Total Debt:      [red]${loan_debt:>12,.2f}[/]

[bold cyan]── BUSINESS OVERVIEW ──[/]

  Monthly Revenue: [green]${monthly_revenue:>10,.2f}[/]
  Monthly Costs:   [red]${monthly_costs:>10,.2f}[/]
  Monthly P&L:     [{pl_color}]${monthly_pl:>10,.2f}[/]

  Active Contracts:  {len(s.active_contracts)}
  Pending Offers:    {len(s.pending_contracts)}
  Racks Rented:      {len(s.racks)}
  Servers Built:     {len(s.servers)}
  Reputation:        {s.reputation}/100
  Credit Score:      {s.credit_score}

[bold cyan]── ALL-TIME ──[/]

  Total Revenue:   [green]${s.total_revenue:>12,.2f}[/]
  Total Expenses:  [red]${s.total_expenses:>12,.2f}[/]
  Day:             {s.day}
"""
        self.query_one("#dash-content", Static).update(content)
