import pytest
import json
from game.models import GameState
from game.save import save_game, load_game


def test_save_and_load_roundtrip(tmp_path):
    state = GameState(company_name="TestCorp", difficulty="normal", day=5, cash=42000.0)
    save_game(state, save_dir=str(tmp_path))
    loaded = load_game("TestCorp", save_dir=str(tmp_path))
    assert loaded.company_name == "TestCorp"
    assert loaded.day == 5
    assert loaded.cash == pytest.approx(42000.0)


def test_save_file_is_valid_json(tmp_path):
    state = GameState(company_name="Foo", difficulty="easy")
    save_game(state, save_dir=str(tmp_path))
    path = tmp_path / "Foo.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["company_name"] == "Foo"


def test_load_missing_returns_none(tmp_path):
    result = load_game("Nonexistent", save_dir=str(tmp_path))
    assert result is None
