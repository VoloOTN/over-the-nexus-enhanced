"""CPU-vs-CPU round-robin battery: every deck.pac .ydc against every other, both seatings, in melonDS.

Reuses CardWorkshop's rig patcher (tools/wc2011/w11speed.py) and deck reader (tools/ydc.py); the rig here
(rig.c) reads a batch of pairings from the save file and writes each result back, so melonDS runs with the
JIT and no GDB; the host relaunches each worker per batch.

    build   rig ROM from rom_all_patches.nds
    run     play all missing pairings, append to results.jsonl (resumable)
    report  standings + hangs from results.jsonl
"""
import argparse
import fnmatch
import hashlib
import json
import os
import queue
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CW = Path(os.environ.get('CARDWORKSHOP', REPO.parent / 'CardWorkshop'))
sys.path[:0] = [str(CW / 'tools' / 'wc2011'), str(CW / 'tools'), str(REPO)]
import ndspy.rom  # noqa: E402
import w11speed  # noqa: E402
import ydc  # noqa: E402
from otn_enhanced.asm.effect_verify import assert_thumb1_only  # noqa: E402
from otn_enhanced.system import skip_animations  # noqa: E402

SRC_ROM = REPO / 'data/over_the_nexus/working/rom_all_patches.nds'
OUT = REPO / 'build/cpu_battery'
RIG_ROM = OUT / 'battery.nds'
RESULTS = OUT / 'results.jsonl'
MAGIC = 0x54544142
RUNTIME_MAGIC = 0x31314453  # View Mode runtime header 'SD11'
CHARA = {False: 309, True: 401}  # a regular / a turbo duelist (CardWorkshop base CPU lists)
BUSY_BREAK = 0x021460e8  # bne past the sub-pass back edge when the duel tick is busy
# save layout (rig.c)
SAV_BASE = 0x1000
TEMPLATE = OUT / 'formatted.sav'  # a save the game formatted itself, so boot keeps it
MAX_PAIRS = 24
RES_SIZE = 4 * 37 + 4 + 2 * 3 * 76  # struct Result (rig.c)


def PAIR(i):
    return SAV_BASE + 0x10 + i * 0x188


def RES(i):
    return PAIR(MAX_PAIRS) + i * RES_SIZE


PRESENT_POLL = 0x0214b490  # (presentation code) -> 1 while it is still playing, 0 when done
DRAIN_TABLE = 0x021c3c5e   # s16 per command op; arm = 0x021C3C60 + entry, a `bl handler ; pop {r3,pc}` stub


def present_poll_sites(ov3, op):
    """Thumb call sites of PRESENT_POLL inside the drain handler of command `op`
    (the handler runs from its entry to the next push {.., lr})."""
    arm = 0x021c3c60 + struct.unpack_from('<h', ov3.d, ov3.o(DRAIN_TABLE) + 2 * op)[0]
    h = w11speed.bl_target(ov3.d, ov3.o(arm), arm)
    end = h + 2
    while struct.unpack_from('<H', ov3.d, ov3.o(end))[0] & 0xff00 != 0xb500:
        end += 2
    return [at for at, t in w11speed.thumb_calls(ov3) if t & ~1 == PRESENT_POLL and h <= at < end]


