"""Verify a NEW CARD through the CPU: does it land (CPU row), and does the CPU play it (mirror duels)?

The CPU plays itself in melonDS, so this is automatic evidence that a card is reachable and activates. It is NOT in-game
confirmation (CLAUDE.md > Verification Rules): only the user can confirm a card works.

    uv run python -m otn_enhanced.tools.cpu_battery.cardtest rows  <rom> <cid> [<cid> ...]
    uv run python -m otn_enhanced.tools.cpu_battery.cardtest rig   <rom>
    uv run python -m otn_enhanced.tools.cpu_battery.cardtest mirror <rom> <cid> [--kit "Name:n,Name:n"] \\
                                   [--extra "Name,Name"] [--duels 16] [--jobs 4] [--fodder lightsworn|none]

rows   static, no emulator: the ov5 CPU candidate rows {id | loc<<14 | param<<18, evaluator} a cid inherited from its donor
       and whether the evaluator is the LP-effect one that rejects anything without an LP-table entry (0x02311084; this
       is what stopped That Grass Looks Greener, notes/that-grass-looks-greener-findings.md).
rig    build the battery rig ROM from <rom> -> build/cpu_battery/cardtest/rig_<rom>.nds
mirror a 40-card deck (3 x the card + the kit that supplies its targets + filler) plays an identical copy of itself on that
       rig; prints drawn / summoned / activated for the card and its kit. drawn > 0 with activated == 0 is a defect to
       explain (or a missing target in the kit); activated > 0 means the CPU can play it.
Workers live under build/cpu_battery/cardtest/ so a run never touches the shared w0..w5 folders of a gauntlet.
Never kill melonDS by process name: the user may have their own instance open.
"""
import argparse
import csv
import json
import struct
import sys
from pathlib import Path

from otn_enhanced.tools.cpu_battery import battery as B

LP_EVALUATORS = {0x0231111D, 0x02311129, 0x02311135}   # thunks into the LP-effect evaluator 0x02311084 / 0x02311130
ALWAYS_TRUE = 0x023107C1                               # movs r0,#1 ; bx lr  (the evaluator of 145 stock rows)
FODDER = ['Wulf, Lightsworn Beast', 'Jain, Lightsworn Paladin', 'Lyla, Lightsworn Sorceress', 'Ryko, Lightsworn Hunter',
          'Lumina, Lightsworn Summoner', 'Ehren, Lightsworn Monk', 'Aurkus, Lightsworn Druid', 'Garoth, Lightsworn Warrior']
WORK = B.REPO / 'build/cpu_battery/cardtest'


def _ov5(rom_path):
    import ndspy.rom
    o = ndspy.rom.NintendoDSRom.fromFile(str(rom_path)).loadArm9Overlays([5])[5]
    return bytes(o.data), o.ramAddress


def rows(a):
    d, base = _ov5(a.rom)
    cids = {int(c, 0) for c in a.cids}
    found, share = {}, {}
    for off in range(0x02390000 - base, min(len(d), 0x02397200 - base) - 8, 4):
        w, h = struct.unpack_from('<II', d, off)
        if (w >> 16) and (w >> 16) & 0xFFF0 == 0 and (w & 0x3FFF) >= 0xD00 and h & 1 and base <= h < base + len(d):
            share[h] = share.get(h, 0) + 1
            if (w & 0x3FFF) in cids:
                found.setdefault(w & 0x3FFF, []).append((base + off, w, h))
    for c in sorted(cids):
        if c not in found:
            print(f'0x{c:04X}: no ov5 CPU row (a monster/new cid has none: the CPU plays it through its own cond/cost)')
        for addr, w, h in found.get(c, []):
            tag = ' <== LP-EFFECT EVALUATOR: returns 0 for a cid with no LP entry; set the word at +4 to 0x023107C1' \
                if h in LP_EVALUATORS else (' (always-true)' if h == ALWAYS_TRUE else '')
            print(f'0x{c:04X}: row {addr:#x} id {w:#x} evaluator {h:#x} (shared by {share[h]} rows){tag}')


def rig(a, quiet=False):
    WORK.mkdir(parents=True, exist_ok=True)
    src = Path(a.rom).resolve()
    out = WORK / f'rig_{src.stem}.nds'
    B.SRC_ROM = src
    sys.argv = ['battery', 'build', '--out', str(out)]
    B.main()
    return out


