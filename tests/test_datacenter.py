import pytest
from game.datacenter import (
    buy_component,
    assemble_server,
    server_meets_contract_requirements,
    rent_rack,
)
from game.models import GameState, Rack


@pytest.fixture
def sample_state():
    state = GameState(company_name="Test", difficulty="normal", cash=10000.0)
    state.racks = [Rack(id="rack1", name="Rack A")]
    return state


def make_state():
    state = GameState(company_name="Test", difficulty="normal", cash=10000.0)
    state.racks = [Rack(id="rack1", name="Rack A")]
    return state


def test_buy_component_deducts_cash():
    state = make_state()
    initial_cash = state.cash
    state = buy_component(state, "cpu_budget")
    assert state.cash == initial_cash - 150
    assert len(state.hardware_inventory) == 1


def test_buy_component_insufficient_funds():
    state = make_state()
    state.cash = 10.0
    with pytest.raises(ValueError, match="Insufficient funds"):
        buy_component(state, "cpu_enterprise")


def test_buy_unknown_component_raises():
    state = make_state()
    with pytest.raises(ValueError, match="Unknown hardware"):
        buy_component(state, "nonexistent_id")


def test_assemble_server_from_components():
    state = make_state()
    state = buy_component(state, "cpu_mid")
    state = buy_component(state, "ram_32gb")
    state = buy_component(state, "ssd_1tb")
    state = buy_component(state, "nic_1g")
    cpu_id = state.hardware_inventory[0].id
    ram_id = state.hardware_inventory[1].id
    ssd_id = state.hardware_inventory[2].id
    nic_id = state.hardware_inventory[3].id
    state, server = assemble_server(state, "MyServer", cpu_id, [ram_id], [ssd_id], nic_id)
    assert server.total_cores == 8
    assert server.total_ram_gb == 32
    assert server.total_storage_gb == 1000
    assert len(state.hardware_inventory) == 0  # all components consumed


def test_assemble_server_adds_to_servers_list():
    state = make_state()
    state = buy_component(state, "cpu_budget")
    state = buy_component(state, "ram_8gb")
    state = buy_component(state, "hdd_500gb")
    state = buy_component(state, "nic_1g")
    ids = [c.id for c in state.hardware_inventory]
    state, server = assemble_server(state, "TestSrv", ids[0], [ids[1]], [ids[2]], ids[3])
    assert any(s.id == server.id for s in state.servers)


def test_server_meets_contract_requirements_pass():
    state = make_state()
    state = buy_component(state, "cpu_pro")
    state = buy_component(state, "ram_128gb")
    state = buy_component(state, "ssd_8tb")
    state = buy_component(state, "nic_10g")
    ids = [c.id for c in state.hardware_inventory]
    state, server = assemble_server(state, "BigServer", ids[0], [ids[1]], [ids[2]], ids[3])
    assert server_meets_contract_requirements(server, cores=16, ram_gb=128, storage_gb=8000)


def test_server_meets_contract_requirements_fail():
    state = make_state()
    state = buy_component(state, "cpu_budget")
    state = buy_component(state, "ram_8gb")
    state = buy_component(state, "hdd_500gb")
    state = buy_component(state, "nic_1g")
    ids = [c.id for c in state.hardware_inventory]
    state, server = assemble_server(state, "SmallServer", ids[0], [ids[1]], [ids[2]], ids[3])
    assert not server_meets_contract_requirements(server, cores=32, ram_gb=128, storage_gb=8000)


def test_rent_rack_adds_rack():
    state = make_state()
    initial_count = len(state.racks)
    state = rent_rack(state)
    assert len(state.racks) == initial_count + 1


def test_rent_rack_max_10():
    state = make_state()
    state.racks = [Rack(id=f"r{i}", name=f"Rack {i}") for i in range(10)]
    with pytest.raises(ValueError, match="Maximum 10 racks"):
        rent_rack(state)