def build(a):
    w11speed.RIG_SRC = str(HERE)
    r = w11speed.Rom11(str(SRC_ROM))
    runtime = next(s for s in r.code.sections if len(s.data) >= 16 and w11speed.u32(s.data, 4) == RUNTIME_MAGIC)
    story_config = w11speed.u32(runtime.data, 8)
    hi = r.arm9.word(w11speed.ARENA_HI_LIT)
    work = str(OUT / 'rig_work')
    defs = (('-DPROBE',) if a.probe else ()) + (('-DFRAMES',) if a.frames else ()) + \
        (('-DSKIP_WAIT',) if a.skip_wait else ())
    blob, syms = w11speed.compile_rig(work, hi - 0x10000, defs)
    base = (hi - len(blob)) & ~0xff
    blob, syms = w11speed.compile_rig(work, base, defs)
    text_end = min(v for k, v in syms.items() if not v & 1 and v >= base)
    assert_thumb1_only(bytes(blob[:text_end - base]), base)
    w11speed.put32(blob, syms['rig_story_config'] - base, story_config)
    r.arm9.set_word(w11speed.ARENA_HI_LIT, base, hi)
    r.arm9.set_word(w11speed.BOOT_CB_LIT, syms['rig_boot'], w11speed.BOOT_CB)
    r.ov[3].set_word(w11speed.EXIT_CB_LIT, syms['rig_boot'], w11speed.EXIT_CB)
    # bx pc ; nop ; ldr pc,[pc,#-4] ; .word cmd_push -- CardWorkshop w11speed's CMD_PUSH head patch
    r.ov[3].write(w11speed.CMD_PUSH, struct.pack('<HHII', 0x4778, 0x46c0, 0xe51ff004, syms['cmd_push']),
                  w11speed.CMD_PUSH_HEAD)
    if a.no_anim:
        r.ov[3].set_word(w11speed.LOOP_MODE_BNE, 0xea000004, 0x1a000004)
        r.ov[3].set_word(w11speed.LOOP_ITER_MOV, 0xe3a07000 | (a.no_anim - 1), 0xe1a07005)
        # notes/battle-speed-ar-findings.md "THE BUSY BREAK": the sub-pass loop drops to one pass whenever the
        # duel tick reports busy (animation or AI), so N passes only helped idle frames. Test ROM only.
        if not a.keep_busy_break:
            r.ov[3].set_word(BUSY_BREAK, 0xe1a00000, 0x1a000005)
    if a.skip_anim:
        for case, native in skip_animations.SKIP_CASES.items():
            e = skip_animations._entry(case)
            if skip_animations._branch_target(e, r.ov[3].word(e)) != native:
                raise SystemExit(f'skip_animations case {case}: not the stock branch')
            r.ov[3].set_word(e, skip_animations._retarget(e, skip_animations.DONE))
    if a.no_wait:
        # experiment: 0x0214B490(code) is the 'presentation code still playing?' poll (1 busy / 0 done) that
        # command handlers wait on after their state change (e.g. the shuffle handler 0x021C0BB4); answer 'done'
        r.ov[3].write(0x0214b490, struct.pack('<II', 0xe3a00000, 0xe12fff1e), struct.pack('<II', 0xe92d4ff8, 0xe59f5b70))
    for case in (int(x, 16) for x in (a.skip_codes or '').split(',') if x):
        # experiment, skip_animations' precedent: interpreter case `case` (= presentation code) returns 'done'
        # at once, so the sequence never starts and its 0x0214B490 poll has nothing to wait for
        e = skip_animations._entry(case)
        if r.ov[3].word(e) >> 24 != 0xea:
            raise SystemExit(f'interpreter case {case:#x} @ {e:#x} is not a b')
        r.ov[3].set_word(e, skip_animations._retarget(e, skip_animations.DONE))
    for op in (int(x, 16) for x in (a.skip_wait or '').split(',') if x):
        # experiment: inside command op's drain handler only, the presentation polls answer 'done'
        for site in present_poll_sites(r.ov[3], op):
            r.ov[3].hook(site, syms['rig_present_done'], PRESENT_POLL)
    if a.frames:
        # the per-frame pad read CardWorkshop's w11speed hooks (h_pad); rig_frame calls it, then counts
        for site in (0x020162e6, 0x0201634c):
            r.arm9.hook(site, syms['rig_frame'], 0x02014efc)
        # every other presentation poll is counted per code (rig_present_poll); --skip-wait sites already moved
        for site, t in w11speed.thumb_calls(r.ov[3]):
            if t & ~1 == PRESENT_POLL:
                r.ov[3].hook(site, syms['rig_present_poll'], PRESENT_POLL)
    r.extra.append((bytes(blob), base))
    out = Path(a.out) if a.out else RIG_ROM
    out.parent.mkdir(parents=True, exist_ok=True)
    r.save(str(out))
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f'{out}: rig {len(blob)} B at {base:#x} (arena top {hi:#x} -> {base:#x}), story_config {story_config:#x}, '
          f'passes {a.no_anim}, skip-anim {a.skip_anim}, probe {a.probe}, frames {a.frames}, sha256 {sha}')


