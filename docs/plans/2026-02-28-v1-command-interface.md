# Datacenter Tycoon v1 — Command Interface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all button-based UI with a persistent terminal command bar, and add the missing gameplay features (server assembly, rack install, gig collection, server repair, early bond selling) to make the game fully playable.

**Architecture:** All game actions move to a single command bar (`Input #cmd-input`) at the bottom of `MainScreen`. Commands are parsed, dispatched to handlers on `MainScreen`, and handlers call the backend game functions. Visual panels become read-only dashboards with numbered rows and `cmd:` hint lines. New backend functions (`install_server_in_rack`, `repair_server`, `accept_gig`) are added with TDD.

**Tech Stack:** Python 3.11, Textual 8.0+, existing game backend in `game/`

**Design doc:** `docs/plans/2026-02-28-v1-command-interface-design.md`

---

## Task 1: Fix dict/dataclass handling in game/datacenter.py + add install_server_in_rack and repair_server

**Context:** After save/load, `hardware_inventory` and `servers` items are plain dicts (JSON deserialization). The existing `_get_component()` and `assemble_server()` use direct attribute access (`c.id`, `c.specs`) which breaks on loaded games. Fix these first, then add the two new functions.

**Files:**
- Modify: `game/datacenter.py`
- Modify: `tests/test_datacenter.py`

**Step 1: Write failing tests for the new functions and the dict-mode fix**

Add to `tests/test_datacenter.py`:
```python
def test_get_component_works_with_dict_inventory(tmp_path):
    """After save/load, inventory items are dicts — assemble must still work."""
    from game.save import save_game, load_game
    from game.datacenter import buy_component, assemble_server
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
    import pytest
    with pytest.raises(ValueError, match="No server"):
        install_server_in_rack(sample_state, "Ghost", 0)

def test_install_server_rack_out_of_range(sample_state):
    from game.datacenter import buy_component, assemble_server, install_server_in_rack
    import pytest
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
    import pytest
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
```

**Step 2: Run to verify failure**
```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
pytest tests/test_datacenter.py -v -k "dict_inventory or install or repair"
```
Expected: FAIL

**Step 3: Fix game/datacenter.py**

Replace the entire file with this corrected version that handles both dict and dataclass throughout:

```python
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
    rack_total_u = rack["total_u"] if isinstance(rack, dict) else rack.total_u

    if _srv_get(server, "rack_id") is not None:
        raise ValueError(f"Server '{server_name}' is already installed in a rack")

    used_u = sum(
        _srv_get(s, "size_u", 1)
        for s in state.servers
        if _srv_get(s, "rack_id") == rack_id
    )
    srv_size_u = _srv_get(server, "size_u", 1)
    if used_u + srv_size_u > rack_total_u:
        raise ValueError(
            f"Rack {rack_index + 1} is full ({used_u}/{rack_total_u} U used)"
        )

    _srv_set(server, "rack_id", rack_id)
    return state


def repair_server(state: GameState, server_name: str, cost: float = 500.0) -> GameState:
    """Repair a degraded server to full health. Costs $cost."""
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
        raise ValueError(f"Insufficient funds: repair costs ${cost:.0f}")

    state.cash -= cost
    _srv_set(server, "health", 1.0)
    return state


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
```

**Step 4: Run tests**
```bash
pytest tests/test_datacenter.py -v
```
Expected: All passing (existing 9 + new 6 = 15 tests)

**Step 5: Commit**
```bash
git add game/datacenter.py tests/test_datacenter.py
git commit -m "feat: fix dict/dataclass handling in datacenter, add install_server_in_rack and repair_server"
```

---

## Task 2: Add accept_gig to game/engine.py

**Files:**
- Modify: `game/engine.py`
- Modify: `tests/test_engine.py`

**Step 1: Write failing test**

Add to `tests/test_engine.py`:
```python
def test_accept_gig_pays_and_removes(sample_state):
    from game.engine import accept_gig, initialize_new_game
    from game.contracts import generate_gigs
    state = initialize_new_game("GigCorp", "normal")
    assert len(state.available_gigs) > 0
    gig = state.available_gigs[0]
    payout = gig.payout if hasattr(gig, "payout") else gig["payout"]
    old_cash = state.cash
    old_count = len(state.available_gigs)
    state = accept_gig(state, 0)
    assert state.cash == pytest.approx(old_cash + payout)
    assert len(state.available_gigs) == old_count - 1

def test_accept_gig_out_of_range_raises(sample_state):
    from game.engine import accept_gig, initialize_new_game
    state = initialize_new_game("GigCorp", "normal")
    with pytest.raises(ValueError, match="No gig"):
        accept_gig(state, 99)
```

**Step 2: Run to verify failure**
```bash
pytest tests/test_engine.py -v -k "gig"
```
Expected: FAIL

**Step 3: Add accept_gig to game/engine.py**

Add after the `_log` function:
```python
def accept_gig(state: GameState, gig_index: int) -> GameState:
    """Collect a gig by index (0-based) — instant payout, removes from board."""
    if gig_index < 0 or gig_index >= len(state.available_gigs):
        raise ValueError(f"No gig at position {gig_index + 1}")
    gig = state.available_gigs[gig_index]
    payout = _get(gig, "payout", 0.0)
    title = _get(gig, "title", "Unknown gig")
    state.cash += payout
    state.total_revenue += payout
    state.available_gigs.pop(gig_index)
    _log(state, f"Gig completed: {title} +${payout:,.2f}")
    return state
```

