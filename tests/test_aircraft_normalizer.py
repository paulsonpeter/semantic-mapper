import io
import json
import unittest
from unittest.mock import patch
import aircraft_normalizer as n


class NormalizerTests(unittest.TestCase):
    def response(self, result):
        return io.BytesIO(json.dumps({"message": {"content": json.dumps(result)}}).encode())

    def test_full_paragraph_is_sent_and_valid_result_returned(self):
        paragraph = "No vibration. Noise starts after takeoff; pressure reads 20 psi."
        expected = {"normalized_term": "WHEEL NOISE"}
        with patch.object(n, "urlopen", return_value=self.response(expected)) as call:
            self.assertEqual(n.normalize_report(paragraph, "test-model"), expected)
        payload = json.loads(call.call_args.args[0].data)
        self.assertEqual(payload["messages"][1]["content"], paragraph)
        self.assertEqual(payload["model"], "test-model")

    def test_rejects_invalid_output_shapes(self):
        for result in [[], {"normalized_term": ""}, {"normalized_term": 5},
                       {"normalized_term": "This is a long rewritten paragraph about aircraft faults"},
                       {"normalized_term": "WHEEL_NOISE"}]:
            with self.subTest(result=result), patch.object(n, "urlopen", return_value=self.response(result)):
                with self.assertRaisesRegex(ValueError, "invalid result"):
                    n.normalize_report("Report")

    def test_input_validation_makes_no_network_call(self):
        with patch.object(n, "urlopen") as call:
            for paragraph in [" ", "a" * (n.MAX_CHARACTERS + 1)]:
                with self.assertRaises(ValueError):
                    n.normalize_report(paragraph)
            call.assert_not_called()

    def test_unavailable_model_has_actionable_error(self):
        with patch.object(n, "urlopen", side_effect=OSError("offline")):
            with self.assertRaisesRegex(ValueError, "Start Ollama"):
                n.normalize_report("Report")

    def test_interface_clears_stale_results_and_handles_model_failure(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py")).run()
        self.assertFalse(app.exception)

        self.assertTrue(app.button[0].disabled)
        app.text_area[0].input("Noise during taxi. No vibration.").run()
        with patch.object(n, "normalize_report", return_value={
                "normalized_term": "WHEEL NOISE"}):
            app.button[0].click().run()
        self.assertIn("WHEEL NOISE", [item.value for item in app.text])
        app.text_area[0].input("Different report").run()
        self.assertNotIn("WHEEL NOISE", [item.value for item in app.text])
        with patch.object(n, "normalize_report", side_effect=ValueError("Model unavailable")):
            app.button[0].click().run()
        self.assertEqual(app.error[0].value, "Model unavailable")
        self.assertFalse(app.exception)

    def test_interface_discards_old_paragraph_result(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"))
        app.session_state["paragraph"] = "Wheel is noisy"
        app.session_state["fault_normalization"] = {
            "original": "Wheel is noisy", "model": "test", "normalized_text": "Old paragraph"}
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        with self.assertRaises(KeyError):
            app.session_state["fault_normalization"]
