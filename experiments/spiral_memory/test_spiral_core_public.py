"""Self-contained synthetic tests for the experimental SNL-MEM-0.2 grammar.

No user memory, proprietary conversation transcripts, or hidden training data.
"""
import unittest
from spiral_core import SpiralError, parse, serialize, entries, query, merge_snapshot


def doc(memory_id='S1', topic='可組合語義'):
    return f'''協議，SNL-MEM-0.2
領域，語言研究
記憶，{memory_id}
原則
存在，{topic}
句號
句號
狀態，示範
句號
出處，A，人工合成測例
句號
句號
句號
句號
'''


class SpiralMemoryPublicTests(unittest.TestCase):
    def test_round_trip(self):
        root = parse(doc())
        self.assertEqual(parse(serialize(root)).as_dict(), root.as_dict())

    def test_entries(self):
        self.assertEqual(entries(parse(doc()))['S1']['領域'], '語言研究')

    def test_search(self):
        self.assertEqual(query(parse(doc()), '可組合語義'), ['S1'])

    def test_merge_two(self):
        merged=merge_snapshot(parse(doc()),parse(doc('S2','階層解析')))
        self.assertEqual(set(entries(merged)), {'S1','S2'})

    def test_duplicate_rejected(self):
        with self.assertRaises(SpiralError):
            merge_snapshot(parse(doc()),parse(doc()))

    def test_unknown_operator_rejected(self):
        with self.assertRaises(SpiralError):
            parse('協議，SNL-MEM-0.2，未知操作，foo，句號，句號')

if __name__ == '__main__':
    unittest.main()