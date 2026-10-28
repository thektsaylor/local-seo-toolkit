"""Offline tests for client config loading."""
import json
import tempfile
import unittest
from pathlib import Path

from toolkit.config import load_client


def write_config(extra_heat_map):
    raw = {
        "name": "Example Plumbing Co",
        "domain": "exampleplumbing.com",
        "center": {"lat": 36.3729, "lng": -94.2088},
        "heat_map": {"keywords": ["plumber"], **extra_heat_map},
    }
    folder = tempfile.mkdtemp()
    path = Path(folder) / "client.json"
    path.write_text(json.dumps(raw))
    return path


class TestHeatMapCenter(unittest.TestCase):
    def test_defaults_to_business_center(self):
        client = load_client(write_config({}))
        self.assertEqual((client.heat_map_lat, client.heat_map_lng), (36.3729, -94.2088))

    def test_own_center_leaves_business_center_alone(self):
        client = load_client(write_config({"center": {"lat": 36.2, "lng": -94.1}}))
        self.assertEqual((client.heat_map_lat, client.heat_map_lng), (36.2, -94.1))
        self.assertEqual((client.lat, client.lng), (36.3729, -94.2088))


if __name__ == "__main__":
    unittest.main()
