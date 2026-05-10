import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.counting_engine import CountingEngine, DetectionBox, map_model_class_to_category


class TestCountingEngine(unittest.TestCase):
    def test_counts_exit_and_return_with_real_track_id(self):
        engine = CountingEngine()
        line_y = 100

        engine.process([DetectionBox(0, 60, 20, 80, 7, "Cemento")], 1, line_y)
        events = engine.process([DetectionBox(0, 95, 20, 115, 7, "Cemento")], 2, line_y)
        self.assertEqual(engine.counts["Cemento"], 1)
        self.assertEqual(events[0].direction, "despachado")

        events = engine.process([DetectionBox(0, 60, 20, 80, 7, "Cemento")], 3, line_y)
        self.assertEqual(engine.counts["Cemento"], 0)
        self.assertEqual(events[0].direction, "retornado")

    def test_does_not_double_count_same_track_outside(self):
        engine = CountingEngine()
        line_y = 100

        engine.process([DetectionBox(0, 60, 20, 80, 11, "Cemento")], 1, line_y)
        engine.process([DetectionBox(0, 95, 20, 115, 11, "Cemento")], 2, line_y)
        engine.process([DetectionBox(0, 120, 20, 140, 11, "Cemento")], 3, line_y)

        self.assertEqual(engine.counts["Cemento"], 1)

    def test_first_crossing_upward_counts_as_exit(self):
        engine = CountingEngine()
        line_y = 100

        engine.process([DetectionBox(0, 120, 20, 140, 12, "Cemento")], 1, line_y)
        events = engine.process([DetectionBox(0, 60, 20, 80, 12, "Cemento")], 2, line_y)

        self.assertEqual(engine.counts["Cemento"], 1)
        self.assertEqual(events[0].direction, "despachado")

    def test_reverse_after_upward_exit_counts_as_return(self):
        engine = CountingEngine()
        line_y = 100

        engine.process([DetectionBox(0, 120, 20, 140, 13, "Cemento")], 1, line_y)
        engine.process([DetectionBox(0, 60, 20, 80, 13, "Cemento")], 2, line_y)
        events = engine.process([DetectionBox(0, 120, 20, 140, 13, "Cemento")], 3, line_y)

        self.assertEqual(engine.counts["Cemento"], 0)
        self.assertEqual(events[0].direction, "retornado")

    def test_proxy_tracking_counts_without_track_id(self):
        engine = CountingEngine(proxy_match_px=100)
        line_y = 100

        engine.process([DetectionBox(10, 60, 30, 80, None, "Tubería Presión")], 1, line_y)
        events = engine.process([DetectionBox(12, 95, 32, 115, None, "Tubería Presión")], 2, line_y)

        self.assertEqual(engine.counts["Tubería Presión"], 1)
        self.assertEqual(len(events), 1)

    def test_model_class_mapping_normalizes_accents(self):
        self.assertEqual(map_model_class_to_category("tubería presión"), "Tubería Presión")
        self.assertEqual(map_model_class_to_category("bag"), "Cemento")
        self.assertIsNone(map_model_class_to_category("tornillo"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
