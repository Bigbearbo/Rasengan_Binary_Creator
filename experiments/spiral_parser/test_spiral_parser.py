import tempfile
import unittest
from pathlib import Path
from spiral_parser import SpiralParser, tokenize


class TestSpiralParser(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "tree.json"
        self.parser = SpiralParser(self.path)
        self.bits = "00" + "1010" + "0010" + "0100"   # 數學 / 新算符5 / 1 / 2

    def test_tokenize(self):
        self.assertEqual(tokenize("1010", 3, 1, 0)["value"], 5)
        self.assertEqual(tokenize("001010", 3, 1, 2)["value"], 5)
        with self.assertRaises(ValueError):
            tokenize("1011", 3, 1, 0)

    def test_create_and_read_tree(self):
        first = self.parser.parse(self.bits)
        self.assertTrue(first["new_node"])
        self.assertEqual([t["value"] for t in first["tokens"]], [0, 5, 1, 2])
        self.assertIn("未知算符", first["hint"])
        second = SpiralParser(self.path).parse(self.bits)
        self.assertFalse(second["new_node"])
        node = SpiralParser(self.path).state["tree"]["math_demo_v1"]["00"]["operators"]["1010"]
        self.assertEqual(node["seen"], 2)

    def test_confirm_only_with_explicit_define(self):
        self.parser.parse(self.bits)
        self.parser.define("1010", "示範算符")
        self.assertIn("已確認語義", SpiralParser(self.path).parse(self.bits)["hint"])

    def test_bad_input_is_transactional(self):
        for bad in ("00" + "1011" + "0010" + "0100", "10" + "1010" + "0010" + "0100", self.bits + "0", "0a" + self.bits[2:]):
            with self.assertRaises(ValueError):
                self.parser.parse(bad)
            self.assertFalse(self.path.exists())

    def test_parameter_change_not_a_new_operator(self):
        self.parser.parse(self.bits)
        self.parser.parse("00" + "1010" + "0110" + "1000")
        node = SpiralParser(self.path).state["tree"]["math_demo_v1"]["00"]["operators"]["1010"]
        self.assertEqual(node["seen"], 2)
        self.assertEqual(node["last_args"], [3, 4])


if __name__ == "__main__":
    unittest.main()