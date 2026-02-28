import json
import dataclasses
from pathlib import Path
from game.models import GameState


def save_game(state: GameState, save_dir: str = "saves") -> None:
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    path = Path(save_dir) / f"{state.company_name}.json"
    with open(path, "w") as f:
        json.dump(dataclasses.asdict(state), f, indent=2)


def load_game(company_name: str, save_dir: str = "saves") -> GameState | None:
    path = Path(save_dir) / f"{company_name}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return GameState(**data)