def _names(rom):
    sys.path[:0] = [str(B.CW / 'tools')]
    from carddb import CardDB, load_from_rom
    r, prof, files = load_from_rom(str(rom))
    return {c.names['e'].replace('\x90', '∞'): c.id for c in CardDB.load(files, prof).cards[1:]}


def mirror(a):
    import w11speed
    import ydc
    src = Path(a.rom).resolve()
    n2c = _names(src)
    cid = int(a.cid, 0)
    kit, missing = [], []
    for part in filter(None, (a.kit or '').split(',')):
        name, _, n = part.rpartition(':') if ':' in part else (part, '', '3')
        (kit if name in n2c else missing).append((name, int(n or 3)))
    extra = [n for n in filter(None, (a.extra or '').split(','))]
    missing += [(n, 0) for n in extra if n not in n2c]
    if missing:
        raise SystemExit(f'not in this ROM: {[m[0] for m in missing if m[0] not in n2c]}')
    in_extra = any(n2c[n] == cid for n in extra)         # an Extra Deck card (Synchro/Fusion): never put it in the Main Deck
    main = [] if in_extra else [cid] * 3
    for name, n in kit:
        main += [n2c[name]] * n
    fodder = [n2c[n] for n in FODDER if n in n2c] if a.fodder == 'lightsworn' else []
    cap = 3                                  # raise the per-card cap when a small kit leaves too few distinct fillers
    while len(main) < 40 and fodder:
        before = len(main)
        for c in fodder:
            if len(main) < 40 and main.count(c) < cap:
                main.append(c)
        if len(main) == before:
            cap += 1
    deck = ydc.Deck(main=main[:60], extra=[n2c[n] for n in extra])
    words = w11speed.deck_words(deck, f'cardtest {cid:#x}')
    rigrom = WORK / f'rig_{src.stem}.nds'
    if not rigrom.exists():
        rig(a)
    B.SRC_ROM, B.RIG_ROM = src, rigrom
    B.OUT = B.REPO / 'build/cpu_battery' / (a.work or f'cardtest_{cid:#06x}')           # workers under <work>/w*, never the shared w0..w5
    games = [(f'{i}', B.seed_of('cardtest', f'{cid}|{i}'), False, words, words) for i in range(a.duels)]
    tot = {'card': [0, 0, 0], 'kit': [0, 0, 0]}
    done = [0]

    def on_result(key, r, k):
        done[0] += 1
        if r.get('status') != 'done':
            print(f'duel {key}: {r.get("status")}', flush=True)
            return
        for s in (0, 1):
            for idx, c in [(i, c) for i, c in enumerate(main[:60])] + [(60 + i, n2c[n]) for i, n in enumerate(extra[:15])]:
                t = tot['card'] if c == cid else tot['kit']
                for j in range(3):
                    t[j] += r['stats'][s][j][idx]
        print(f'[w{k}] {done[0]}/{len(games)}', flush=True)

    B.play(games, a.jobs, a.timeout, False, on_result)
    out = WORK / f'mirror_{cid:#06x}.csv'
    with out.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['what', 'drawn', 'summoned', 'activated'])
        w.writerow([f'card 0x{cid:04X} (x3, both seats)', *tot['card']])
        w.writerow(['kit', *tot['kit']])
    print(f'MIRROR {cid:#06x}: {a.duels} duels, card drawn/summoned/activated = {tot["card"]}, kit = {tot["kit"]} -> {out}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('rows')
    p.add_argument('rom')
    p.add_argument('cids', nargs='+')
    p.set_defaults(fn=rows)
    p = sub.add_parser('rig')
    p.add_argument('rom')
    p.set_defaults(fn=lambda a: print(rig(a)))
    p = sub.add_parser('mirror')
    p.add_argument('rom')
    p.add_argument('cid')
    p.add_argument('--kit', help='"Name:copies,Name:copies" -- the cards that supply the effect\'s targets / cost')
    p.add_argument('--extra', help='"Name,Name" -- Extra Deck cards')
    p.add_argument('--duels', type=int, default=16)
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--fodder', choices=['lightsworn', 'none'], default='lightsworn')
    p.add_argument('--timeout', type=float, default=300, help='seconds without a result before a duel counts as a hang')
    p.add_argument('--work', default=None, help='worker folder under build/cpu_battery (default cardtest_<cid>: one folder per card, so two runs of different cards never share workers)')
    p.set_defaults(fn=mirror)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
