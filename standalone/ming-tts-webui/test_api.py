"""HTTP validation must reject bad requests before loading the GPU model."""
import unittest
from fastapi.testclient import TestClient
from app import app
from engine import engine


class APITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_is_cheap(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok", "model_loaded": False})
        self.assertIsNone(engine.model)

    def test_rejects_invalid_requests_before_loading_model(self):
        for url in ("/api?text=%20", "/api?text=hello&seed=-2", "/api?text=hello&speaker=unknown"):
            self.assertEqual(self.client.get(url).status_code, 400)
        self.assertEqual(self.client.post("/api/tts", json={"text": ""}).status_code, 422)
        self.assertEqual(self.client.post("/api/tts", json={"text": "x" * 50001}).status_code, 422)
        self.assertIsNone(engine.model)

    def test_json_api_does_not_accept_server_audio_paths(self):
        result = self.client.post("/api/tts", json={"text": "你好", "mode": "声音克隆"})
        self.assertEqual(result.status_code, 400)
        self.assertIn("上传音频", result.json()["detail"])
        self.assertIsNone(engine.model)


if __name__ == "__main__":
    unittest.main()
