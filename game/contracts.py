import json
import random
import uuid
from pathlib import Path
from game.models import GameState, Contract, Gig

CLIENTS = json.loads(
    (Path(__file__).parent.parent / "data" / "clients.json").read_text()
)


def generate_contract(state: GameState, seed: int = None) -> Contract:
    rng = random.Random(seed)
    rep = state.reputation

    if rep < 20:
        cores = rng.choice([2, 4, 4, 8])
        ram = rng.choice([8, 16, 32])
        storage = rng.choice([100, 250, 500])
        sla = "99.0"
        revenue = rng.uniform(500, 1500)
    elif rep < 50:
        cores = rng.choice([4, 8, 16])
        ram = rng.choice([32, 64, 128])
        storage = rng.choice([500, 1000, 2000])
        sla = rng.choice(["99.0", "99.5"])
        revenue = rng.uniform(1500, 5000)
    else:
        cores = rng.choice([16, 32, 64])
        ram = rng.choice([128, 256])
        storage = rng.choice([2000, 4000, 8000])
        sla = rng.choice(["99.5", "99.9"])
        revenue = rng.uniform(5000, 15000)

    # Occasional whale contract at high reputation
    if rep >= 60 and rng.random() < 0.03:
        revenue = rng.uniform(20000, 60000)

    client = rng.choice(CLIENTS["names"])
    duration = rng.choice([30, 60, 90, 180])

    return Contract(
        id=str(uuid.uuid4()),
        client_name=client,
        required_cores=cores,
        required_ram_gb=ram,
        required_storage_gb=storage,
        sla_tier=sla,
        monthly_revenue=round(revenue, 2),
        duration_days=duration,
        days_remaining=duration,
        status="pending",
    )


def generate_gigs(seed: int = None) -> list[Gig]:
    rng = random.Random(seed)
    templates = rng.sample(CLIENTS["gig_templates"], k=rng.randint(2, 4))
    return [
        Gig(
            id=str(uuid.uuid4()),
            title=t["title"],
            description=f"One-off job: {t['title']}",
            payout=round(rng.uniform(*t["payout_range"]), 2),
        )
        for t in templates
    ]


def negotiate_contract(contract: Contract, counter_pct: float) -> Contract | None:
    """Counter-offer. Returns a new Contract with higher revenue, or None if rejected."""
    if counter_pct > 0.30:
        return None
    accept_chance = 1.0 - (counter_pct / 0.30)
    if random.random() > accept_chance:
        return None
    # Build new contract with bumped revenue
    import dataclasses
    d = dataclasses.asdict(contract)
    d["monthly_revenue"] = round(contract.monthly_revenue * (1 + counter_pct), 2)
    return Contract(**d)


def check_sla_health(contract: Contract, server_health: float) -> str:
    """Returns 'green', 'yellow', or 'red' based on server health and degraded days."""
    if server_health < 0.1:
        return "red"
    if server_health < 0.6 or contract.days_degraded >= 2:
        return "yellow"
    return "green"
