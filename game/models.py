from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Component:
    id: str
    type: str          # "cpu" | "ram" | "storage" | "nic"
    name: str
    specs: dict        # e.g. {"cores": 8, "speed": "3.2GHz"}
    price: float
    size_u: float = 0  # rack units contribution


@dataclass
class Server:
    id: str
    name: str
    components: list[str]   # component ids
    total_cores: int
    total_ram_gb: int
    total_storage_gb: int
    nic_speed_gbps: int
    size_u: int             # 1-4
    rack_id: Optional[str] = None
    slot_start: Optional[int] = None
    contract_id: Optional[str] = None
    health: float = 1.0    # 1.0 = healthy, 0.5 = degraded, 0.0 = failed
    days_degraded: int = 0


@dataclass
class Rack:
    id: str
    name: str
    total_u: int = 12
    location_tier: str = "standard"  # "standard" | "tier2" | "tier3"
    monthly_rent: float = 800.0


@dataclass
class Contract:
    id: str
    client_name: str
    required_cores: int
    required_ram_gb: int
    required_storage_gb: int
    sla_tier: str          # "99.0" | "99.5" | "99.9"
    monthly_revenue: float
    duration_days: int
    days_remaining: int
    server_id: Optional[str] = None
    status: str = "pending"  # "pending" | "active" | "breached" | "complete"
    sla_health: float = 1.0
    days_degraded: int = 0


@dataclass
class Gig:
    id: str
    title: str
    description: str
    payout: float
    days_available: int = 1
    accepted: bool = False


@dataclass
class Loan:
    id: str
    principal: float
    remaining_balance: float
    annual_rate: float
    term_days: int
    days_remaining: int
    monthly_payment: float


@dataclass
class Bond:
    id: str
    face_value: float
    annual_yield: float
    maturity_days: int
    days_remaining: int
    purchase_price: float


@dataclass
class CD:
    id: str
    balance: float
    annual_rate: float
    lock_days: int
    days_remaining: int


@dataclass
class StockHolding:
    ticker: str
    shares: int
    avg_cost: float


@dataclass
class GameState:
    company_name: str
    difficulty: str
    day: int = 0

    # Money
    cash: float = 50000.0
    savings: float = 0.0

    # Financial instruments
    cds: list = field(default_factory=list)
    bonds: list = field(default_factory=list)
    loans: list = field(default_factory=list)
    portfolio: dict = field(default_factory=dict)  # ticker -> {"shares": int, "avg_cost": float}

    # Business
    racks: list = field(default_factory=list)
    hardware_inventory: list = field(default_factory=list)
    servers: list = field(default_factory=list)
    active_contracts: list = field(default_factory=list)
    pending_contracts: list = field(default_factory=list)
    available_gigs: list = field(default_factory=list)

    # Metrics
    reputation: int = 0
    credit_score: int = 650
    total_revenue: float = 0.0
    total_expenses: float = 0.0

    # Log
    event_log: list = field(default_factory=list)

    # Market prices (ticker -> price)
    market_prices: dict = field(default_factory=dict)
    price_history: dict = field(default_factory=dict)  # ticker -> [last 30 prices]
