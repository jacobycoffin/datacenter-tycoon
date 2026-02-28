from textual.app import ComposeResult
from textual.widgets import Static

CMD_HINT = (
    "[dim]cmd:[/] [cyan]accept <n>[/]  [dim]|[/]  [cyan]decline <n>[/]  [dim]|[/]  "
    "[cyan]negotiate <n>[/]  [dim]|[/]  [cyan]assign <n> <server>[/]  [dim]|[/]  [cyan]gig <n>[/]"
)


class ContractsPane(Static):
    def compose(self) -> ComposeResult:
        yield Static(CMD_HINT, id="contracts-cmd")
        yield Static("", id="contracts-content")

    def on_mount(self) -> None:
        self._refresh()

    def _get(self, obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _sla_color(self, server_health: float, days_degraded: int) -> str:
        if server_health < 0.1:
            return "red"
        if server_health < 0.6 or days_degraded >= 2:
            return "yellow"
        return "green"

    def _refresh(self) -> None:
        s = self.app.state
        lines = ["[bold cyan]── INCOMING OFFERS ──[/]", ""]
        header = f"  {'#':<3} {'Client':<20} {'Cores':>5} {'RAM':>7} {'Storage':>8} {'SLA':>5} {'Revenue/mo':>12} {'Days':>5}"
        lines.append(f"[bold]{header}[/]")
        lines.append("  " + "─" * 72)
        if not s.pending_contracts:
            lines.append("  [dim]No incoming offers[/]")
        for i, c in enumerate(s.pending_contracts, 1):
            lines.append(
                f"  [{i:<2}] {self._get(c,'client_name',''):<20} "
                f"{self._get(c,'required_cores',0):>5} "
                f"{self._get(c,'required_ram_gb',0):>6}GB "
                f"{self._get(c,'required_storage_gb',0):>7}GB "
                f"  {self._get(c,'sla_tier',''):>5} "
                f"${self._get(c,'monthly_revenue',0):>11,.2f} "
                f"{self._get(c,'duration_days',0):>5}d"
            )

        lines += ["", "[bold cyan]── ACTIVE CONTRACTS ──[/]", ""]
        header2 = f"  {'#':<3} {'Client':<20} {'Revenue/mo':>12} {'Days Left':>10} {'Server':<16} {'SLA':>5}"
        lines.append(f"[bold]{header2}[/]")
        lines.append("  " + "─" * 72)
        if not s.active_contracts:
            lines.append("  [dim]No active contracts[/]")
        for i, c in enumerate(s.active_contracts, 1):
            server_id = self._get(c, "server_id")
            server = next((sv for sv in s.servers if self._get(sv, "id") == server_id), None)
            health_str = "[dim]unassigned[/]"
            srv_name = "—"
            if server:
                srv_name = self._get(server, "name", "?")
                health = self._get(server, "health", 1.0)
                days_deg = self._get(c, "days_degraded", 0)
                sla = self._sla_color(health, days_deg)
                color = {"green": "green", "yellow": "yellow", "red": "red"}[sla]
                health_str = f"[{color}]{sla.upper()}[/]"
            lines.append(
                f"  [{i:<2}] {self._get(c,'client_name',''):<20} "
                f"${self._get(c,'monthly_revenue',0):>11,.2f} "
                f"{self._get(c,'days_remaining',0):>10}d "
                f"  {srv_name:<16} {health_str:>5}"
            )

        lines += ["", "[bold cyan]── GIG BOARD ──[/]", ""]
        if not s.available_gigs:
            lines.append("  [dim]No gigs available[/]")
        for i, gig in enumerate(s.available_gigs, 1):
            g = gig if isinstance(gig, dict) else vars(gig)
            lines.append(f"  [{i}] [yellow]${g.get('payout',0):,.2f}[/]  {g.get('title','')}  —  {g.get('description','')}")

        self.query_one("#contracts-content", Static).update("\n".join(lines))