def decks(pattern):
    """{name: (0xC0 deck record, turbo)}. Turbo = holds a Speed Spell, the only Spells a Turbo Duel allows
    (all 44 _rd, 40 wrd*, rtlr* decks)."""
    from carddb import CardDB, load_from_rom
    rom, prof, files = load_from_rom(str(SRC_ROM))
    speed = {c.id for c in CardDB.load(files, prof).cards[1:] if c.names['e'].startswith('Speed Spell')}
    names = {}
    for k, v in ydc.rom_decks(rom).items():
        deck = ydc.Deck.parse(v)
        names[k[5:-4]] = (w11speed.deck_words(deck, k), any(c in speed for c in deck.main))
    if pattern:
        pats = pattern.split(',')
        names = {k: v for k, v in names.items() if any(fnmatch.fnmatch(k, p) for p in pats)}
    return names


def seed_of(x, y):
    return int.from_bytes(hashlib.sha256(f'{x}|{y}'.encode()).digest()[:4], 'little')


def tile_geometry(k, w=276, h=448):
    """Qt saveGeometry blob (v3) putting worker k's window in a grid over the desktop work area (no overlap).
    w x h = melonDS's measured outer window size plus a small gap."""
    import base64
    import ctypes
    import ctypes.wintypes as wt
    wa = wt.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(wa), 0)  # SPI_GETWORKAREA
    sw = ctypes.windll.user32.GetSystemMetrics(0)
    cols = max(1, (wa.right - wa.left) // w)
    rows = max(1, (wa.bottom - wa.top) // h)
    x, y = wa.left + 8 + (k % cols) * w, wa.top + 31 + (k // cols % rows) * h  # +8/+31 = Qt frame margins
    frame, client = (x, y, x + 255, y + 435), (x, y + 31, x + 255, y + 435)
    return base64.b64encode(struct.pack('>IHH4i4iiBBi4i', 0x01D9D0CB, 3, 0, *frame, *client, 0, 0, 0, sw,
                                        *client)).decode()


class Worker:
    """One melonDS process (JIT on) in its own portable folder. Input and output go through battery.sav:
    the host writes a batch of pairings before boot, the rig writes each result back (rig.c save layout)."""

    def __init__(self, k, gl=False):
        self.k = k
        self.dir = OUT / f'w{k}'
        self.dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / 'melonDS.exe', self.dir / 'melonDS.exe')
        t = (REPO / 'melonDS.toml').read_text()
        t = re.sub(r'(?m)^RecentROM = .*$', 'RecentROM = []', t)
        t = re.sub(r'(?m)^Volume = .*$', 'Volume = 0', t)
        t = re.sub(r'(?m)^LimitFPS = .*$', 'LimitFPS = false', t)
        t = re.sub(r'(\[JIT\]\n(?:[^\[\n].*\n|\n)*?)Enable = \w+', r'\1Enable = true', t)
        # 3D renderer: 0 software (CPU, plus a render thread), 1 OpenGL (GPU); duel logic is unaffected
        t = re.sub(r'(\[3D\]\n(?:[^\[\n].*\n|\n)*?)Renderer = \d+', rf'\g<1>Renderer = {1 if gl else 0}', t)
        t = re.sub(r'(\[Instance0\.Gdb\]\n(?:[^\[\n].*\n|\n)*?)Enabled = \w+', r'\1Enabled = false', t)
        (self.dir / 'melonDS.toml').write_text(t)
        self.rom = self.dir / 'battery.nds'
        # relink unless this worker's ROM IS the current rig (an mtime test let a newer foreign rig, linked by another run,
        # stay in w0..w5 and silently replace the ROM a later gauntlet believed it was playing)
        if not self.rom.exists() or not os.path.samefile(self.rom, RIG_ROM):
            self.rom.unlink(missing_ok=True)
            os.link(RIG_ROM, self.rom)
        self.sav = self.rom.with_suffix('.sav')
        self.proc = None

    def launch(self):
        # Qt restores the window from the toml, and melonDS rewrites it when the window moves: re-tile on every launch
        p = self.dir / 'melonDS.toml'
        p.write_text(re.sub(r'(?m)^Geometry = .*$', f'Geometry = "{tile_geometry(self.k)}"', p.read_text(), count=1))
        self.stop()
        self.proc = subprocess.Popen([str(self.dir / 'melonDS.exe'), str(self.rom)], cwd=self.dir,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        self.proc = None

    def batch(self, pairs, timeout, emit):
        """Play pairs [(seed, turbo, deck0, deck1)] in one boot. emit(i, result) per finished duel.
        Returns the number of pairs finished; the caller requeues the rest after a hang/crash."""
        sav = bytearray(template(self))
        struct.pack_into('<4I', sav, SAV_BASE, MAGIC, len(pairs), 0, 0)
        for i, (seed, turbo, d0, d1) in enumerate(pairs):
            sav[PAIR(i):PAIR(i) + 0x188] = struct.pack('<I2H', seed, CHARA[turbo], turbo) + d0 + d1
        self.sav.write_bytes(sav)
        self.launch()
        done, t_last = 0, time.time()
        try:
            while done < len(pairs):
                time.sleep(2)
                try:
                    data = self.sav.read_bytes()
                except OSError:  # melonDS mid-flush
                    continue
                magic, _, now = struct.unpack_from('<3I', data, SAV_BASE) if len(data) > SAV_BASE else (0, 0, 0)
                if magic != MAGIC:
                    raise RuntimeError(f'worker {self.k}: battery header gone from {self.sav} (save reformatted?)')
                for i in range(done, min(now, len(pairs))):
                    w = struct.unpack_from('<37I2H', data, RES(i))
                    emit(i, {'status': 'done', 'lp': list(w[1:3]), 'deck_left': list(w[3:5]), 'duel': list(w[5:37]),
                             'mode': list(w[37:39]), 'turns': w[5 + 16] + 1,
                             'stats': [[list(data[RES(i) + 152 + 228 * s + 76 * k:][:76]) for k in range(3)]
                                       for s in range(2)],
                             'wall': round(time.time() - t_last, 1)})
                    t_last = time.time()
                if now > done:
                    done = min(now, len(pairs))
                elif self.proc.poll() is not None:
                    emit(done, {'status': 'crash', 'wall': round(time.time() - t_last, 1)})
                    return done + 1
                elif time.time() - t_last > timeout:
                    emit(done, {'status': 'hang', 'wall': round(time.time() - t_last, 1)})
                    return done + 1
            return done
        finally:
            self.stop()


_template_lock = threading.Lock()


def template(w):
    """The game reformats a save without its ID at boot, wiping the batch: boot once on a blank save and keep
    what the game writes."""
    with _template_lock:
        if not TEMPLATE.exists():
            w.sav.write_bytes(b'\xff' * 0x10000)
            w.launch()
            try:
                t0 = time.time()
                while not w.sav.read_bytes().startswith(b'wcs2011'):
                    if time.time() - t0 > 60:
                        raise RuntimeError('the game never formatted the blank save')
                    time.sleep(1)
                time.sleep(3)  # let melonDS finish the flush
            finally:
                w.stop()
            data = w.sav.read_bytes()
            if any(b != 0xff for b in data[SAV_BASE:RES(MAX_PAIRS)]):
                raise RuntimeError('the formatted save uses the battery range')
            TEMPLATE.write_bytes(data)
        return TEMPLATE.read_bytes()


def play(games, jobs, timeout, gl, on_result):
    """Play games [(key, seed, turbo, deck0, deck1)] across `jobs` melonDS workers, in save-file batches.
    on_result(key, result, worker) runs under a lock once per game, including hangs and crashes."""
    q = queue.Queue()
    for g in games:
        q.put(g)
    lock = threading.Lock()
    size = max(1, min(MAX_PAIRS, -(-len(games) // max(1, jobs))))  # small runs still use every worker

    def work(k):
        w = Worker(k, gl)
        while True:
            chunk = []
            while len(chunk) < size:
                try:
                    chunk.append(q.get_nowait())
                except queue.Empty:
                    break
            if not chunk:
                return

            def emit(i, res):
                with lock:
                    on_result(chunk[i][0], res, k)

            got = w.batch([g[1:] for g in chunk], timeout, emit)
            for g in chunk[got:]:
                q.put(g)

    threads = [threading.Thread(target=work, args=(k,), daemon=True) for k in range(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def run(a):
    pool = decks(a.decks)
    done = set()
    if RESULTS.exists():
        for line in RESULTS.read_text().splitlines():
            r = json.loads(line)
            done.add((r['a'], r['b']))
    todo = [(x, y) for x in pool for y in pool if x != y and pool[x][1] == pool[y][1] and (x, y) not in done]
    print(f'{len(pool)} decks ({sum(t for _, t in pool.values())} turbo; regular never meets turbo), {len(done)} duels already recorded, {len(todo)} to play, {a.jobs} workers', flush=True)
    t_start, n_done = time.time(), [0]

    def on_result(key, res, k):
        x, y = key
        with RESULTS.open('a') as f:
            f.write(json.dumps({'a': x, 'b': y, 'turbo': pool[x][1], 'seed': seed_of(x, y), **res}) + '\n')
        n_done[0] += 1
        rate = n_done[0] / (time.time() - t_start) * 3600
        print(f'[w{k}] {x} vs {y}: {res["status"]} lp {res.get("lp")} {res.get("wall")} s '
              f'| {n_done[0]}/{len(todo)}, {rate:.0f}/h, eta {(len(todo) - n_done[0]) / max(rate, 1e-9):.1f} h',
              flush=True)

    play([((x, y), seed_of(x, y), pool[x][1], pool[x][0], pool[y][0]) for x, y in todo], a.jobs, a.timeout, a.gl,
         on_result)


def winner(r):
    """0 = side a, 1 = side b, None = undecided. LP <= 0 loses (lp is u32: negative wraps), then deck-out."""
    lost = [lp == 0 or lp >= 0x80000000 for lp in r['lp']]
    if lost[0] != lost[1]:
        return 1 if lost[0] else 0
    out = [n == 0 for n in r['deck_left']]
    if out[0] != out[1]:
        return 1 if out[0] else 0
    return None


def card_stats(rows, out=None, only=None):
    """card_stats.csv: per card, over every finished duel of every deck running it, how often it was drawn,
    summoned (Normal + Flip + Special) and had an effect activated; duels counts each deck that ran it once per
    duel. card_stats_by_deck.csv: the same per deck. Both sorted by summoned, then activated, highest first.
    Counts are per deck slot (rig.c), merged by cid. only = count just that deck (a gauntlet)."""
    import csv
    from carddb import CardDB, load_from_rom
    rom, prof, files = load_from_rom(str(SRC_ROM))
    # the game's text stores the Meklord Emperors' infinity sign as byte 0x90
    names = {c.id: c.names['e'].replace('\x90', '∞') for c in CardDB.load(files, prof).cards[1:]}
    decks = {k[5:-4]: ydc.Deck.parse(v) for k, v in ydc.rom_decks(rom).items()}
    tot, duels = {}, {}
    for r in rows:
        if r['status'] != 'done' or 'stats' not in r:
            continue
        for side, name in enumerate((r['a'], r['b'])):
            if only and name != only:
                continue
            d = decks[name]
            duels[name] = duels.get(name, 0) + 1
            for k, cid in [(i, c) for i, c in enumerate(d.main[:60])] + [(60 + i, c) for i, c in enumerate(d.extra[:15])]:
                t = tot.setdefault((name, cid), [0, 0, 0])
                for j in range(3):
                    t[j] += r['stats'][side][j][k]
    out = Path(out or OUT / 'card_stats.csv')
    by_card = {}
    for (name, cid), t in tot.items():
        c = by_card.setdefault(cid, [0, 0, 0, 0])
        c[0] += duels[name]
        for j in range(3):
            c[j + 1] += t[j]
    rank = lambda kv: (-kv[1][-2], -kv[1][-1])  # summoned, then activated
    with out.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['card', 'cid', 'duels', 'drawn', 'summoned', 'activated'])
        for cid, (du, dr, su, ac) in sorted(by_card.items(), key=rank):
            w.writerow([names.get(cid, ''), cid, du, dr, su, ac])
    with out.with_name('card_stats_by_deck.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['deck', 'card', 'cid', 'duels', 'drawn', 'summoned', 'activated'])
        for (name, cid), (dr, su, ac) in sorted(tot.items(), key=rank):
            w.writerow([name, names.get(cid, ''), cid, duels[name], dr, su, ac])
    print(f'card stats: {out} (+ {out.with_name("card_stats_by_deck.csv").name})')


def turns_of(r):
    """Turns played. duel[16] is 0x0229DD54, the 0-based index of the current turn (3 probe duels: 45/8/15 at the
    end, with 46/9/16 turn-start ops in their logs)."""
    return r.get('turns', r['duel'][16] + 1)


def report(a):
    rows = [json.loads(line) for line in RESULTS.read_text().splitlines()]
    st, turns = {}, {}
    bad = []
    for r in rows:
        for d in (r['a'], r['b']):
            st.setdefault(d, [0, 0, 0, 0])
        if r['status'] != 'done':
            bad.append(r)
            st[r['a']][3] += 1
            st[r['b']][3] += 1
            continue
        w = winner(r)
        if w is None:
            st[r['a']][2] += 1
            st[r['b']][2] += 1
        else:
            st[(r['a'], r['b'])[w]][0] += 1
            st[(r['a'], r['b'])[1 - w]][1] += 1
        for d in (r['a'], r['b']):
            turns.setdefault(d, []).append(turns_of(r))
    lines = ['| deck | W | L | D | hang/crash | win % | avg turns |', '|---|---|---|---|---|---|---|']
    for d, (w, l, dr, h) in sorted(st.items(), key=lambda kv: -kv[1][0] / max(1, sum(kv[1][:3]))):
        t = turns.get(d, [])
        lines.append(f'| {d} | {w} | {l} | {dr} | {h} | {100 * w / max(1, w + l + dr):.1f} | '
                     f'{sum(t) / len(t):.1f} |' if t else f'| {d} | {w} | {l} | {dr} | {h} | 0.0 | - |')
    lines += ['', f'## Not finished ({len(bad)})', ''] + [f'- {r["a"]} vs {r["b"]}: {r["status"]} {r.get("error", "")}'
                                                          for r in bad]
    card_stats(rows)
    out = OUT / 'standings.md'
    out.write_text(f'# CPU battery: {len(rows)} duels\n\n' + '\n'.join(lines) + '\n')
    print('\n'.join(lines[:22]))
    print(f'... full table: {out}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('build')
    p.add_argument('--no-anim', type=int, default=32,
                   help='duel loop passes per frame, busy frames included (0 = stock; max 64)')
    p.add_argument('--no-skip-anim', dest='skip_anim', action='store_false',
                   help='keep the 5 cut-in commands otn_enhanced/system/skip_animations.py skips')
    p.add_argument('--probe', action='store_true', help='log every duel command into the save (run with --batch 1)')
    p.add_argument('--frames', action='store_true',
                   help='experiment: count frames per duel and frames with a duel command queued/running '
                        '(written over duel[30] / duel[31])')
    p.add_argument('--no-wait', action='store_true',
                   help='experiment: presentation poll 0x0214B490 always answers "done"')
    p.add_argument('--keep-busy-break', action='store_true',
                   help='experiment: leave the busy break in, as CardWorkshop w11speed --no-anim does')
    p.add_argument('--skip-codes', metavar='CODES',
                   help='experiment: comma-separated hex presentation codes whose interpreter case ends at once')
    p.add_argument('--skip-wait', metavar='OPS',
                   help='experiment: comma-separated hex command ops whose handlers stop waiting on presentation')
    p.add_argument('--out', help='write the ROM here instead of build/cpu_battery/battery.nds')
    p.set_defaults(fn=build)
    p = sub.add_parser('run')
    p.add_argument('--decks', help='comma-separated fnmatch patterns on deck names (no deck/ or .ydc)')
    p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--timeout', type=float, default=900, help='seconds before a duel counts as a hang')
    p.add_argument('--gl', action='store_true', help='OpenGL 3D renderer: moves DS 3D drawing to the GPU')
    p.set_defaults(fn=run)
    p = sub.add_parser('report')
    p.set_defaults(fn=report)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
