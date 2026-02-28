from textual.app import ComposeResult
from textual.widgets import Static

CMD_HINT = (
    "[dim]cmd:[/] [cyan]transfer <amt> savings|checking[/]  [dim]|[/]  "
    "[cyan]loan <amt> <months>[/]  [dim]|[/]  [cyan]bond <amt>[/]  [dim]|[/]  [cyan]sellbond <n>[/]"
)


class BankingPane(Static):
    def compose(self) -> ComposeResult:
        yield Static(CMD_HINT, id="banking-cmd")
        yield Static("", id="banking-content")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        s = self.app.state
        from game.finance import loan_interest_rate_for_credit_score
        rate = loan_interest_rate_for_credit_score(s.credit_score)
        score_pct = s.credit_score / 850
        bar_len = 20
        filled = int(score_pct * bar_len)
        score_color = "green" if s.credit_score >= 700 else ("yellow" if s.credit_score >= 600 else "red")
        bar = f"[{score_color}]{'█' * filled}[/]{'░' * (bar_len - filled)}"

        lines = [
            "[bold cyan]── ACCOUNTS ──[/]",
            f"  Checking:  [green]${s.cash:>12,.2f}[/]  (0% interest)",
            f"  Savings:   [green]${s.savings:>12,.2f}[/]  (6%/yr)",
            "",
            "[bold cyan]── CREDIT SCORE ──[/]",
            f"  {s.credit_score}  {bar}  (loan rate: {rate*100:.1f}% APR)",
            "",
            "[bold cyan]── ACTIVE LOANS ──[/]",
        ]
        if not s.loans:
            lines.append("  No active loans")
        for i, loan in enumerate(s.loans, 1):
            bal = loan["remaining_balance"] if isinstance(loan, dict) else loan.remaining_balance
            pmt = loan["monthly_payment"] if isinstance(loan, dict) else loan.monthly_payment
            days = loan["days_remaining"] if isinstance(loan, dict) else loan.days_remaining
            lines.append(f"  [{i}] ${bal:,.2f} remaining  |  ${pmt:,.2f}/mo  |  {days}d left")

        lines += ["", "[bold cyan]── BONDS ──[/]"]
        if not s.bonds:
            lines.append("  No bonds held")
        for i, bond in enumerate(s.bonds, 1):
            fv = bond["face_value"] if isinstance(bond, dict) else bond.face_value
            yld = bond["annual_yield"] if isinstance(bond, dict) else bond.annual_yield
            days = bond["days_remaining"] if isinstance(bond, dict) else bond.days_remaining
            lines.append(f"  [{i}] ${fv:,.2f} face  |  {yld*100:.0f}%/yr  |  {days}d to maturity")

        lines += ["", "[bold cyan]── CDs ──[/]"]
        if not s.cds:
            lines.append("  No CDs")
        for cd in s.cds:
            bal = cd["balance"] if isinstance(cd, dict) else cd.balance
            days = cd["days_remaining"] if isinstance(cd, dict) else cd.days_remaining
            lines.append(f"  ${bal:,.2f}  |  15%/yr  |  {days}d remaining")

        self.query_one("#banking-content", Static).update("\n".join(lines))