**Step 4: Run tests**
```bash
pytest tests/test_engine.py -v
```
Expected: All passing (existing 10 + new 2 = 12 tests)

**Step 5: Commit**
```bash
git add game/engine.py tests/test_engine.py
git commit -m "feat: add accept_gig to engine"
```

---

## Task 3: Convert all UI panels to read-only dashboards with numbered rows and cmd hints

**Context:** Remove all buttons, inputs (except glossary search), and Select widgets from the four panels. Add `[n]` numbers to every table row. Add a `cmd:` hint line at the top of each panel. The panels become pure display. All interactivity moves to the command bar (added in Task 4).

**Files:**
- Modify: `ui/screens/market_screen.py`
- Modify: `ui/screens/banking_screen.py`
- Modify: `ui/screens/contracts_screen.py`
- Modify: `ui/screens/datacenter_screen.py`

Also fix the `render_rack()` bug where `used_u` is never incremented.

**Step 1: Replace market_screen.py**

```python
from textual.app import ComposeResult
from textual.widgets import Static
from ui.screens.dashboard import sparkline
import json
from pathlib import Path

COMPANIES = json.loads((Path(__file__).parent.parent.parent / "data" / "companies.json").read_text())
CMD_HINT = "[dim]cmd:[/] [cyan]buy <qty> <ticker>[/]  [dim]|[/]  [cyan]sell <qty> <ticker>[/]"


class MarketPane(Static):
    def compose(self) -> ComposeResult:
        yield Static(CMD_HINT, id="market-cmd")
        yield Static("", id="market-content")

    def on_mount(self):
        self._build_table()
        self._refresh_portfolio()

    def _build_table(self):
        s = self.app.state
        lines = ["[bold cyan]── MARKET ──[/]", ""]
        header = f"  {'#':<3} {'Ticker':<6} {'Company':<22} {'Price':>8} {'Chg%':>7}  {'Chart':<16} {'Owned':>5}"
        lines.append(f"[bold]{header}[/]")
        lines.append("  " + "─" * 72)
        for i, co in enumerate(COMPANIES, 1):
            ticker = co["ticker"]
            price = s.market_prices.get(ticker, co["base_price"])
            hist = s.price_history.get(ticker, [price])
            prev = hist[-2] if len(hist) >= 2 else price
            chg = (price - prev) / prev * 100 if prev else 0
            chg_color = "green" if chg >= 0 else "red"
            chart = sparkline(hist, width=15)
            owned = s.portfolio.get(ticker, {}).get("shares", 0)
            lines.append(
                f"  [{i:<2}] [bold]{ticker:<6}[/] {co['name']:<22} "
                f"${price:>7.2f} [{chg_color}]{chg:>+6.2f}%[/]  {chart}  {owned:>5}"
            )
        self.query_one("#market-content", Static).update("\n".join(lines))

    def _refresh_portfolio(self):
        from game.market import portfolio_value
        s = self.app.state
        val = portfolio_value(s.portfolio, s.market_prices)
        lines = ["", f"[bold cyan]── PORTFOLIO (${val:,.2f}) ──[/]"]
        has_holdings = False
        for ticker, holding in s.portfolio.items():
            if holding.get("shares", 0) > 0:
                has_holdings = True
                price = s.market_prices.get(ticker, 0)
                cost = holding["avg_cost"]
                gain = (price - cost) / cost * 100 if cost else 0
                color = "green" if gain >= 0 else "red"
                lines.append(f"  {ticker}: {holding['shares']} shares @ ${price:.2f}  [{color}]{gain:+.1f}%[/]")
        if not has_holdings:
            lines.append("  [dim]No holdings[/]")
        existing = self.query_one("#market-content", Static).renderable
        self.query_one("#market-content", Static).update(str(existing) + "\n" + "\n".join(lines))
```

**Step 2: Replace banking_screen.py**

Keep `_refresh()` but remove the compose buttons/inputs. Replace compose with a single Static + cmd hint:

```python
import uuid
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
```

**Step 3: Replace contracts_screen.py**

```python
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
```

**Step 4: Update datacenter_screen.py — fix render_rack bug + remove buttons + add cmd hint**

Fix render_rack to track used_u correctly. Replace the file:

```python
from textual.app import ComposeResult
from textual.widgets import Static, Select
from textual.containers import Horizontal, Vertical
from game.datacenter import buy_component, rent_rack, HARDWARE

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
            srv_slot = srv.get("slot_start") if isinstance(srv, dict) else srv.slot_start
            # match servers starting at this u position, or untracked (slot_start=None)
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

        # Hardware shop
        shop_lines = ["[bold cyan]── HARDWARE SHOP ──[/]", ""]
        for cat, items in HARDWARE.items():
            shop_lines.append(f"  [bold]{cat.upper()}[/]")
            for item in items:
                specs_str = " ".join(f"{v}" for v in item["specs"].values())
                shop_lines.append(f"    [cyan]{item['id']:<18}[/] {item['name']:<22} {specs_str:<12} ${item['price']:,.0f}")
            shop_lines.append("")
        self.query_one("#shop-content", Static).update("\n".join(shop_lines))

        # Inventory
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
```

