from textual.app import ComposeResult
from textual.widgets import Static, Input, Label
from textual.containers import Vertical, ScrollableContainer

GLOSSARY = {
    "APR (Annual Percentage Rate)": "The yearly cost of borrowing money as a percentage. A 5% APR loan on $10,000 costs $500/year. In this game: lower APR = cheaper loans.",
    "Amortization": "Spreading loan payments evenly over time. Each payment covers some interest and some principal. Early payments are mostly interest; later ones are mostly principal.",
    "Bond": "A fixed-income investment where you lend money for a set period and receive interest. At maturity you get your principal back. In this game: bonds pay 12-18%/yr.",
    "Bankruptcy": "When total debt exceeds total assets. In this game: if net worth goes negative with outstanding loans, it is game over.",
    "Cash Flow": "Money coming in minus money going out. Positive = healthy. In this game: contract revenue minus rack rent minus loan payments.",
    "CD (Certificate of Deposit)": "A savings account that locks your money for a fixed period in exchange for a higher rate. In this game: 15%/yr.",
    "Credit Score": "A number (300-850) representing creditworthiness. Higher = better loan rates. In this game: grows +2/month with on-time payments.",
    "Compound Interest": "Earning interest on your interest. All interest in this game compounds daily.",
    "Diversification": "Spreading investments across different assets to reduce risk. Mix stocks, bonds, and savings.",
    "Fixed Income": "Investments with predictable, regular returns — like bonds or CDs. Lower risk than stocks.",
    "Interest Rate": "The percentage charged on borrowed money or paid on saved money.",
    "Liquidity": "How easily an asset converts to cash. Cash = perfectly liquid. CDs = illiquid until maturity.",
    "Loan Principal": "The original amount borrowed, not counting interest.",
    "Net Worth": "Total assets (cash + investments) minus total liabilities (loans). The truest measure of financial health.",
    "Opportunity Cost": "The return you give up by choosing one investment over another.",
    "Portfolio": "Your collection of investments (stocks, bonds, etc.).",
    "P&L (Profit and Loss)": "Revenue minus expenses over a period. Positive = you made money.",
    "Rack Unit (U)": "Standard server rack space. One U = 1.75 inches. In this game: each rack has 12U.",
    "SLA (Service Level Agreement)": "Minimum uptime a customer expects. Failing an SLA loses the contract and incurs a penalty.",
    "Savings Rate": "Interest paid on savings per year. In this game: 6%/yr compounded daily.",
    "Yield": "Return on an investment as a percentage of cost. In this game: bond yields are 12-18%.",
    "Brownian Motion": "Random price movements in stock markets — each day prices shift randomly up or down.",
    "Amortization Schedule": "A table showing each loan payment broken into principal and interest portions.",
    "Bear Market": "A period of falling stock prices (typically >20% decline). Good time to buy.",
    "Bull Market": "A period of rising stock prices. Good time to sell.",
}


class GlossaryPane(Static):
    def compose(self) -> ComposeResult:
        yield Label("[bold cyan]── FINANCE GLOSSARY ──  Type to filter[/]")
        yield Input(placeholder="Search terms...", id="glossary-search")
        yield ScrollableContainer(Static("", id="glossary-content"), id="glossary-scroll")

    def on_mount(self) -> None:
        self._render(GLOSSARY)

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        filtered = {k: v for k, v in GLOSSARY.items() if query in k.lower() or query in v.lower()}
        self._render(filtered)

    def _render(self, terms: dict) -> None:
        lines = []
        for term, definition in sorted(terms.items()):
            lines.append(f"[bold yellow]{term}[/]")
            lines.append(f"  {definition}")
            lines.append("")
        content = "\n".join(lines) if lines else "[dim]No matches[/]"
        self.query_one("#glossary-content", Static).update(content)
