"""C-migration Phase 1: print the next N unconverted C-classified stubs, smallest first, with literal pools, callee
arity (c_callee_audit.arg_regs) and the KB fact / slot_<NAME> each call resolves to.

    uv run python -m otn_enhanced.tools.c_next [N]   # needs scratch/c_corpus.json, c_classify.json, c_engine_syms.json
"""
import json
import sys

from otn_enhanced.asm.thumb_disasm import decode_thumb
from otn_enhanced.c_forms import FORMS
from otn_enhanced.tools.c_callee_audit import Image, arg_regs
from otn_enhanced.tools.c_corpus import _slots

img = Image('data/over_the_nexus/working/rom_all_patches.nds')
SKIP = {'CAVE3_KMW_COND', 'CAVE3_SEAL_C3', 'CAVE3_PINE_RES', 'CAVE3_QSR_COND', 'CAVE_REVSYN_C2COST', 'CAVE_WR_RES', 'CAVE_IK_C3F2', 'CAVE_IK_M_C3F2', 'CAVE_IK_O_C3F2', 'CAVE3_SL_COND', 'CAVE3_WNM_COND'}   # parked: see notes/c-toolchain-findings.md
DECK_WALKER = 0x0223BC3C                      # wrappers around it compile to 40 B for 36 B slots -> .S
n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
co = {s['name']: s for s in json.load(open('scratch/c_corpus.json'))['slots']}
sy = {x['addr']: x for x in json.load(open('scratch/c_engine_syms.json'))}
sl = _slots()
cl = sorted((x for x in json.load(open('scratch/c_classify.json'))
             if x['form'] == 'C' and x['slot'] not in FORMS and x['slot'] not in SKIP), key=lambda x: x['size'])


def who(t):
    e = sy.get('0x%08X' % t)
    if e:
        return e['kb'][0] if e['kb'] else 'NO-FACT'
    s = next((s['name'] for s in sl if s['addr'] == t), None)
    return 'slot_' + s if s else 'UNKNOWN'


shown = 0
for x in cl:
    s = co[x['slot']]
    raw, b = bytes.fromhex(s['bytes']), int(s['addr'], 16)
    ins = decode_thumb(raw, b)
    if any(i.mnemonic == 'BL' and i.branch_target == DECK_WALKER for i in ins):
        continue
    print('==', s['name'], s['owner'], s['addr'], s['size'])
    pool = {}
    for i in ins:
        po = ''
        if i.is_pool_ref:
            k = i.pool_addr - b
            v = int.from_bytes(raw[k:k + 4], 'little') if 0 <= k <= len(raw) - 4 else None
            po = ' =0x%08X' % v if v is not None else ''
            pool[i.operands.split(',')[0]] = v
        t = i.branch_target if i.mnemonic == 'BL' else (
            (pool.get(i.operands.strip()) or 0) & ~1 if i.mnemonic == 'BLX' else None)
        if t:
            po += ' args%s %s' % (sorted(arg_regs(img, t)), who(t))
        print('  ', hex(i.addr), i.mnemonic, i.operands, po)
    shown += 1
    if shown >= n:
        break
