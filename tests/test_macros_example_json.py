import json
import os
import unittest


class TestMacrosExampleJson(unittest.TestCase):
    def test_macros_example_json_is_valid(self):
        json_path = os.path.join(os.path.dirname(__file__), os.pardir, "macros.example.json")
        with open(json_path, encoding="utf-8") as fp:
            data = json.load(fp)

        self.assertIsInstance(data, dict)
        self.assertIn("layout", data)


if __name__ == "__main__":
    unittest.main()
