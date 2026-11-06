"""shader_split.bahs_shaders: an entry its scan takes that pairs a compute control section with a graphics shader's code (SPH 0x481 / 0x482 at the start) is left out; a true compute entry stays. Made-up bytes, no game files."""
import os
import struct
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/gfx/tools'))
_had = os.environ.get('DM_GAME'); os.environ['DM_GAME'] = '010029B0118E8000'   # shader_split loads a profile at import; other tests expect no default game
import shader_split as ss
if _had is None: del os.environ['DM_GAME']
else: os.environ['DM_GAME'] = _had


def bahs(first_word):
    """One entry at 0x100, its control section at 0x200 (compute, +0x56 = 5), its code of 0x100 bytes at the region's start"""
    region, code = 0x1000, struct.pack('<I', first_word) + bytes(0xfc)
    ctl = bytearray(0xd8)
    ctl[:8] = ss.CTL_MAGIC + struct.pack('<I', 0xc9)
    struct.pack_into('<I', ctl, 0x44, len(code)); ctl[0x56] = 5
    d = bytearray(region + len(code))
    d[:4] = b'BAHS'
    struct.pack_into('<II', d, 0x18, len(code), region)
    struct.pack_into('<IIIi', d, 0x100, 0, 0, len(ctl), 0x100)
    d[0x200:0x200 + len(ctl)] = ctl
    d[region:region + len(code)] = code
    return bytes(d)


class Stray(unittest.TestCase):
    def test_compute_code_is_taken(self):
        self.assertEqual([x[1] for x in ss.bahs_shaders(bahs(0x00087919), 'test')], ['cs'])

    def test_sph_in_a_compute_entry_is_left_out(self):
        for word in (0x020c0481, 0x000c0482):
            self.assertEqual(ss.bahs_shaders(bahs(word), 'test'), [])


if __name__ == '__main__':
    unittest.main()
