import uuid
from textual.app import ComposeResult
from textual.widgets import Static, Button, Input, Label, Select
from textual.containers import Horizontal, Vertical


class BankingPane(Static):
    def compose(self) -> ComposeResult:
        yield Static("", id="banking-content")
        with Horizontal():
            with Vertical():
                yield Label("[bold cyan]Transfer[/]")
                yield Input(placeholder="Amount", id="transfer-input")
                yield Button("→ Savings", id="btn-to-savings", variant="primary")
                yield Button("← Checking", id="btn-to-checking", variant="default")
            with Vertical():
                yield Label("[bold cyan]New Loan[/]")
                yield Input(placeholder="$5K-$500K", id="loan-amount")
                yield Select(
                    [("6 months", "6"), ("12 months", "12"), ("24 months", "24")],
                    id="loan-term",
                    prompt="Select term",
                )
                yield Button("Apply for Loan", id="btn-loan", variant="warning")
            with Vertical():
                yield Label("[bold cyan]Buy Bond[/]")
                yield Input(placeholder="min $1,000", id="bond-amount")
                yield Select(
                    [
                        ("30 days — 12%/yr", "30"),
                        ("60 days — 14%/yr", "60"),
                        ("90 days — 16%/yr", "90"),
                        ("180 days — 18%/yr", "180"),
                    ],
                    id="bond-maturity",
                    prompt="Select maturity",
                )
                yield Button("Buy Bond", id="btn-bond", variant="success")
        yield Static("", id="banking-status")

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
            f"  {s.credit_score}  {bar}  (current loan rate: {rate*100:.1f}% APR)",
            "",
            "[bold cyan]── ACTIVE LOANS ──[/]",
        ]
        if not s.loans:
            lines.append("  No active loans")
        for loan in s.loans:
            remaining_balance = loan["remaining_balance"] if isinstance(loan, dict) else loan.remaining_balance
            monthly_payment = loan["monthly_payment"] if isinstance(loan, dict) else loan.monthly_payment
            days_remaining = loan["days_remaining"] if isinstance(loan, dict) else loan.days_remaining
            lines.append(f"  ${remaining_balance:,.2f} remaining  |  ${monthly_payment:,.2f}/mo  |  {days_remaining}d left")

        lines += ["", "[bold cyan]── BONDS ──[/]"]
        if not s.bonds:
            lines.append("  No bonds held")
        for bond in s.bonds:
            face_value = bond["face_value"] if isinstance(bond, dict) else bond.face_value
            annual_yield = bond["annual_yield"] if isinstance(bond, dict) else bond.annual_yield
            days_remaining = bond["days_remaining"] if isinstance(bond, dict) else bond.days_remaining
            lines.append(f"  ${face_value:,.2f} face  |  {annual_yield*100:.0f}%/yr  |  {days_remaining}d to maturity")

        lines += ["", "[bold cyan]── CDs ──[/]"]
        if not s.cds:
            lines.append("  No CDs")
        for cd in s.cds:
            balance = cd["balance"] if isinstance(cd, dict) else cd.balance
            days_remaining = cd["days_remaining"] if isinstance(cd, dict) else cd.days_remaining
            lines.append(f"  ${balance:,.2f}  |  15%/yr  |  {days_remaining}d remaining")

        self.query_one("#banking-content", Static).update("\n".join(lines))

    def _parse_amount(self, field_id: str) -> float | None:
        val = self.query_one(f"#{field_id}", Input).value.strip()
        val = val.replace(",", "").replace("$", "")
        try:
            return float(val)
        except ValueError:
            return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        s = self.app.state
        status = self.query_one("#banking-status", Static)

        if event.button.id == "btn-to-savings":
            amt = self._parse_amount("transfer-input")
            if amt is None or amt <= 0 or amt > s.cash:
                status.update("[red]Invalid amount or insufficient cash[/]")
                return
            s.cash -= amt
            s.savings += amt
            status.update(f"[green]Moved ${amt:,.2f} to savings[/]")

        elif event.button.id == "btn-to-checking":
            amt = self._parse_amount("transfer-input")
            if amt is None or amt <= 0 or amt > s.savings:
                status.update("[red]Invalid amount or insufficient savings[/]")
                return
            s.savings -= amt
            s.cash += amt
            status.update(f"[green]Moved ${amt:,.2f} to checking[/]")

        elif event.button.id == "btn-loan":
            from game.finance import loan_interest_rate_for_credit_score, calculate_loan_payment
            amt = self._parse_amount("loan-amount")
            term_sel = self.query_one("#loan-term", Select)
            if amt is None or not (5000 <= amt <= 500000):
                status.update("[red]Amount must be $5,000 – $500,000[/]")
                return
            if term_sel.is_blank():
                status.update("[red]Select a loan term[/]")
                return
            term_months = int(term_sel.value)
            rate = loan_interest_rate_for_credit_score(s.credit_score)
            payment = calculate_loan_payment(amt, rate, term_months)
            loan = {
                "id": str(uuid.uuid4()),
                "principal": amt,
                "remaining_balance": amt,
                "annual_rate": rate,
                "term_days": term_months * 30,
                "days_remaining": term_months * 30,
                "monthly_payment": round(payment, 2),
            }
            s.loans.append(loan)
            s.cash += amt
            status.update(f"[green]Loan approved: ${amt:,.2f} at {rate*100:.1f}% APR, ${payment:,.2f}/mo[/]")

        elif event.button.id == "btn-bond":
            YIELDS = {"30": 0.12, "60": 0.14, "90": 0.16, "180": 0.18}
            amt = self._parse_amount("bond-amount")
            mat_sel = self.query_one("#bond-maturity", Select)
            if amt is None or amt < 1000:
                status.update("[red]Minimum bond purchase is $1,000[/]")
                return
            if amt > s.cash:
                status.update("[red]Insufficient funds[/]")
                return
            if mat_sel.is_blank():
                status.update("[red]Select bond maturity[/]")
                return
            maturity = int(mat_sel.value)
            yld = YIELDS[str(maturity)]
            bond = {
                "id": str(uuid.uuid4()),
                "face_value": amt,
                "annual_yield": yld,
                "maturity_days": maturity,
                "days_remaining": maturity,
                "purchase_price": amt,
            }
            s.bonds.append(bond)
            s.cash -= amt
            status.update(f"[green]Bond purchased: ${amt:,.2f} at {yld*100:.0f}%/yr, matures in {maturity} days[/]")

        self._refresh()
