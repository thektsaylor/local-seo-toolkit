"""Offline tests for the result parsing. Run with: python3 -m unittest discover tests"""
import unittest

from toolkit.config import Client, clean_domain
from toolkit.serp import change, grid_points, is_client, read_maps, read_organic

CLIENT = Client(name="Example Plumbing Co", domain="exampleplumbing.com",
                maps_name="Example Plumbing Co", lat=36.3729, lng=-94.2088)


class TestMatching(unittest.TestCase):
    def test_clean_domain(self):
        self.assertEqual(clean_domain("https://www.ExamplePlumbing.com/about?x=1"), "exampleplumbing.com")

    def test_lookalike_domain_does_not_match(self):
        self.assertFalse(is_client({"domain": "notexampleplumbing.com"}, CLIENT, check_name=False))

    def test_subdomain_matches(self):
        self.assertTrue(is_client({"domain": "shop.exampleplumbing.com"}, CLIENT, check_name=False))

    def test_name_fallback_only_when_allowed(self):
        item = {"title": "Example Plumbing Co - Bentonville"}
        self.assertTrue(is_client(item, CLIENT))
        self.assertFalse(is_client(item, CLIENT, check_name=False))


class TestOrganic(unittest.TestCase):
    def test_reads_positions(self):
        items = [
            {"type": "local_pack", "title": "Rival Plumbing"},
            {"type": "local_pack", "title": "Example Plumbing Co"},
            {"type": "organic", "rank_group": 1, "domain": "rival.com", "url": "https://rival.com/"},
            {"type": "organic", "rank_group": 4, "domain": "www.exampleplumbing.com",
             "url": "https://www.exampleplumbing.com/water-heaters/"},
            {"type": "knowledge_graph", "title": "Example Plumbing Co"},
        ]
        result = read_organic(items, CLIENT)
        self.assertEqual(result["web"], 4)
        self.assertEqual(result["page"], "/water-heaters/")
        self.assertEqual(result["map"], 2)
        self.assertTrue(result["panel"])
        self.assertEqual(result["map_leaders"], ["Rival Plumbing", "Example Plumbing Co"])

    def test_not_found(self):
        result = read_organic([{"type": "organic", "rank_group": 1, "domain": "rival.com"}], CLIENT)
        self.assertIsNone(result["web"])
        self.assertIsNone(result["map"])
        self.assertFalse(result["panel"])


class TestMaps(unittest.TestCase):
    def test_position_and_leader(self):
        items = [
            {"type": "maps_search", "rank_group": 1, "title": "Rival Plumbing"},
            {"type": "maps_search", "rank_group": 2, "title": "Example Plumbing Co",
             "domain": "exampleplumbing.com"},
        ]
        self.assertEqual(read_maps(items, CLIENT), {"position": 2, "leader": "Rival Plumbing"})


class TestHelpers(unittest.TestCase):
    def test_change(self):
        self.assertEqual(change(3, 5), "+2")
        self.assertEqual(change(5, 3), "-2")
        self.assertEqual(change(4, 4), "=")
        self.assertEqual(change(4, None), "new")
        self.assertEqual(change(None, 4), "lost")

    def test_grid_is_centered(self):
        points = grid_points(36.3729, -94.2088, 5, 2)
        self.assertEqual(len(points), 25)
        middle = points[12]
        self.assertEqual((middle["row"], middle["col"]), (2, 2))
        self.assertAlmostEqual(middle["lat"], 36.3729, places=4)
        self.assertGreater(points[0]["lat"], points[-1]["lat"])   # row 0 is north
        self.assertLess(points[0]["lng"], points[-1]["lng"])      # col 0 is west


if __name__ == "__main__":
    unittest.main()
