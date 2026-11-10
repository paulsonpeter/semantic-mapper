import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import cloud_normalizer as aircraft_normalizer
import fault_store


class ApprovalTests(unittest.TestCase):
    def test_approval_persists_once_and_input_change_requires_new_generation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
                fault_store, "DB_PATH", Path(directory) / "approved.db"):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py")).run()
            app.text_area[0].input("Wheel rumbles during taxi").run()
            with patch.object(aircraft_normalizer, "normalize_report", return_value={"normalized_term": "WHEEL NOISE"}):
                app.button[0].click().run()
            self.assertEqual(fault_store.records(), [])
            app.button[1].click().run(timeout=15)
            rows = fault_store.records()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["paragraph"], "Wheel rumbles during taxi")
            self.assertEqual(rows[0]["normalized_term"], "WHEEL NOISE")
            self.assertTrue(rows[0]["approved_at"])
            self.assertTrue(app.button[1].disabled)
            fault_store.initialize()
            self.assertEqual(len(fault_store.records()), 1)
            self.assertFalse(fault_store.approve(rows[0]["paragraph"], "WHEEL NOISE", rows[0]["model"]))
            app.text_area[0].input("Engine vibration").run()
            self.assertEqual(len(app.button), 1)
            self.assertFalse(app.exception)

