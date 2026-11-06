#!/usr/bin/env python3
"""Ampere ALU instructions through the offline translator (dmsh_xlate, arch sm86), on registers the translator cannot fold, their result stored to shared memory so
that it is kept: BREV, and HADD2 / HMUL2 with an immediate (test_dmsh_ampere_mem.py's Pokopia class has those two on constants, a negative immediate's sign, F2FP.MERGE_C,
F2I from a half, UP2UR, MEMBAR and ERRBAR). Needs DMSH_TEST_XLATE (the translator) like the other translator tests."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dmsh_ampere_mem import EXIT, Translated, inst

STORE = (0x000fe8000000c800, 0x0000080609008388)   # STS.U32 [R9 * 16 + 8], R6 (Mario Kart World f94552a2a2bff505): the sink, R9 the thread index


def waiting(i): return (i[0] | 0x3f << 52, i[1])   # the instruction waits on every scoreboard (control bits 116..121): it reads what an S2R before it wrote
def s2r_tid(rd): return (0x000e260000002100, 0x0000000000007919 | rd << 16)   # S2R Rd, SR_TID.X (Mario Kart World's encoding, write barrier 0)


class Alu(Translated):
    def kept(self, *code, srcs=()):
        """code between S2R R9 (and each register of srcs) = the thread index and the store of R6"""
        pre = b''.join(inst(*s2r_tid(r)) for r in (9, *srcs))
        body = b''.join(inst(*waiting(i)) for i in code)
        return self.translate(pre + body + inst(*waiting(STORE)) + inst(*EXIT), shared=0x1000)


class DeadChannel(Translated):
    """An image read whose .x is dead and whose .y is used: the optimizer's RemoveNode followed the read as if it were removed, so the chain computing its coordinate lost its last use and went, and the
    shader read an uninitialized variable (Ocarina of Time's wind solver 04942f42cae10d0f, the encodings below are from it: its velocity field oscillated and the grass flickered at 10 Hz)"""
    Y_MINUS_1 = (0x000fe40007ffe0ff, 0xffffffff01077810)   # IADD R7, R1, -1
    SULD = (0x000f6200001e0300, 0x6000080006047b97)        # SULD.XY R4, [R6, R7]: R5 is .y
    STORE_Y = (STORE[0], 0x0000080509008388)               # STS.U32 [R9 * 16 + 8], R5

    def test_coordinate_survives(self):
        msl = self.translate(b''.join(inst(*waiting(i)) for i in (s2r_tid(1), s2r_tid(6), s2r_tid(9), self.Y_MINUS_1, self.SULD, self.STORE_Y)) + inst(*EXIT), shared=0x1000)
        self.assertRegex(msl, r'\+ \(-1\)|- 1\b')
        self.assertNotRegex(msl, r'(?m)^\s+int (_\d+);\n\s+int _\d+ = \1;')


class Brev(Alu):
    BREV = (0x001e240000000000, 0x0000001300067301)   # BREV R6, R19 (Pokémon Pokopia 6e8db04c25a53d8c, whose destination is R3)

    def test_reverses_the_bits(self):
        self.assertIn('reverse_bits', self.kept(self.BREV, srcs=(19,)))


class HalfImmediate(Alu):
    """HADD2 / HMUL2 Rd, Ra, imm (form 2): the second source is the immediate at bits 32..63, not the register field at 64 that HFMA2's B uses in that form. Pokopia's
    blur 85446a6753300fc8 steps its loop with HADD2 R6, R6, 2.0h; reading R0 there, the loop never ended and the GPU hung"""
    HADD2 = (0x000fe20000000800, 0x4000400006067430)   # HADD2 R6, R6, 2, 2 (field 64 = R0)
    HMUL2 = (HADD2[0], HADD2[1] & ~0xfff | 0x432)      # HMUL2 R6, R6, 2, 2: the same fields (no game encoding met)

    def test_hadd2_adds_the_immediate(self):
        msl = self.kept(self.HADD2, srcs=(6,))
        self.assertIn('spvFAdd', msl)
        self.assertRegex(msl, r'\b2\.0\b')   # read from R0 (never written) it was 0, and the add folded away

    def test_hmul2_multiplies_by_the_immediate(self):
        msl = self.kept(self.HMUL2, srcs=(6,))
        self.assertIn('spvFMul', msl)
        self.assertRegex(msl, r'\b2\.0\b')


class F2ip(Alu):
    """F2IP.U8.F32.NTZ (0x243) Rd, a, b, RZ in the encodings of Ocarina of Time's video recorder (word 2 0x04ff) and foliage mesh shaders (0xc4ff, a = RZ): b in byte 0, a in byte 1, saturated, NaN 0"""
    NEAREST = (0x000fe200000004ff, 0x0000001309067243)   # F2IP R6, R9, R19
    TRUNCATE = (0x000fe2000000c4ff, 0x00000013ff067243)  # F2IP R6, RZ, R19

    def refused(self, code):
        with self.assertRaises(AssertionError) as e: self.kept(code, srcs=(19,))
        self.assertIn('F2IP form', str(e.exception))

    def test_two_values_round_and_pack(self):
        msl = self.kept(self.NEAREST, srcs=(19,))
        self.assertEqual(msl.count('rint('), 2)
        self.assertIn('<< 8', msl)
        self.assertIn('255.0', msl)
        self.assertRegex(msl, r'\b2147483647\b|\b2147483647u\b')   # NaN by its bits

    def test_one_value_truncates(self):
        msl = self.kept(self.TRUNCATE, srcs=(19,))
        self.assertIn('trunc(', msl)
        self.assertNotIn('<< 8', msl)

    def test_other_forms_stay_refused(self):
        self.refused((self.NEAREST[0] & ~0xff | 5, self.NEAREST[1]))   # a C register
        self.refused((self.NEAREST[0] | 1 << 72 - 64, self.NEAREST[1]))   # another type
        self.refused((self.NEAREST[0] ^ 1 << 78 - 64, self.NEAREST[1]))   # floor
        self.refused((self.NEAREST[0], self.NEAREST[1] | 1 << 63))   # a modifier


class CompareFtz(Alu):
    """FSETP / FSET .FTZ (bit 80): a denormal operand compares as zero, as on NVIDIA; Apple's GPUs keep denormals. Mario Kart World's deferred lighting 635061c90d75a8d1
    normalises its four depth-weighted samples by 1 / sum only where FSETP.NEU.FTZ says sum != 0: a denormal sum passed, its reciprocal overflowed, and the NaN came out
    of a min(x, 1.0) as a fully lit dot. test_dmsh_maxwell_ftz.py has Maxwell's"""
    FSETP = (0x000fca0003f1d000, 0x800000141300720b)   # FSETP.NEU.FTZ.AND P0, PT, R19, -R20, PT (the game's guard, there on R35 and -R10)
    FSET = (0x000fe2000381d000, 0x800000141306720a)    # FSET.NEU.FTZ.AND R6, R19, -R20, PT
    FSEL = (0x000fe40000000000, 0x0000001413067208)    # FSEL R6, R19, R20, P0: keeps the predicate
    FLUSH = '1.1754943508222875'                       # FLT_MIN, the bound under which an operand is flushed

    def test_fsetp_flushes_both_operands(self):
        self.assertEqual(self.kept(self.FSETP, self.FSEL, srcs=(19, 20)).count(self.FLUSH), 2)

    def test_fset_flushes_both_operands(self):
        self.assertEqual(self.kept(self.FSET, srcs=(19, 20)).count(self.FLUSH), 2)

    def test_without_ftz_compares_as_is(self):
        self.assertNotIn(self.FLUSH, self.kept((self.FSETP[0] & ~(1 << 16), self.FSETP[1]), self.FSEL, srcs=(19, 20)))

    def test_against_zero_flushes_one(self):
        self.assertEqual(self.kept((self.FSETP[0], 0x000000ff1300720b), self.FSEL, srcs=(19, 20)).count(self.FLUSH), 1)


if __name__ == '__main__':
    unittest.main()
