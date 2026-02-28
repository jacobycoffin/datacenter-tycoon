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
    assert loaded == state  # full equality check


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


def test_save_preserves_plain_list_and_dict_fields(tmp_path):
    state = GameState(company_name="Bar", difficulty="normal")
    state.event_log = ["Day 1: started", "Day 2: earned $500"]
    state.market_prices = {"NVLT": 145.0, "CLOD": 88.5}
    save_game(state, save_dir=str(tmp_path))
    loaded = load_game("Bar", save_dir=str(tmp_path))
    assert loaded.event_log == ["Day 1: started", "Day 2: earned $500"]
    assert loaded.market_prices == {"NVLT": 145.0, "CLOD": 88.5}


def test_company_name_with_special_chars_saves_safely(tmp_path):
    state = GameState(company_name="My/Fancy Corp!", difficulty="normal")
    save_game(state, save_dir=str(tmp_path))
    # File should exist with sanitized name
    assert (tmp_path / "My_Fancy_Corp.json").exists()
    # Load should work using same sanitization
    loaded = load_game("My/Fancy Corp!", save_dir=str(tmp_path))
    assert loaded is not None
    assert loaded.company_name == "My/Fancy Corp!"
