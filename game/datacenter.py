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


def _get_component(state: GameState, comp_id: str) -> Component:
    for c in state.hardware_inventory:
        if c.id == comp_id:
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

    total_cores = cpu.specs["cores"]
    total_ram = sum(r.specs["gb"] for r in rams)
    total_storage = sum(s.specs["gb"] for s in storages)
    nic_speed = nic.specs["gbps"]
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
    state.hardware_inventory = [c for c in state.hardware_inventory if c.id not in used]
    state.servers.append(server)
    return state, server


def server_meets_contract_requirements(
    server: Server, cores: int, ram_gb: int, storage_gb: int
) -> bool:
    return (
        server.total_cores >= cores
        and server.total_ram_gb >= ram_gb
        and server.total_storage_gb >= storage_gb
        and server.health > 0.4
    )


def rent_rack(state: GameState) -> GameState:
    if len(state.racks) >= 10:
        raise ValueError("Maximum 10 racks reached")
    tier = "standard"
    if state.reputation >= 60:
        tier = "tier3"
    elif state.reputation >= 30:
        tier = "tier2"
    rent_map = {"standard": 800.0, "tier2": 1200.0, "tier3": 2000.0}
    rack = Rack(
        id=str(uuid.uuid4()),
        name=f"Rack {len(state.racks) + 1}",
        location_tier=tier,
        monthly_rent=rent_map[tier],
    )
    state.racks.append(rack)
    return state
