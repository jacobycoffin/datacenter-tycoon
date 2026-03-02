import json
import re
import dataclasses
from pathlib import Path
from game.models import GameState

_DEFAULT_SAVES_DIR = Path(__file__).resolve().parent.parent / "saves"


def _safe_filename(name: str) -> str:
    """Convert company name to a safe filename (alphanumeric, spaces→underscore)."""
    return re.sub(r'[^\w\-]', '_', name).strip('_') or 'save'


def save_game(state: GameState, save_dir: Path | str | None = None) -> None:
    save_path = Path(save_dir) if save_dir is not None else _DEFAULT_SAVES_DIR
    save_path.mkdir(parents=True, exist_ok=True)
    path = save_path / f"{_safe_filename(state.company_name)}.json"
    with open(path, "w") as f:
        json.dump(dataclasses.asdict(state), f, indent=2)


def load_game(company_name: str, save_dir: Path | str | None = None) -> GameState | None:
    save_path = Path(save_dir) if save_dir is not None else _DEFAULT_SAVES_DIR
    path = save_path / f"{_safe_filename(company_name)}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    try:
        return GameState(**data)
    except (TypeError, KeyError):
        return None
