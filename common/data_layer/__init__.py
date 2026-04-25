"""Pluggable key-value collection layer (file-backed by default, database-ready)."""

from common.data_layer.data_layer import get_collection
from common.data_layer.key_value_collection import KeyValueCollection

__all__ = ["get_collection", "KeyValueCollection"]
