from textual.app import ComposeResult
from textual.widgets import Static, Button, DataTable, Select, Label
from textual.containers import Horizontal, Vertical
from game.contracts import negotiate_contract


class ContractsPane(Static):
    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]── INCOMING OFFERS ──[/]")
        yield DataTable(id="offers-table", cursor_type="row", zebra_stripes=True)
        with Horizontal():
            yield Button("Accept", id="btn-accept", variant="success")
            yield Button("Negotiate (+15%)", id="btn-negotiate", variant="warning")
            yield Button("Decline", id="btn-decline", variant="error")
        yield Static("[bold cyan]── ACTIVE CONTRACTS ──[/]")
        yield DataTable(id="active-table", cursor_type="row", zebra_stripes=True)
        yield Label("Assign server to selected contract:")
        yield Select([], id="server-select", prompt="Select server")
        yield Button("Assign Server", id="btn-assign", variant="primary")
        yield Static("[bold cyan]── GIG BOARD ──[/]")
        yield Static("", id="gig-list")
        yield Static("", id="contract-status")

    def on_mount(self) -> None:
        self._refresh()

    def _get(self, obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _sla_color(self, server_health: float, days_degraded: int) -> str:
        """Return 'green', 'yellow', or 'red' based on server health."""
        if server_health < 0.1:
            return "red"
        if server_health < 0.6 or days_degraded >= 2:
            return "yellow"
        return "green"

    def _refresh(self) -> None:
        s = self.app.state

        offers = self.query_one("#offers-table", DataTable)
        offers.clear(columns=True)
        offers.add_columns("Client", "Cores", "RAM", "Storage", "SLA", "Revenue/mo", "Days")
        for c in s.pending_contracts:
            offers.add_row(
                self._get(c, "client_name", ""),
                str(self._get(c, "required_cores", 0)),
                f"{self._get(c, 'required_ram_gb', 0)}GB",
                f"{self._get(c, 'required_storage_gb', 0)}GB",
                self._get(c, "sla_tier", ""),
                f"${self._get(c, 'monthly_revenue', 0):,.2f}",
                f"{self._get(c, 'duration_days', 0)}d",
            )

        active = self.query_one("#active-table", DataTable)
        active.clear(columns=True)
        active.add_columns("Client", "Revenue/mo", "Days Left", "Server", "SLA Health")
        for c in s.active_contracts:
            server_id = self._get(c, "server_id")
            server = next((sv for sv in s.servers if self._get(sv, "id") == server_id), None)
            health_str = "[dim]unassigned[/]"
            if server:
                health = self._get(server, "health", 1.0)
                days_degraded = self._get(c, "days_degraded", 0)
                sla = self._sla_color(health, days_degraded)
                color = {"green": "green", "yellow": "yellow", "red": "red"}[sla]
                health_str = f"[{color}]{sla.upper()}[/]"
            active.add_row(
                self._get(c, "client_name", ""),
                f"${self._get(c, 'monthly_revenue', 0):,.2f}",
                str(self._get(c, "days_remaining", 0)),
                self._get(server, "name", "—") if server else "—",
                health_str,
            )

        srv_sel = self.query_one("#server-select", Select)
        unassigned = [sv for sv in s.servers if not self._get(sv, "contract_id")]
        srv_sel.set_options([
            (f"{self._get(sv,'name','')} ({self._get(sv,'total_cores',0)}c/{self._get(sv,'total_ram_gb',0)}GB)",
             self._get(sv, "id", ""))
            for sv in unassigned
        ])

        gig_lines = []
        for gig in s.available_gigs:
            g = gig if isinstance(gig, dict) else vars(gig)
            gig_lines.append(f"  [yellow]${g.get('payout',0):,.2f}[/]  {g.get('title','')}")
        self.query_one("#gig-list", Static).update(
            "\n".join(gig_lines) if gig_lines else "  [dim]No gigs available[/]"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        s = self.app.state
        status = self.query_one("#contract-status", Static)

        if event.button.id in ("btn-accept", "btn-negotiate", "btn-decline"):
            offers_table = self.query_one("#offers-table", DataTable)
            row = offers_table.cursor_row
            if not s.pending_contracts or row is None or row >= len(s.pending_contracts):
                status.update("[red]No contract selected[/]")
                return
            contract = s.pending_contracts[row]

            if event.button.id == "btn-accept":
                if isinstance(contract, dict):
                    contract["status"] = "active"
                else:
                    contract.status = "active"
                s.active_contracts.append(contract)
                s.pending_contracts.pop(row)
                client = self._get(contract, "client_name", "unknown")
                status.update(f"[green]Contract accepted from {client}![/]")

            elif event.button.id == "btn-negotiate":
                if isinstance(contract, dict):
                    from game.models import Contract as ContractModel
                    c_obj = ContractModel(**contract)
                else:
                    c_obj = contract
                new_contract = negotiate_contract(c_obj, counter_pct=0.15)
                if new_contract:
                    new_contract.status = "active"
                    s.active_contracts.append(new_contract)
                    s.pending_contracts.pop(row)
                    status.update(f"[green]Negotiated! New rate: ${new_contract.monthly_revenue:,.2f}/mo[/]")
                else:
                    s.pending_contracts.pop(row)
                    status.update(f"[red]Counter-offer rejected.[/]")

            elif event.button.id == "btn-decline":
                s.pending_contracts.pop(row)
                status.update("[yellow]Contract declined.[/]")

        elif event.button.id == "btn-assign":
            active_table = self.query_one("#active-table", DataTable)
            srv_sel = self.query_one("#server-select", Select)
            row = active_table.cursor_row
            if row is None or row >= len(s.active_contracts):
                status.update("[red]Select an active contract[/]")
                return
            if srv_sel.is_blank():
                status.update("[red]Select a server[/]")
                return
            srv_val = srv_sel.value
            contract = s.active_contracts[row]
            server = next((sv for sv in s.servers if self._get(sv, "id") == srv_val), None)
            if server:
                if isinstance(contract, dict):
                    contract["server_id"] = srv_val
                else:
                    contract.server_id = srv_val
                if isinstance(server, dict):
                    server["contract_id"] = self._get(contract, "id")
                else:
                    server.contract_id = self._get(contract, "id")
                sname = self._get(server, "name", "server")
                cname = self._get(contract, "client_name", "client")
                status.update(f"[green]Assigned {sname} to {cname}[/]")

        self._refresh()
