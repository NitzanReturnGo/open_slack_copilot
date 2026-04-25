import json
from pathlib import Path

import pytest

from common.data_layer import data_layer
from common.data_layer.file_key_value_collection import FileKeyValueCollection
from common.data_layer.key_value_collection import KeyValueCollection


def test_file_kv_round_trip(tmp_path: Path) -> None:
    col: KeyValueCollection = FileKeyValueCollection(tmp_path / "c1")
    assert col.get("k") is None
    col.set("k1", {"a": 1})
    assert col.get("k1") == {"a": 1}
    assert col.list_keys() == ["k1"]
    assert col.delete("k1") is True
    assert col.get("k1") is None
    assert col.delete("k1") is False


def test_get_collection_uses_patched_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(data_layer, "_data_root", lambda: tmp_path)
    col = data_layer.get_collection("test_col")
    col.set("u1", {"x": 2})
    f = tmp_path / "test_col" / "u1.json"
    assert f.is_file()
    assert json.loads(f.read_text())["x"] == 2


def test_invalid_collection_name() -> None:
    with pytest.raises(ValueError):
        data_layer.get_collection("")


def test_non_file_backend_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(data_layer.settings, "data_layer", {"backend": "redis", "root": "/"})
    with pytest.raises(NotImplementedError):
        data_layer.get_collection("x")