def test_get_component_works_with_dict_inventory(tmp_path):
    """After save/load, inventory items are dicts — assemble must still work."""
    from game.save import save_game, load_game
    from game.datacenter import buy_component, assemble_server
    from game.models import GameState
    state = GameState(company_name="Test", difficulty="normal", cash=10000.0)
    state = buy_component(state, "cpu_budget")
    state = buy_component(state, "ram_8gb")
    state = buy_component(state, "hdd_500gb")
    state = buy_component(state, "nic_1g")
    save_game(state, save_dir=str(tmp_path))
    loaded = load_game("Test", save_dir=str(tmp_path))
    # All items are now dicts
    assert isinstance(loaded.hardware_inventory[0], dict)
    cpu_id = loaded.hardware_inventory[0]["id"]
    ram_id = loaded.hardware_inventory[1]["id"]
    stor_id = loaded.hardware_inventory[2]["id"]
    nic_id = loaded.hardware_inventory[3]["id"]
    loaded, server = assemble_server(loaded, "TestBox", cpu_id, [ram_id], [stor_id], nic_id)
    assert len(loaded.servers) == 1
    assert len(loaded.hardware_inventory) == 0


def test_install_server_in_rack(sample_state):
    from game.datacenter import buy_component, assemble_server, install_server_in_rack
    s = buy_component(sample_state, "cpu_budget")
    s = buy_component(s, "ram_8gb")
    s = buy_component(s, "hdd_500gb")
    s = buy_component(s, "nic_1g")
    cpu_id = s.hardware_inventory[0].id
    ram_id = s.hardware_inventory[1].id
    stor_id = s.hardware_inventory[2].id
    nic_id = s.hardware_inventory[3].id
    s, srv = assemble_server(s, "WebBox", cpu_id, [ram_id], [stor_id], nic_id)
    assert srv.rack_id is None
    s = install_server_in_rack(s, "WebBox", 0)
    assert s.servers[0].rack_id == s.racks[0].id


def test_install_server_wrong_name_raises(sample_state):
    from game.datacenter import install_server_in_rack
    with pytest.raises(ValueError, match="No server"):
        install_server_in_rack(sample_state, "Ghost", 0)


def test_install_server_rack_out_of_range(sample_state):
    from game.datacenter import buy_component, assemble_server, install_server_in_rack
    s = buy_component(sample_state, "cpu_budget")
    s = buy_component(s, "ram_8gb")
    s = buy_component(s, "hdd_500gb")
    s = buy_component(s, "nic_1g")
    cpu_id = s.hardware_inventory[0].id
    ram_id = s.hardware_inventory[1].id
    stor_id = s.hardware_inventory[2].id
    nic_id = s.hardware_inventory[3].id
    s, srv = assemble_server(s, "Box", cpu_id, [ram_id], [stor_id], nic_id)
    with pytest.raises(ValueError, match="does not exist"):
        install_server_in_rack(s, "Box", 99)


def test_repair_server(sample_state):
    from game.datacenter import buy_component, assemble_server, repair_server
    s = buy_component(sample_state, "cpu_budget")
    s = buy_component(s, "ram_8gb")
    s = buy_component(s, "hdd_500gb")
    s = buy_component(s, "nic_1g")
    cpu_id = s.hardware_inventory[0].id
    ram_id = s.hardware_inventory[1].id
    stor_id = s.hardware_inventory[2].id
    nic_id = s.hardware_inventory[3].id
    s, srv = assemble_server(s, "FixBox", cpu_id, [ram_id], [stor_id], nic_id)
    s.servers[0].health = 0.5
    old_cash = s.cash
    s = repair_server(s, "FixBox")
    assert s.servers[0].health == 1.0
    assert s.cash == old_cash - 500.0


def test_repair_healthy_server_raises(sample_state):
    from game.datacenter import buy_component, assemble_server, repair_server
    s = buy_component(sample_state, "cpu_budget")
    s = buy_component(s, "ram_8gb")
    s = buy_component(s, "hdd_500gb")
    s = buy_component(s, "nic_1g")
    cpu_id = s.hardware_inventory[0].id
    ram_id = s.hardware_inventory[1].id
    stor_id = s.hardware_inventory[2].id
    nic_id = s.hardware_inventory[3].id
    s, srv = assemble_server(s, "HealthyBox", cpu_id, [ram_id], [stor_id], nic_id)
    with pytest.raises(ValueError, match="already at full health"):
        repair_server(s, "HealthyBox")
