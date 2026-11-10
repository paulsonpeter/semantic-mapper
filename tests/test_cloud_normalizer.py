import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import cloud_normalizer as n


class CloudNormalizerTests(unittest.TestCase):
    def response(self, text='{"normalized_term":"WHEEL NOISE"}', status="completed", kind="output_text"):
        return io.BytesIO(json.dumps({"status": status, "output": [
            {"type": "message", "content": [{"type": kind, "text": text}]}]}).encode())

    def test_cloud_request_preserves_input_and_does_not_store_response(self):
        with patch.object(n, "urlopen", return_value=self.response()) as call:
            self.assertEqual(n.normalize_report("Wheel rumbling during taxi", api_key="test-key"),
                             {"normalized_term": "WHEEL NOISE"})
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        payload = json.loads(request.data)
        self.assertFalse(payload["store"])
        self.assertEqual(payload["input"], "Wheel rumbling during taxi")
        self.assertTrue(payload["text"]["format"]["strict"])

    def test_missing_key_does_not_make_request(self):
        with patch.dict(n.os.environ, {}, clear=True), patch.object(n, "urlopen") as call:
            with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
                n.normalize_report("Noise")
            call.assert_not_called()

    def test_api_errors_do_not_expose_credentials_or_response(self):
        error = HTTPError("https://api.openai.com", 401, "private-response", {}, None)
        with patch.object(n, "urlopen", side_effect=error):
            with self.assertRaises(ValueError) as caught:
                n.normalize_report("Noise", api_key="private-key")
        self.assertNotIn("private", str(caught.exception))
        self.assertIn("rejected", str(caught.exception))

    def test_refusal_incomplete_and_invalid_output(self):
        for response in [self.response(kind="refusal"), self.response(status="incomplete"),
                         self.response(text='{"normalized_term":"A long rewritten paragraph with too many words"}'),
                         self.response(text='{}')]:
            with patch.object(n, "urlopen", return_value=response), self.assertRaises(ValueError):
                n.normalize_report("Noise", api_key="test-key")
