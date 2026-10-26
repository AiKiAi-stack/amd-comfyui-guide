import tempfile
import unittest
from pathlib import Path
from engine import Request, read_text_file


class RequestTests(unittest.TestCase):
    def test_clone_needs_audio_and_transcript(self):
        with self.assertRaisesRegex(ValueError, "逐字文字"):
            Request("你好", mode="声音克隆", reference_audio="voice.wav").validate()

    def test_long_text_is_not_truncated(self):
        request = Request("这是一段长文字。" * 1000)
        request.validate()
        self.assertEqual(len(request.text), 8000)
        with self.assertRaisesRegex(ValueError, "不会被截断"):
            Request("字" * 50001).validate()

    def test_text_file_encodings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "article.txt"
            for encoding in ("utf-8-sig", "gb18030"):
                path.write_bytes("你好，长文本。".encode(encoding))
                self.assertEqual(read_text_file(path), "你好，长文本。")

    def test_invalid_voice_and_mode(self):
        for request in (Request("你好", speaker="不存在的音色"), Request("你好", mode="未知"),
                        Request("你好", mode="音色设计"), Request("你好", segment_length=0)):
            with self.assertRaises(ValueError):
                request.validate()


if __name__ == "__main__":
    unittest.main()