**Step 5: Run tests to ensure nothing broke**
```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate && pytest tests/ -q
```
Expected: All passing

**Step 6: Verify imports**
```bash
python -c "from ui.screens.market_screen import MarketPane; from ui.screens.banking_screen import BankingPane; from ui.screens.contracts_screen import ContractsPane; from ui.screens.datacenter_screen import DatacenterPane; print('OK')"
```

**Step 7: Commit**
```bash
git add ui/screens/market_screen.py ui/screens/banking_screen.py ui/screens/contracts_screen.py ui/screens/datacenter_screen.py
git commit -m "refactor: convert all panels to read-only dashboards with numbered rows and cmd hints"
```

---

## Task 4: Add command bar to MainScreen — layout + global commands

**Context:** Add the command bar Input and feedback Static to the MainScreen layout. Wire up `on_input_submitted` with a dispatch router. Implement global commands: `day`, `save`, `help`, `tab <n>`.

**Files:**
- Modify: `ui/screens/main_screen.py`

**Step 1: Replace main_screen.py with the command-bar version**

```python
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane, Footer, RichLog, Static, Input
from textual.containers import Vertical
from textual.binding import Binding
from game.engine import advance_day
from game.save import save_game


class MainScreen(Screen):
    BINDINGS = [
        Binding("space", "advance_day", "Advance Day"),
        Binding("1", "tab_1", "Dashboard"),
        Binding("2", "tab_2", "Datacenter"),
        Binding("3", "tab_3", "Market"),
        Binding("4", "tab_4", "Banking"),
        Binding("5", "tab_5", "Contracts"),
        Binding("6", "tab_6", "Glossary"),
    ]

    def compose(self) -> ComposeResult:
        from ui.screens.dashboard import DashboardPane
        from ui.screens.datacenter_screen import DatacenterPane
        from ui.screens.market_screen import MarketPane
        from ui.screens.banking_screen import BankingPane
        from ui.screens.contracts_screen import ContractsPane
        from ui.screens.glossary_screen import GlossaryPane

        yield Static("", id="game-header")
        with TabbedContent(id="main-tabs"):
            with TabPane("Dashboard [1]", id="tab-dashboard"):
                yield DashboardPane()
            with TabPane("Datacenter [2]", id="tab-datacenter"):
                yield DatacenterPane()
            with TabPane("Market [3]", id="tab-market"):
                yield MarketPane()
            with TabPane("Banking [4]", id="tab-banking"):
                yield BankingPane()
            with TabPane("Contracts [5]", id="tab-contracts"):
                yield ContractsPane()
            with TabPane("Glossary [6]", id="tab-glossary"):
                yield GlossaryPane()
        yield RichLog(id="event-log", max_lines=3, markup=True)
        yield Static("", id="cmd-feedback")
        yield Input(placeholder="> type a command (help for list)", id="cmd-input")
        yield Footer()

    def on_mount(self):
        self._update_header()
        self.query_one("#cmd-input", Input).focus()

    def _update_header(self) -> str:
        s = self.app.state
        from game.market import portfolio_value
        net = s.cash + s.savings + portfolio_value(s.portfolio, s.market_prices)
        text = (
            f"[bold cyan]{s.company_name}[/]  │  Day {s.day}  │  "
            f"Cash: [green]${s.cash:,.2f}[/]  │  Net Worth: [yellow]${net:,.2f}[/]  │  "
            f"Rep: {s.reputation}  │  Credit: {s.credit_score}"
        )
        self.query_one("#game-header", Static).update(text)
        return text

    def refresh_ui(self):
        self._update_header()
        log = self.query_one("#event-log", RichLog)
        log.clear()
        for entry in self.app.state.event_log[-3:]:
            log.write(entry)
        tabs = self.query_one("#main-tabs", TabbedContent)
        active = tabs.active
        try:
            if active == "tab-dashboard":
                self.query_one("DashboardPane").refresh_content()
            elif active == "tab-market":
                pane = self.query_one("MarketPane")
                pane._build_table()
                pane._refresh_portfolio()
            elif active == "tab-contracts":
                self.query_one("ContractsPane")._refresh()
            elif active == "tab-banking":
                self.query_one("BankingPane")._refresh()
            elif active == "tab-datacenter":
                self.query_one("DatacenterPane")._refresh()
        except Exception as e:
            self.log.error(f"Tab refresh failed: {e}")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self.refresh_ui()

    # ── Key bindings ───────────────────────────────────────────────
    def action_advance_day(self):
        self._run_command("day", [])

    def action_tab_1(self): self.query_one("#main-tabs", TabbedContent).active = "tab-dashboard"
    def action_tab_2(self): self.query_one("#main-tabs", TabbedContent).active = "tab-datacenter"
    def action_tab_3(self): self.query_one("#main-tabs", TabbedContent).active = "tab-market"
    def action_tab_4(self): self.query_one("#main-tabs", TabbedContent).active = "tab-banking"
    def action_tab_5(self): self.query_one("#main-tabs", TabbedContent).active = "tab-contracts"
    def action_tab_6(self): self.query_one("#main-tabs", TabbedContent).active = "tab-glossary"

    # ── Command bar ────────────────────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "cmd-input":
            return
        raw = event.value.strip()
        event.input.value = ""
        if not raw:
            return
        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]
        self._run_command(cmd, args)

    def _run_command(self, cmd: str, args: list[str]) -> None:
        handlers = {
            "day":       self._cmd_day,
            "save":      self._cmd_save,
            "help":      self._cmd_help,
            "tab":       self._cmd_tab,
            "buy":       self._cmd_buy,
            "sell":      self._cmd_sell,
            "transfer":  self._cmd_transfer,
            "loan":      self._cmd_loan,
            "bond":      self._cmd_bond,
            "sellbond":  self._cmd_sellbond,
            "accept":    self._cmd_accept,
            "decline":   self._cmd_decline,
            "negotiate": self._cmd_negotiate,
            "assign":    self._cmd_assign,
            "gig":       self._cmd_gig,
            "buyhw":     self._cmd_buyhw,
            "assemble":  self._cmd_assemble,
            "install":   self._cmd_install,
            "repair":    self._cmd_repair,
            "rent":      self._cmd_rent,
        }
        handler = handlers.get(cmd)
        feedback = self.query_one("#cmd-feedback", Static)
        if handler is None:
            feedback.update(f"[red]Unknown command '{cmd}'. Type 'help' for list.[/]")
            return
        try:
            success, msg = handler(args)
        except Exception as e:
            feedback.update(f"[red]Error: {e}[/]")
            return
        color = "green" if success else "red"
        feedback.update(f"[{color}]{msg}[/]")
        if success:
            save_game(self.app.state)
            self.refresh_ui()
            if self.app.state.cash < 0:
                self._show_game_over()

    def _show_game_over(self):
        self.notify("BANKRUPTCY — Game Over! Restart with 'new' or quit.", severity="error", timeout=10)

    # ── Global commands ────────────────────────────────────────────
    def _cmd_day(self, args):
        self.app.state = advance_day(self.app.state)
        return True, f"Day {self.app.state.day} — market moved, billing processed."

    def _cmd_save(self, args):
        save_game(self.app.state)
        return True, "Game saved."

    def _cmd_tab(self, args):
        tab_map = {"1": "tab-dashboard", "2": "tab-datacenter", "3": "tab-market",
                   "4": "tab-banking", "5": "tab-contracts", "6": "tab-glossary"}
        if not args or args[0] not in tab_map:
            return False, "Usage: tab <1-6>"
        self.query_one("#main-tabs", TabbedContent).active = tab_map[args[0]]
        return True, f"Switched to tab {args[0]}."

    def _cmd_help(self, args):
        help_text = (
            "[bold cyan]COMMANDS[/]\n"
            "  [cyan]day[/]                         Advance one day\n"
            "  [cyan]tab <1-6>[/]                   Switch tab\n"
            "  [cyan]save[/]                        Save game\n"
            "  [cyan]buy <qty> <ticker>[/]           Buy stocks\n"
            "  [cyan]sell <qty> <ticker>[/]          Sell stocks\n"
            "  [cyan]transfer <amt> savings|checking[/]  Move money\n"
            "  [cyan]loan <amt> <months>[/]          Take loan (6/12/24 months)\n"
            "  [cyan]bond <amt>[/]                  Buy 30-day bond (15%/yr)\n"
            "  [cyan]sellbond <n>[/]                Sell bond #n early\n"
            "  [cyan]accept <n>[/]                  Accept contract offer #n\n"
            "  [cyan]decline <n>[/]                 Decline contract offer #n\n"
            "  [cyan]negotiate <n>[/]               Counter-offer +15%\n"
            "  [cyan]assign <n> <server>[/]         Assign server to active contract #n\n"
            "  [cyan]gig <n>[/]                     Collect gig #n\n"
            "  [cyan]buyhw <hw_id>[/]               Buy hardware component\n"
            "  [cyan]assemble <name> <ids...>[/]     Build server from components\n"
            "  [cyan]install <server> <rack_n>[/]    Install server in rack #n\n"
            "  [cyan]repair <server>[/]             Repair server ($500)\n"
            "  [cyan]rent[/]                        Rent another rack"
        )
        self.query_one("#cmd-feedback", Static).update(help_text)
        return True, ""

    # ── Placeholder stubs (implemented in Tasks 5-8) ──────────────
    def _cmd_buy(self, args):      return False, "Not yet implemented"
    def _cmd_sell(self, args):     return False, "Not yet implemented"
    def _cmd_transfer(self, args): return False, "Not yet implemented"
    def _cmd_loan(self, args):     return False, "Not yet implemented"
    def _cmd_bond(self, args):     return False, "Not yet implemented"
    def _cmd_sellbond(self, args): return False, "Not yet implemented"
    def _cmd_accept(self, args):   return False, "Not yet implemented"
    def _cmd_decline(self, args):  return False, "Not yet implemented"
    def _cmd_negotiate(self, args):return False, "Not yet implemented"
    def _cmd_assign(self, args):   return False, "Not yet implemented"
    def _cmd_gig(self, args):      return False, "Not yet implemented"
    def _cmd_buyhw(self, args):    return False, "Not yet implemented"
    def _cmd_assemble(self, args): return False, "Not yet implemented"
    def _cmd_install(self, args):  return False, "Not yet implemented"
    def _cmd_repair(self, args):   return False, "Not yet implemented"
    def _cmd_rent(self, args):     return False, "Not yet implemented"
```

