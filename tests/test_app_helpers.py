import json
import tempfile
import unittest
from pathlib import Path

import app


class AppHelperTests(unittest.TestCase):
    def test_progress_cookie_round_trips_json(self):
        data = {"mastered_ids": ["简答_1", "问答_2"], "check_ins": {"2026-06-15": 3}}

        encoded = app.encode_progress_cookie(data)
        decoded = app.decode_progress_cookie(encoded)

        self.assertEqual(decoded, data)

    def test_bad_progress_cookie_returns_empty_progress(self):
        decoded = app.decode_progress_cookie("not-valid-cookie-data")

        self.assertEqual(decoded, {"mastered_ids": [], "check_ins": {}})

    def test_load_question_prompts_from_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "questions.json"
            path.write_text(
                json.dumps({"简答_1": "连续性介质假设", "问答_2": "矩形断面明渠问题"}, ensure_ascii=False),
                encoding="utf-8",
            )

            prompts = app.load_question_prompts(path)

        self.assertEqual(prompts["简答_1"], "连续性介质假设")
        self.assertEqual(prompts["问答_2"], "矩形断面明渠问题")

    def test_parse_pdf_numbers_rejects_invalid_ranges(self):
        self.assertEqual(app.parse_pdf_numbers("9-7.pdf"), [])
        self.assertEqual(app.parse_pdf_numbers("abc.pdf"), [])


if __name__ == "__main__":
    unittest.main()
