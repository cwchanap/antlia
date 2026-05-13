from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAP_SCENE = ROOT / "scenes" / "simple_city_map.tscn"


class SimpleCityMapSceneTest(unittest.TestCase):
    def test_simple_city_map_scene_contains_static_city_grid(self):
        self.assertTrue(MAP_SCENE.exists(), "simple city map scene is missing")
        scene = MAP_SCENE.read_text(encoding="utf-8")

        required_nodes = [
            '[node name="SimpleCityMap" type="Node3D"]',
            '[node name="Roads" type="Node3D" parent="."]',
            '[node name="RoadNorthSouthWest" type="MeshInstance3D" parent="Roads"]',
            '[node name="RoadNorthSouthCenter" type="MeshInstance3D" parent="Roads"]',
            '[node name="RoadNorthSouthEast" type="MeshInstance3D" parent="Roads"]',
            '[node name="RoadEastWestSouth" type="MeshInstance3D" parent="Roads"]',
            '[node name="RoadEastWestCenter" type="MeshInstance3D" parent="Roads"]',
            '[node name="RoadEastWestNorth" type="MeshInstance3D" parent="Roads"]',
            '[node name="CityBlocks" type="Node3D" parent="."]',
            '[node name="BlockSouthWest" type="StaticBody3D" parent="CityBlocks"]',
            '[node name="BlockSouthEast" type="StaticBody3D" parent="CityBlocks"]',
            '[node name="BlockNorthWest" type="StaticBody3D" parent="CityBlocks"]',
            '[node name="BlockNorthEast" type="StaticBody3D" parent="CityBlocks"]',
            '[node name="BoundaryNorth" type="StaticBody3D" parent="Boundaries"]',
            '[node name="BoundarySouth" type="StaticBody3D" parent="Boundaries"]',
            '[node name="BoundaryWest" type="StaticBody3D" parent="Boundaries"]',
            '[node name="BoundaryEast" type="StaticBody3D" parent="Boundaries"]',
        ]
        for node in required_nodes:
            self.assertIn(node, scene)

        stop_nodes = re.findall(
            r'\[node name="BusStop[A-D]" type="Node3D" parent="BusStops" groups=\["bus_stops"\]\]',
            scene,
        )
        self.assertEqual(len(stop_nodes), 4)

        forbidden_runtime_systems = [
            "Route",
            "Passenger",
            "TrafficLight",
            "Minimap",
            "Area3D",
        ]
        for token in forbidden_runtime_systems:
            self.assertNotIn(token, scene)


if __name__ == "__main__":
    unittest.main()