**Step 2: Run tests**
```bash
pytest tests/ -q
```
Expected: All passing (UI changes don't affect unit tests)

**Step 3: Verify imports**
```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
python -c "from ui.screens.main_screen import MainScreen; print('OK')"
```

**Step 4: Commit**
```bash
git add ui/screens/main_screen.py
git commit -m "feat: add command bar to MainScreen with global commands and stub handlers"
```

---

## Task 5: Implement market commands (buy, sell)

**Files:**
- Modify: `ui/screens/main_screen.py` — replace `_cmd_buy` and `_cmd_sell` stubs

**Step 1: Replace the two stub methods**

```python
def _cmd_buy(self, args):
    # buy <qty> <ticker>
    if len(args) != 2:
        return False, "Usage: buy <qty> <ticker>"
    try:
        qty = int(args[0])
    except ValueError:
        return False, "Usage: buy <qty> <ticker>  (qty must be a number)"
    ticker = args[1].upper()
    s = self.app.state
    price = s.market_prices.get(ticker)
    if price is None:
        return False, f"Unknown ticker '{ticker}'"
    if qty <= 0:
        return False, "Quantity must be positive"
    cost = price * qty
    if s.cash < cost:
        return False, f"Insufficient funds: need ${cost:,.2f}, have ${s.cash:,.2f}"
    s.cash -= cost
    holding = s.portfolio.setdefault(ticker, {"shares": 0, "avg_cost": 0.0})
    total = holding["shares"] + qty
    holding["avg_cost"] = (holding["avg_cost"] * holding["shares"] + cost) / total
    holding["shares"] = total
    return True, f"Bought {qty} {ticker} @ ${price:.2f}  (-${cost:,.2f})"

def _cmd_sell(self, args):
    # sell <qty> <ticker>
    if len(args) != 2:
        return False, "Usage: sell <qty> <ticker>"
    try:
        qty = int(args[0])
    except ValueError:
        return False, "Usage: sell <qty> <ticker>  (qty must be a number)"
    ticker = args[1].upper()
    s = self.app.state
    price = s.market_prices.get(ticker)
    if price is None:
        return False, f"Unknown ticker '{ticker}'"
    holding = s.portfolio.get(ticker, {})
    owned = holding.get("shares", 0)
    if qty <= 0 or qty > owned:
        return False, f"You own {owned} shares of {ticker}"
    proceeds = price * qty
    s.cash += proceeds
    holding["shares"] -= qty
    if holding["shares"] == 0:
        del s.portfolio[ticker]
    return True, f"Sold {qty} {ticker} @ ${price:.2f}  (+${proceeds:,.2f})"
```

**Step 2: Run tests**
```bash
pytest tests/ -q
```

**Step 3: Commit**
```bash
git add ui/screens/main_screen.py
git commit -m "feat: implement buy and sell commands"
```

---

## Task 6: Implement banking commands (transfer, loan, bond, sellbond)

**Files:**
- Modify: `ui/screens/main_screen.py` — replace 4 stub methods

**Step 1: Replace the four stub methods**

```python
def _cmd_transfer(self, args):
    # transfer <amount> savings|checking
    if len(args) != 2 or args[1] not in ("savings", "checking"):
        return False, "Usage: transfer <amount> savings|checking"
    try:
        amt = float(args[0].replace(",", "").replace("$", ""))
    except ValueError:
        return False, "Usage: transfer <amount> savings|checking"
    if amt <= 0:
        return False, "Amount must be positive"
    s = self.app.state
    if args[1] == "savings":
        if amt > s.cash:
            return False, f"Insufficient checking: have ${s.cash:,.2f}"
        s.cash -= amt
        s.savings += amt
        return True, f"Moved ${amt:,.2f} → savings (savings: ${s.savings:,.2f})"
    else:
        if amt > s.savings:
            return False, f"Insufficient savings: have ${s.savings:,.2f}"
        s.savings -= amt
        s.cash += amt
        return True, f"Moved ${amt:,.2f} → checking (checking: ${s.cash:,.2f})"

def _cmd_loan(self, args):
    # loan <amount> <months>
    import uuid
    from game.finance import loan_interest_rate_for_credit_score, calculate_loan_payment
    if len(args) != 2:
        return False, "Usage: loan <amount> <months>  (months: 6, 12, or 24)"
    try:
        amt = float(args[0].replace(",", "").replace("$", ""))
        months = int(args[1])
    except ValueError:
        return False, "Usage: loan <amount> <months>"
    if months not in (6, 12, 24):
        return False, "Term must be 6, 12, or 24 months"
    if not (5000 <= amt <= 500000):
        return False, "Loan amount must be $5,000–$500,000"
    s = self.app.state
    rate = loan_interest_rate_for_credit_score(s.credit_score)
    payment = calculate_loan_payment(amt, rate, months)
    loan = {
        "id": str(uuid.uuid4()),
        "principal": amt,
        "remaining_balance": amt,
        "annual_rate": rate,
        "term_days": months * 30,
        "days_remaining": months * 30,
        "monthly_payment": round(payment, 2),
    }
    s.loans.append(loan)
    s.cash += amt
    return True, f"Loan approved: ${amt:,.2f} at {rate*100:.1f}% APR, ${payment:,.2f}/mo for {months} months"

def _cmd_bond(self, args):
    # bond <amount>  — 30-day maturity, 15% yield (simplified from UI version)
    import uuid
    if len(args) != 1:
        return False, "Usage: bond <amount>  (min $1,000)"
    try:
        amt = float(args[0].replace(",", "").replace("$", ""))
    except ValueError:
        return False, "Usage: bond <amount>"
    if amt < 1000:
        return False, "Minimum bond purchase is $1,000"
    s = self.app.state
    if amt > s.cash:
        return False, f"Insufficient funds: need ${amt:,.2f}, have ${s.cash:,.2f}"
    bond = {
        "id": str(uuid.uuid4()),
        "face_value": amt,
        "annual_yield": 0.15,
        "maturity_days": 30,
        "days_remaining": 30,
        "purchase_price": amt,
    }
    s.bonds.append(bond)
    s.cash -= amt
    return True, f"Bond purchased: ${amt:,.2f} at 15%/yr, matures in 30 days"

def _cmd_sellbond(self, args):
    # sellbond <n>  — sell bond #n early at discounted value
    from game.finance import bond_current_value
    if len(args) != 1:
        return False, "Usage: sellbond <n>"
    try:
        idx = int(args[0]) - 1
    except ValueError:
        return False, "Usage: sellbond <n>  (n is the bond number)"
    s = self.app.state
    if idx < 0 or idx >= len(s.bonds):
        return False, f"No bond #{idx+1}"
    bond = s.bonds[idx]
    fv = bond["face_value"] if isinstance(bond, dict) else bond.face_value
    yld = bond["annual_yield"] if isinstance(bond, dict) else bond.annual_yield
    days_rem = bond["days_remaining"] if isinstance(bond, dict) else bond.days_remaining
    mat_days = bond["maturity_days"] if isinstance(bond, dict) else bond.maturity_days
    value = bond_current_value(fv, yld, days_rem, mat_days)
    s.cash += value
    s.bonds.pop(idx)
    diff = value - fv
    sign = "+" if diff >= 0 else ""
    return True, f"Sold bond for ${value:,.2f} (face ${fv:,.2f}, {sign}${diff:,.2f})"
```

**Step 2: Run tests + commit**
```bash
pytest tests/ -q
git add ui/screens/main_screen.py
git commit -m "feat: implement banking commands (transfer, loan, bond, sellbond)"
```

---

## Task 7: Implement contract commands (accept, decline, negotiate, assign, gig)

**Files:**
- Modify: `ui/screens/main_screen.py` — replace 5 stub methods

**Step 1: Replace the five stub methods**

```python
def _cmd_accept(self, args):
    # accept <n>
    if len(args) != 1:
        return False, "Usage: accept <n>"
    try:
        idx = int(args[0]) - 1
    except ValueError:
        return False, "Usage: accept <n>"
    s = self.app.state
    if idx < 0 or idx >= len(s.pending_contracts):
        return False, f"No offer #{idx+1}"
    contract = s.pending_contracts[idx]
    if isinstance(contract, dict):
        contract["status"] = "active"
    else:
        contract.status = "active"
    s.active_contracts.append(contract)
    s.pending_contracts.pop(idx)
    client = contract.get("client_name", "?") if isinstance(contract, dict) else contract.client_name
    return True, f"Contract accepted from {client}! Assign a server with: assign <n> <server>"

def _cmd_decline(self, args):
    # decline <n>
    if len(args) != 1:
        return False, "Usage: decline <n>"
    try:
        idx = int(args[0]) - 1
    except ValueError:
        return False, "Usage: decline <n>"
    s = self.app.state
    if idx < 0 or idx >= len(s.pending_contracts):
        return False, f"No offer #{idx+1}"
    contract = s.pending_contracts.pop(idx)
    client = contract.get("client_name", "?") if isinstance(contract, dict) else contract.client_name
    return True, f"Declined offer from {client}."

def _cmd_negotiate(self, args):
    # negotiate <n>
    from game.contracts import negotiate_contract
    from game.models import Contract as ContractModel
    if len(args) != 1:
        return False, "Usage: negotiate <n>"
    try:
        idx = int(args[0]) - 1
    except ValueError:
        return False, "Usage: negotiate <n>"
    s = self.app.state
    if idx < 0 or idx >= len(s.pending_contracts):
        return False, f"No offer #{idx+1}"
    contract = s.pending_contracts[idx]
    c_obj = ContractModel(**contract) if isinstance(contract, dict) else contract
    new_contract = negotiate_contract(c_obj, counter_pct=0.15)
    s.pending_contracts.pop(idx)
    if new_contract:
        new_contract.status = "active"
        s.active_contracts.append(new_contract)
        return True, f"Negotiated! New rate: ${new_contract.monthly_revenue:,.2f}/mo"
    return False, "Counter-offer rejected."

def _cmd_assign(self, args):
    # assign <n> <server_name>
    if len(args) < 2:
        return False, "Usage: assign <contract_n> <server_name>"
    try:
        idx = int(args[0]) - 1
    except ValueError:
        return False, "Usage: assign <contract_n> <server_name>"
    server_name = " ".join(args[1:])
    s = self.app.state
    if idx < 0 or idx >= len(s.active_contracts):
        return False, f"No active contract #{idx+1}"
    contract = s.active_contracts[idx]
    server = next(
        (sv for sv in s.servers
         if (sv.get("name","") if isinstance(sv,dict) else sv.name).lower() == server_name.lower()),
        None
    )
    if server is None:
        return False, f"No server named '{server_name}'"
    srv_id = server.get("id") if isinstance(server,dict) else server.id
    ctr_id = contract.get("id") if isinstance(contract,dict) else contract.id
    if isinstance(contract, dict): contract["server_id"] = srv_id
    else: contract.server_id = srv_id
    if isinstance(server, dict): server["contract_id"] = ctr_id
    else: server.contract_id = ctr_id
    cname = contract.get("client_name","?") if isinstance(contract,dict) else contract.client_name
    return True, f"Assigned {server_name} to {cname}'s contract."

def _cmd_gig(self, args):
    # gig <n>
    from game.engine import accept_gig
    if len(args) != 1:
        return False, "Usage: gig <n>"
    try:
        idx = int(args[0]) - 1
    except ValueError:
        return False, "Usage: gig <n>"
    try:
        self.app.state = accept_gig(self.app.state, idx)
        return True, f"Gig completed! Check event log for payout."
    except ValueError as e:
        return False, str(e)
```

**Step 2: Run tests + commit**
```bash
pytest tests/ -q
git add ui/screens/main_screen.py
git commit -m "feat: implement contract commands (accept, decline, negotiate, assign, gig)"
```

---

## Task 8: Implement datacenter commands (buyhw, assemble, install, repair, rent)

**Files:**
- Modify: `ui/screens/main_screen.py` — replace 5 stub methods

**Step 1: Replace the five stub methods**

```python
def _cmd_buyhw(self, args):
    # buyhw <hw_id>
    from game.datacenter import buy_component
    if len(args) != 1:
        return False, "Usage: buyhw <hw_id>  (see hw_id column in Datacenter tab)"
    try:
        self.app.state = buy_component(self.app.state, args[0])
        return True, f"Purchased {args[0]}. Check Datacenter inventory."
    except ValueError as e:
        return False, str(e)

def _cmd_assemble(self, args):
    # assemble <name> <hw_id...>
    # Component types identified by id prefix: cpu_ / ram_ / hdd_ ssd_ / nic_
    from game.datacenter import assemble_server
    if len(args) < 5:
        return False, "Usage: assemble <name> <cpu_id> <ram_id> <storage_id> <nic_id>  (more ram/storage ok)"
    name = args[0]
    hw_ids = args[1:]
    cpu_ids, ram_ids, stor_ids, nic_ids = [], [], [], []
    for hw_id in hw_ids:
        if hw_id.startswith("cpu_"):
            cpu_ids.append(hw_id)
        elif hw_id.startswith("ram_"):
            ram_ids.append(hw_id)
        elif hw_id.startswith("hdd_") or hw_id.startswith("ssd_"):
            stor_ids.append(hw_id)
        elif hw_id.startswith("nic_"):
            nic_ids.append(hw_id)
        else:
            return False, f"Unknown component type for '{hw_id}'. IDs must start with cpu_/ram_/hdd_/ssd_/nic_"
    if len(cpu_ids) != 1:
        return False, "Need exactly 1 CPU (cpu_budget / cpu_mid / cpu_pro / cpu_enterprise)"
    if not ram_ids:
        return False, "Need at least 1 RAM stick"
    if not stor_ids:
        return False, "Need at least 1 storage drive"
    if len(nic_ids) != 1:
        return False, "Need exactly 1 NIC (nic_1g / nic_10g)"
    # Use instance ids from inventory that match these hw_ids
    s = self.app.state
    def find_inv_id(hw_id):
        """Find the instance id of an unassigned component matching hw_id."""
        from game.datacenter import HARDWARE, _find_hardware
        hw = _find_hardware(hw_id)
        for c in s.hardware_inventory:
            c_name = c.get("name") if isinstance(c, dict) else c.name
            c_id = c.get("id") if isinstance(c, dict) else c.id
            if c_name == hw["name"]:
                return c_id
        return None
    used = set()
    def claim(hw_id):
        from game.datacenter import HARDWARE, _find_hardware
        hw = _find_hardware(hw_id)
        for c in s.hardware_inventory:
            c_name = c.get("name") if isinstance(c, dict) else c.name
            c_id = c.get("id") if isinstance(c, dict) else c.id
            if c_name == hw["name"] and c_id not in used:
                used.add(c_id)
                return c_id
        return None
    cpu_inst = claim(cpu_ids[0])
    ram_insts = [claim(r) for r in ram_ids]
    stor_insts = [claim(r) for r in stor_ids]
    nic_inst = claim(nic_ids[0])
    missing = []
    if cpu_inst is None: missing.append(cpu_ids[0])
    for i, r in enumerate(ram_insts):
        if r is None: missing.append(ram_ids[i])
    for i, r in enumerate(stor_insts):
        if r is None: missing.append(stor_ids[i])
    if nic_inst is None: missing.append(nic_ids[0])
    if missing:
        return False, f"Not in inventory: {', '.join(missing)}"
    try:
        self.app.state, server = assemble_server(s, name, cpu_inst, ram_insts, stor_insts, nic_inst)
        cores = server.total_cores
        ram = server.total_ram_gb
        stor = server.total_storage_gb
        return True, f"Built '{name}': {cores} cores / {ram}GB RAM / {stor}GB storage. Install with: install {name} <rack_n>"
    except ValueError as e:
        return False, str(e)

def _cmd_install(self, args):
    # install <server_name> <rack_n>
    from game.datacenter import install_server_in_rack
    if len(args) < 2:
        return False, "Usage: install <server_name> <rack_n>"
    try:
        rack_n = int(args[-1]) - 1
    except ValueError:
        return False, "Usage: install <server_name> <rack_n>  (rack_n is a number)"
    server_name = " ".join(args[:-1])
    try:
        self.app.state = install_server_in_rack(self.app.state, server_name, rack_n)
        return True, f"Installed '{server_name}' in Rack {rack_n+1}."
    except ValueError as e:
        return False, str(e)

def _cmd_repair(self, args):
    # repair <server_name>
    from game.datacenter import repair_server
    if not args:
        return False, "Usage: repair <server_name>"
    server_name = " ".join(args)
    try:
        self.app.state = repair_server(self.app.state, server_name)
        return True, f"Repaired '{server_name}' to 100% health. (-$500)"
    except ValueError as e:
        return False, str(e)

def _cmd_rent(self, args):
    # rent
    from game.datacenter import rent_rack
    try:
        self.app.state = rent_rack(self.app.state)
        rack = self.app.state.racks[-1]
        rent = rack.monthly_rent if hasattr(rack, "monthly_rent") else rack.get("monthly_rent", 800)
        return True, f"Rented a new rack (${rent:,.0f}/mo). You now have {len(self.app.state.racks)} racks."
    except ValueError as e:
        return False, str(e)
```

**Step 2: Run tests + commit**
```bash
pytest tests/ -q
git add ui/screens/main_screen.py
git commit -m "feat: implement datacenter commands (buyhw, assemble, install, repair, rent)"
```

---

## Task 9: Full test suite run + tag v1.0.0

**Step 1: Run complete test suite**
```bash
cd /home/jacoby/datacenter-game && source venv/bin/activate
pytest tests/ -v --tb=short
```
Expected: All tests pass (target: 62 passing — 15 datacenter + 12 engine + 10 finance + 7 market + 9 contracts + 5 save + any new ones)

**Step 2: Verify all imports**
```bash
python -c "
from ui.app import DatacenterApp
from ui.screens.main_screen import MainScreen
from ui.screens.dashboard import DashboardPane
from ui.screens.market_screen import MarketPane
from ui.screens.banking_screen import BankingPane
from ui.screens.contracts_screen import ContractsPane
from ui.screens.datacenter_screen import DatacenterPane
from ui.screens.glossary_screen import GlossaryPane
from game.datacenter import install_server_in_rack, repair_server
from game.engine import accept_gig
print('All imports OK')
"
```

**Step 3: Smoke test the game loop**
```bash
python -c "
from game.engine import initialize_new_game, advance_day, accept_gig
from game.datacenter import buy_component, assemble_server, install_server_in_rack, repair_server
from game.save import save_game, load_game
import tempfile, os

s = initialize_new_game('v1Test', 'normal')
s = buy_component(s, 'cpu_budget')
s = buy_component(s, 'ram_8gb')
s = buy_component(s, 'hdd_500gb')
s = buy_component(s, 'nic_1g')
cpu = s.hardware_inventory[0].id
ram = s.hardware_inventory[1].id
stor = s.hardware_inventory[2].id
nic = s.hardware_inventory[3].id
s, srv = assemble_server(s, 'Box1', cpu, [ram], [stor], nic)
s = install_server_in_rack(s, 'Box1', 0)
assert s.servers[0].rack_id == s.racks[0].id, 'Rack install failed'
gig_count = len(s.available_gigs)
s = accept_gig(s, 0)
assert len(s.available_gigs) == gig_count - 1, 'Gig accept failed'
for _ in range(5):
    s = advance_day(s)
print('All smoke tests passed. Day:', s.day, 'Cash:', round(s.cash, 2))
"
```

**Step 4: Tag v1.0.0**
```bash
git tag v1.0.0 -m "Datacenter Tycoon v1.0.0 — fully playable with command interface"
```

**Step 5: Push to GitHub**
```bash
TOKEN=$(gh auth token)
git remote set-url origin "https://jacobycoffin:${TOKEN}@github.com/jacobycoffin/datacenter-tycoon.git"
git push origin master
git push origin v1.0.0
git remote set-url origin "https://github.com/jacobycoffin/datacenter-tycoon.git"
```
