from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal
from game.datacenter import HARDWARE

CMD_HINT = (
    "[dim]cmd:[/] [cyan]buyhw <hw_id>[/]  [dim]|[/]  "
    "[cyan]assemble <name> <cpu> <ram...> <storage...> <nic>[/]  [dim]|[/]  "
    "[cyan]install <server> <rack_n>[/]  [dim]|[/]  [cyan]repair <server>[/]  [dim]|[/]  [cyan]rent[/]"
)


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
    u = 0
    while u < total_u:
        placed = False
        for srv in rack_servers:
            srv_size = srv["size_u"] if isinstance(srv, dict) else srv.size_u
            srv_name = srv["name"] if isinstance(srv, dict) else srv.name
            srv_health = srv["health"] if isinstance(srv, dict) else srv.health
            srv_slot = srv.get("slot_start") if isinstance(srv, dict) else getattr(srv, "slot_start", None)
            if srv_slot is None or srv_slot == u:
                health_color = "green" if srv_health > 0.7 else ("yellow" if srv_health > 0.3 else "red")
                label = f"{srv_name[:12]:<12}"
                for uu in range(srv_size):
                    if u + uu < total_u:
                        lines.append(f"│ [{health_color}]{u+uu+1:02d}U {label}[/] │")
                u += srv_size
                placed = True
                break
        if not placed:
            lines.append(f"│ [dim]{u+1:02d}U  ─ empty ──────[/] │")
            u += 1
    lines.append("└─────────────────────┘")
    return "\n".join(lines)


class DatacenterPane(Static):
    def compose(self) -> ComposeResult:
        yield Static(CMD_HINT, id="dc-cmd")
        with Horizontal():
            yield Static("", id="rack-view")
            yield Static("", id="shop-content")
        yield Static("", id="inv-content")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        s = self.app.state
        rack_text = "\n\n".join(render_rack(r, s.servers) for r in s.racks) or "[dim]No racks rented[/]"
        self.query_one("#rack-view", Static).update(rack_text)

        shop_lines = ["[bold cyan]── HARDWARE SHOP ──[/]", ""]
        for cat, items in HARDWARE.items():
            shop_lines.append(f"  [bold]{cat.upper()}[/]")
            for item in items:
                specs_str = " ".join(f"{v}" for v in item["specs"].values())
                shop_lines.append(f"    [cyan]{item['id']:<18}[/] {item['name']:<22} {specs_str:<12} ${item['price']:,.0f}")
            shop_lines.append("")
        self.query_one("#shop-content", Static).update("\n".join(shop_lines))

        inv_lines = ["[bold cyan]── COMPONENTS IN INVENTORY ──[/]"]
        for c in s.hardware_inventory:
            if isinstance(c, dict):
                inv_lines.append(f"  [{c.get('type','').upper()}] {c.get('name','')} — id: [cyan]{c.get('id','')[:8]}[/]")
            else:
                inv_lines.append(f"  [{c.type.upper()}] {c.name} — id: [cyan]{c.id[:8]}[/]")
        if not s.hardware_inventory:
            inv_lines.append("  [dim]No components[/]")

        inv_lines += ["", "[bold cyan]── ASSEMBLED SERVERS ──[/]"]
        unracked = []
        racked = []
        for srv in s.servers:
            if isinstance(srv, dict):
                rack_id = srv.get("rack_id")
                name = srv.get("name", "")
                cores = srv.get("total_cores", 0)
                ram = srv.get("total_ram_gb", 0)
                storage = srv.get("total_storage_gb", 0)
                health = srv.get("health", 1.0)
            else:
                rack_id = srv.rack_id
                name = srv.name
                cores = srv.total_cores
                ram = srv.total_ram_gb
                storage = srv.total_storage_gb
                health = srv.health
            h_color = "green" if health > 0.7 else ("yellow" if health > 0.3 else "red")
            info = f"  {name} — {cores}c/{ram}GB/{storage}GB  [{h_color}]health:{health*100:.0f}%[/]"
            if rack_id is None:
                unracked.append(info + "  [dim]unracked[/]")
            else:
                racked.append(info + f"  rack: {rack_id[:8]}")
        for line in unracked + racked:
            inv_lines.append(line)
        if not s.servers:
            inv_lines.append("  [dim]No servers assembled[/]")

        self.query_one("#inv-content", Static).update("\n".join(inv_lines))
