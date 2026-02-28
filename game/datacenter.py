import json
import uuid
from pathlib import Path
from game.models import GameState, Component, Server, Rack

HARDWARE = json.loads(
    (Path(__file__).parent.parent / "data" / "hardware.json").read_text()
)


def _find_hardware(hw_id: str) -> dict:
    for category in HARDWARE.values():
        for item in category:
            if item["id"] == hw_id:
                return item
    raise ValueError(f"Unknown hardware id: {hw_id}")


def _category_of(hw_id: str) -> str:
    for cat, items in HARDWARE.items():
        for item in items:
            if item["id"] == hw_id:
                return cat
    raise ValueError(f"Unknown hardware id: {hw_id}")


def _comp_get(c, key):
    """Get attribute from a Component (dataclass or dict)."""
    return c[key] if isinstance(c, dict) else getattr(c, key)


def _srv_get(s, key, default=None):
    """Get attribute from a Server (dataclass or dict)."""
    if isinstance(s, dict):
        return s.get(key, default)
    return getattr(s, key, default)


def _srv_set(s, key, value):
    """Set attribute on a Server (dataclass or dict)."""
    if isinstance(s, dict):
        s[key] = value
    else:
        setattr(s, key, value)


def buy_component(state: GameState, hw_id: str) -> GameState:
    hw = _find_hardware(hw_id)
    if state.cash < hw["price"]:
        raise ValueError(
            f"Insufficient funds: need ${hw['price']:.2f}, have ${state.cash:.2f}"
        )
    state.cash -= hw["price"]
    comp = Component(
        id=str(uuid.uuid4()),
        type=_category_of(hw_id),
        name=hw["name"],
        specs=hw["specs"],
        price=hw["price"],
    )
    state.hardware_inventory.append(comp)
    return state


def _get_component(state: GameState, comp_id: str):
    for c in state.hardware_inventory:
        if _comp_get(c, "id") == comp_id:
            return c
    raise ValueError(f"Component {comp_id} not in inventory")


def assemble_server(
    state: GameState,
    name: str,
    cpu_id: str,
    ram_ids: list[str],
    storage_ids: list[str],
    nic_id: str,
) -> tuple[GameState, Server]:
    cpu = _get_component(state, cpu_id)
    rams = [_get_component(state, rid) for rid in ram_ids]
    storages = [_get_component(state, sid) for sid in storage_ids]
    nic = _get_component(state, nic_id)

    cpu_specs = _comp_get(cpu, "specs")
    total_cores = cpu_specs["cores"]
    total_ram = sum(_comp_get(r, "specs")["gb"] for r in rams)
    total_storage = sum(_comp_get(s, "specs")["gb"] for s in storages)
    nic_speed = _comp_get(nic, "specs")["gbps"]
    size_u = max(1, min(4, 1 + len(rams) // 2 + len(storages) // 2))

    server = Server(
        id=str(uuid.uuid4()),
        name=name,
        components=[cpu_id] + ram_ids + storage_ids + [nic_id],
        total_cores=total_cores,
        total_ram_gb=total_ram,
        total_storage_gb=total_storage,
        nic_speed_gbps=nic_speed,
        size_u=size_u,
    )

    used = set([cpu_id, nic_id] + ram_ids + storage_ids)
    state.hardware_inventory = [
        c for c in state.hardware_inventory if _comp_get(c, "id") not in used
    ]
    state.servers.append(server)
    return state, server


def install_server_in_rack(state: GameState, server_name: str, rack_index: int) -> GameState:
    """Install a server (by name, case-insensitive) into rack at rack_index (0-based)."""
    server = next(
        (s for s in state.servers if _srv_get(s, "name", "").lower() == server_name.lower()),
        None,
    )
    if server is None:
        raise ValueError(f"No server named '{server_name}'")

    if rack_index < 0 or rack_index >= len(state.racks):
        raise ValueError(f"Rack {rack_index + 1} does not exist")

    rack = state.racks[rack_index]
    rack_id = rack["id"] if isinstance(rack, dict) else rack.id

    # Check capacity
    total_u = rack["total_u"] if isinstance(rack, dict) else rack.total_u
    used_u = sum(
        _srv_get(s, "size_u", 1)
        for s in state.servers
        if _srv_get(s, "rack_id") == rack_id
    )
    server_size = _srv_get(server, "size_u", 1)
    if used_u + server_size > total_u:
        raise ValueError(
            f"Rack {rack_index + 1} is full ({used_u}/{total_u} U used)"
        )

    _srv_set(server, "rack_id", rack_id)
    return state


def repair_server(state: GameState, server_name: str, cost: float = 500.0) -> GameState:
    """Repair a degraded server. Cost: $500. Raises if already healthy."""
    server = next(
        (s for s in state.servers if _srv_get(s, "name", "").lower() == server_name.lower()),
        None,
    )
    if server is None:
        raise ValueError(f"No server named '{server_name}'")

    health = _srv_get(server, "health", 1.0)
    if health >= 1.0:
        raise ValueError(f"Server '{server_name}' is already at full health")

    if state.cash < cost:
        raise ValueError(f"Insufficient funds: need ${cost:.2f}, have ${state.cash:.2f}")

    state.cash -= cost
    _srv_set(server, "health", 1.0)
    state.event_log.append(f"Repaired server '{server_name}' (-${cost:.2f})")
    return state


def server_meets_contract_requirements(
    server, cores: int, ram_gb: int, storage_gb: int
) -> bool:
    return (
        _srv_get(server, "total_cores", 0) >= cores
        and _srv_get(server, "total_ram_gb", 0) >= ram_gb
        and _srv_get(server, "total_storage_gb", 0) >= storage_gb
        and _srv_get(server, "health", 0.0) > 0.4
    )


def rent_rack(state: GameState) -> GameState:
    if len(state.racks) >= 10:
        raise ValueError("Maximum 10 racks reached")
    tier = "standard"
    if state.reputation >= 60:
        tier = "tier3"
    elif state.reputation >= 30:
        tier = "tier2"
    rent = {"standard": 800.0, "tier2": 1200.0, "tier3": 2000.0}[tier]
    rack = Rack(
        id=str(uuid.uuid4()),
        name=f"Rack {len(state.racks) + 1}",
        location_tier=tier,
        monthly_rent=rent,
    )
    state.racks.append(rack)
    return state


def assign_server_to_rack(state: GameState, server_id: str, rack_id: str) -> GameState:
    server = next((s for s in state.servers if _srv_get(s, "id") == server_id), None)
    if server is None:
        raise ValueError(f"Server {server_id} not found")
    _srv_set(server, "rack_id", rack_id)
    return state
