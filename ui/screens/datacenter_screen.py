from textual.app import ComposeResult
from textual.widgets import Static, Button, DataTable, Select, Label, Input
from textual.containers import Horizontal, Vertical, ScrollableContainer
from game.datacenter import buy_component, assemble_server, rent_rack, HARDWARE


def render_rack(rack, servers: list) -> str:
    rack_id = rack["id"] if isinstance(rack, dict) else rack.id
    rack_name = rack["name"] if isinstance(rack, dict) else rack.name
    rack_tier = rack["location_tier"] if isinstance(rack, dict) else rack.location_tier
    total_u = rack["total_u"] if isinstance(rack, dict) else rack.total_u

    rack_servers = []
    for s in servers:
        rid = s["rack_id"] if isinstance(s, dict) else s.rack_id
        if rid == rack_id:
            rack_servers.append(s)

    lines = [f"[bold]┌─ {rack_name} ({rack_tier}) ─────┐[/]"]
    used_u = 0
    for u in range(total_u):
        placed = False
        for srv in rack_servers:
            srv_size = srv["size_u"] if isinstance(srv, dict) else srv.size_u
            srv_name = srv["name"] if isinstance(srv, dict) else srv.name
            srv_health = srv["health"] if isinstance(srv, dict) else srv.health
            if used_u == u:
                health_color = "green" if srv_health > 0.7 else ("yellow" if srv_health > 0.3 else "red")
                label = f"{srv_name[:12]:<12}"
                lines.append(f"│ [{health_color}]{u+1:02d}U {label}[/] │")
                placed = True
                break
        if not placed:
            lines.append(f"│ [dim]{u+1:02d}U  ─ empty ──────[/] │")
    lines.append("└─────────────────────┘")
    return "\n".join(lines)


class DatacenterPane(Static):
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static("", id="rack-view")
            with Vertical():
                yield Label("[bold cyan]── HARDWARE SHOP ──[/]")
                yield Select(
                    [("CPUs", "cpu"), ("RAM", "ram"), ("Storage", "storage"), ("NICs", "nic")],
                    id="hw-category",
                    prompt="Select category",
                )
                yield DataTable(id="hw-table", cursor_type="row", zebra_stripes=True)
                yield Button("Buy Selected", id="btn-buy-hw", variant="success")
                yield Static("", id="shop-status")
        yield Label("[bold cyan]── INVENTORY ──[/]")
        yield Static("", id="inv-content")
        yield Button("Rent Another Rack", id="btn-rent-rack", variant="warning")
        yield Static("", id="dc-status")

    def on_mount(self) -> None:
        self._refresh()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "hw-category" and event.value and not event.select.is_blank():
            self._populate_hw_table(str(event.value))

    def _populate_hw_table(self, category: str) -> None:
        table = self.query_one("#hw-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Name", "Specs", "Price")
        for item in HARDWARE.get(category, []):
            specs = ", ".join(f"{k}: {v}" for k, v in item["specs"].items())
            table.add_row(item["name"], specs, f"${item['price']:,.2f}", key=item["id"])

    def _refresh(self) -> None:
        s = self.app.state
        rack_text = "\n\n".join(render_rack(r, s.servers) for r in s.racks) or "[dim]No racks rented[/]"
        self.query_one("#rack-view", Static).update(rack_text)

        inv_lines = []
        for c in s.hardware_inventory:
            if isinstance(c, dict):
                inv_lines.append(f"  [{c.get('type','').upper()}] {c.get('name','')} (${c.get('price',0):,.2f})")
            else:
                inv_lines.append(f"  [{c.type.upper()}] {c.name} (${c.price:,.2f})")
        self.query_one("#inv-content", Static).update(
            "\n".join(inv_lines) if inv_lines else "  [dim]No components in inventory[/]"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        s = self.app.state
        dc_status = self.query_one("#dc-status", Static)
        shop_status = self.query_one("#shop-status", Static)

        if event.button.id == "btn-buy-hw":
            table = self.query_one("#hw-table", DataTable)
            if table.cursor_row is None:
                shop_status.update("[red]Select a component first[/]")
                return
            # Get the row key (hardware id)
            row_keys = list(table.rows.keys())
            if table.cursor_row >= len(row_keys):
                return
            hw_id = row_keys[table.cursor_row].value
            try:
                self.app.state = buy_component(s, hw_id)
                shop_status.update("[green]Component purchased![/]")
                self._refresh()
            except ValueError as e:
                shop_status.update(f"[red]{e}[/]")

        elif event.button.id == "btn-rent-rack":
            try:
                self.app.state = rent_rack(s)
                dc_status.update("[green]New rack rented![/]")
                self._refresh()
            except ValueError as e:
                dc_status.update(f"[red]{e}[/]")
