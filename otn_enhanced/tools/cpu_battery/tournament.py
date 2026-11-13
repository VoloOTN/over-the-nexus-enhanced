"""CPU-vs-CPU Swiss tournaments with a single-elimination top cut, on the battery ROM (battery.py), with history.

Every match is best of 5 with the first player alternating. Each tournament lives in data/cpu_tournaments/<id>/:
meta.json (settings, deck list, ROM hashes), games.jsonl (every game, incl. per-card stats and turns),
standings.md, bracket.md, card_stats.csv, summary.json. Finished tournaments also append one line to
data/cpu_tournaments/history.jsonl, so results can be compiled across tournaments later.

The tournament state is a pure function of games.jsonl, so a stopped tournament resumes by running it again.

    run --pool regular|turbo [--rounds N] [--cut 32] [--id ID]   start, or resume ID
    selftest                                                       check the pairing/bracket logic offline
"""
import argparse
import datetime
import hashlib
import json
import math
import queue
import sys
import threading
import time
from pathlib import Path

from otn_enhanced.tools.cpu_battery import battery

HISTORY = battery.REPO / 'data' / 'cpu_tournaments'
SWISS_BO, CUT_BO = 3, 5  # new tournaments: best of 3 in the Swiss rounds, best of 5 in the top cut


def best_of(meta, stage):
    """Match length of a stage ('s<r>' Swiss, 'b<n>' bracket). Tournaments started before the split
    recorded a single best_of, used for both, so they replay and resume exactly as they were played."""
    return meta.get('cut_best_of' if stage[0] == 'b' else 'swiss_best_of', meta.get('best_of', CUT_BO))


def h32(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:4], 'little')


def sha256(path):
    d = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            d.update(block)
    return d.hexdigest()


class Match:
    """x is the higher-ranked deck. Game g (1-based) puts x on side 0 when g is odd, so the first player
    alternates. Only as many games are scheduled as the leader still needs to reach a majority of best_of."""

    def __init__(self, tid, stage, x, y, games, best_of=CUT_BO):
        self.tid, self.stage, self.x, self.y = tid, stage, x, y
        self.best_of, self.win = best_of, best_of // 2 + 1
        self.played = []  # (game number, winning deck or None)
        n = 1
        while f'{stage}/{x}/{y}/g{n}' in games:
            r = games[f'{stage}/{x}/{y}/g{n}']
            w = battery.winner(r) if r['status'] == 'done' else None
            self.played.append((n, None if w is None else (r['a'], r['b'])[w]))
            n += 1

    def wins(self, d):
        return sum(1 for _, w in self.played if w == d)

    @property
    def decided(self):
        return max(self.wins(self.x), self.wins(self.y)) >= self.win or len(self.played) >= self.best_of

    def needed(self):
        """Games still to play right now: [(key, a, b, seed)]."""
        if self.decided:
            return []
        n0 = len(self.played) + 1
        k = min(self.best_of - len(self.played), self.win - max(self.wins(self.x), self.wins(self.y)))
        out = []
        for n in range(n0, n0 + k):
            a, b = (self.x, self.y) if n % 2 else (self.y, self.x)
            out.append((f'{self.stage}/{self.x}/{self.y}/g{n}', a, b, h32(self.tid, self.stage, self.x, self.y, n)))
        return out

    def result(self):
        """Winning deck, or None for a drawn match (only possible when games are drawn or unfinished)."""
        wx, wy = self.wins(self.x), self.wins(self.y)
        return self.x if wx > wy else self.y if wy > wx else None


class Standings:
    def __init__(self, decks):
        self.decks = decks
        self.points = dict.fromkeys(decks, 0)
        self.mw = dict.fromkeys(decks, 0)  # match wins, byes included
        self.mp = dict.fromkeys(decks, 0)  # matches played, byes included
        self.gw = dict.fromkeys(decks, 0)
        self.gp = dict.fromkeys(decks, 0)
        self.opp = {d: [] for d in decks}
        self.byes = set()

    def add(self, m):
        w = m.result()
        for d, o in ((m.x, m.y), (m.y, m.x)):
            self.opp[d].append(o)
            self.mp[d] += 1
            self.gw[d] += m.wins(d)
            self.gp[d] += len(m.played)
            if w == d:
                self.points[d] += 3
                self.mw[d] += 1
            elif w is None:
                self.points[d] += 1

    def bye(self, d):
        self.byes.add(d)
        self.points[d] += 3
        self.mw[d] += 1
        self.mp[d] += 1

    def mwp(self, d):
        return max(1 / 3, self.mw[d] / self.mp[d]) if self.mp[d] else 1 / 3

    def omw(self, d):
        return sum(map(self.mwp, self.opp[d])) / len(self.opp[d]) if self.opp[d] else 0

    def gwp(self, d):
        return self.gw[d] / self.gp[d] if self.gp[d] else 0

    def order(self, salt):
        return sorted(self.decks, key=lambda d: (-self.points[d], -self.omw(d), -self.gwp(d), h32(salt, d)))


def swiss_pairs(st, ranked, salt):
    """[(x, y)] top-down within the ranking, avoiding rematches where possible, plus the bye deck (or None):
    the lowest-ranked deck that has not had one."""
    ranked = list(ranked)
    bye = None
    if len(ranked) % 2:
        bye = next((d for d in reversed(ranked) if d not in st.byes), ranked[-1])
        ranked.remove(bye)
    pairs, free = [], ranked
    while free:
        d = free.pop(0)
        e = next((o for o in free if o not in st.opp[d]), free[0])  # ponytail: greedy, a rematch only when forced
        free.remove(e)
        pairs.append((d, e))
    return pairs, bye


def bracket_order(n):
    """Seed numbers in bracket order: 1 and 2 can only meet in the final (n = 8 -> 1 8 4 5 2 7 3 6)."""
    cur = [1]
    while len(cur) < n:
        m = 2 * len(cur)
        cur = [x for s in cur for x in (s, m + 1 - s)]
    return cur


def simulate(meta, games):
    """Replay the tournament from recorded games. Returns (games to play now, state)."""
    tid, decks = meta['id'], meta['decks']
    st = Standings(decks)
    rounds = []
    for r in range(1, meta['rounds'] + 1):
        ranked = st.order(f'{tid}|r{r}') if r > 1 else sorted(decks, key=lambda d: h32(tid, 'r1', d))
        pairs, bye = swiss_pairs(st, ranked, f'{tid}|r{r}')
        ms = [Match(tid, f's{r}', x, y, games, best_of(meta, 's')) for x, y in pairs]
        rounds.append((ms, bye))
        need = [g for m in ms for g in m.needed()]
        if need:
            return need, {'stage': f'Swiss round {r}/{meta["rounds"]}', 'standings': st, 'rounds': rounds}
        for m in ms:
            st.add(m)
        if bye:
            st.bye(bye)
    final = st.order(f'{tid}|final')
    cut = final[:meta['cut']]
    alive = [cut[s - 1] for s in bracket_order(len(cut))]
    seed = {d: i + 1 for i, d in enumerate(cut)}
    bracket = []
    b = 1
    while len(alive) > 1:
        ms = []
        for i in range(0, len(alive), 2):
            x, y = sorted(alive[i:i + 2], key=seed.get)
            ms.append(Match(tid, f'b{b}', x, y, games, best_of(meta, 'b')))
        bracket.append(ms)
        need = [g for m in ms for g in m.needed()]
        if need:
            return need, {'stage': f'Top {len(alive)}', 'standings': st, 'rounds': rounds, 'bracket': bracket,
                          'final': final, 'seed': seed}
        alive = [m.result() or m.x for m in ms]  # a drawn bracket match goes to the higher seed
        b += 1
    return [], {'stage': 'finished', 'standings': st, 'rounds': rounds, 'bracket': bracket, 'final': final,
                'seed': seed, 'champion': alive[0]}


def write_reports(tdir, meta, games, state):
    st, final = state['standings'], state.get('final') or state['standings'].order(meta['id'] + '|final')
    lines = [f'# {meta["id"]}: Swiss standings ({state["stage"]})', '',
             '| # | deck | points | match W-L-D | OMW% | GW% |', '|---|---|---|---|---|---|']
    for i, d in enumerate(final, 1):
        lw =[m for ms, _ in state['rounds'] for m in ms if d in (m.x, m.y) and m.decided]
        l_ = sum(1 for m in lw if m.result() not in (d, None))
        dr = sum(1 for m in lw if m.result() is None)
        lines.append(f'| {i} | {d} | {st.points[d]} | {st.mw[d]}-{l_}-{dr} | {100 * st.omw(d):.1f} | '
                     f'{100 * st.gwp(d):.1f} |')
    (tdir / 'standings.md').write_text('\n'.join(lines) + '\n')
    lines = [f'# {meta["id"]}: Top {meta["cut"]} bracket', '']
    for ms in state.get('bracket', []):
        lines.append(f'## Top {2 * len(ms)}')
        for m in ms:
            seed = state['seed']
            score = f'{m.wins(m.x)}-{m.wins(m.y)}' + (f' ({len(m.played)} games)' if m.played else '')
            res = m.result() if m.decided else None
            tail = f' -> **{res or m.x}**' + (' (drawn, higher seed advances)' if m.decided and res is None else '') \
                if m.decided else ''
            lines.append(f'- ({seed[m.x]}) {m.x} vs ({seed[m.y]}) {m.y}: {score}{tail}')
        lines.append('')
    if 'champion' in state:
        lines.append(f'**Champion: {state["champion"]}**')
    (tdir / 'bracket.md').write_text('\n'.join(lines) + '\n')
    battery.card_stats(list(games.values()), tdir / 'card_stats.csv')


def summary(meta, state):
    st, br = state['standings'], state['bracket']
    place = {}
    for i, ms in enumerate(reversed(br)):  # final first
        for m in ms:
            loser = m.y if (m.result() or m.x) == m.x else m.x
            place[loser] = 2 ** i + 1  # final loser 2, semi-final losers 3, ...
    place[state['champion']] = 1
    return {'id': meta['id'], 'finished': datetime.datetime.now().isoformat(timespec='seconds'),
            'pool': meta['pool'], 'decks': len(meta['decks']), 'rounds': meta['rounds'], 'cut': meta['cut'],
            'swiss_best_of': best_of(meta, 's'), 'cut_best_of': best_of(meta, 'b'), 'rom': meta['rom'],
            'champion': state['champion'],
            'placements': dict(sorted(place.items(), key=lambda kv: kv[1])),
            'swiss': [{'deck': d, 'rank': i + 1, 'points': st.points[d], 'omw': round(st.omw(d), 4),
                       'gwp': round(st.gwp(d), 4)} for i, d in enumerate(state['final'])]}


def progress(meta, need):
    """(label, matches in this round, matches still open in it, matches in later rounds) for the stage `need`
    belongs to: Swiss round r has len(decks) // 2 matches and the top cut cut - 1; bracket round b with m open
    matches started with m (no match is decided before its round is played) and leaves m - 1 after it."""
    stage = need[0][0].split('/')[0]
    open_ = len({g[0].rsplit('/', 1)[0] for g in need})
    if stage[0] == 's':
        r, per = int(stage[1:]), len(meta['decks']) // 2
        return f'round {r}/{meta["rounds"]}', per, open_, (meta['rounds'] - r) * per + meta['cut'] - 1
    size = meta['cut'] >> (int(stage[1:]) - 1)
    return f'top {size}', size // 2, open_, size // 2 - 1


def play_matches(meta, need, games, record, jobs, timeout, pool, worker=None):
    """One worker per best-of-5 match: play what the match still needs (one emulator boot), re-check it, play
    game 4/5 if it is still open, then take the next match. Returns when every match with games in `need`
    is decided. record(game, result, worker) runs under a lock and must add the game to `games`."""
    turbo = meta['pool'] == 'turbo'
    q = queue.Queue()
    for prefix in dict.fromkeys(g[0].rsplit('/', 1)[0] for g in need):  # 'stage/x/y', each match once
        q.put(prefix)
    lock = threading.Lock()
    label, per_round, open_, later = progress(meta, need)
    done = [per_round - open_]

    def work(k):
        w = (worker or battery.Worker)(k)
        while True:
            try:
                stage, x, y = q.get_nowait().split('/')
            except queue.Empty:
                return
            while True:
                with lock:
                    m = Match(meta['id'], stage, x, y, games, best_of(meta, stage))
                    todo = m.needed()
                    if not todo:
                        done[0] += 1
                        w_ = m.result()
                        res = f'{w_} beats {y if w_ == x else x} {max(m.wins(x), m.wins(y))}-' \
                              f'{min(m.wins(x), m.wins(y))}' if w_ else f'{x} vs {y} drawn'
                        print(f'[w{k}] {label} decided: {res} | {done[0]}/{per_round} matches done this round '
                              f'| {per_round - done[0] + later} matches left in the tournament', flush=True)
                if not todo:
                    break

                def emit(i, res, todo=todo):
                    with lock:
                        record(todo[i], res, k)

                # a hang or crash is recorded for its game and ends the batch; the loop re-checks the match
                w.batch([(g[3], turbo, pool[g[1]][0], pool[g[2]][0]) for g in todo], timeout, emit)

    threads = [threading.Thread(target=work, args=(k,), daemon=True) for k in range(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def run(a):
    pool = battery.decks(a.decks)
    if a.id and (HISTORY / a.id / 'meta.json').exists():
        meta = json.loads((HISTORY / a.id / 'meta.json').read_text())
        print(f'resuming {meta["id"]}')
    else:
        if not a.pool:
            raise SystemExit('--pool regular|turbo for a new tournament')
        turbo = a.pool == 'turbo'
        names = sorted(k for k, (_, t) in pool.items() if t == turbo)
        tid = a.id or f'{datetime.date.today().isoformat()}_{a.pool}'
        if (HISTORY / tid).exists():
            raise SystemExit(f'{HISTORY / tid} exists: pass --id {tid} alone to resume it, or another --id')
        rounds = a.rounds or math.ceil(math.log2(len(names)))
        if a.cut & (a.cut - 1) or a.cut > len(names):
            raise SystemExit('--cut must be a power of two no larger than the pool')
        print(f'hashing ROMs for the record...', flush=True)
        meta = {'id': tid, 'created': datetime.datetime.now().isoformat(timespec='seconds'), 'pool': a.pool,
                'rounds': rounds, 'cut': a.cut, 'swiss_best_of': a.swiss_bo, 'cut_best_of': a.cut_bo,
                'decks': names,
                'rom': {'source': str(battery.SRC_ROM.relative_to(battery.REPO)),
                        'source_sha256': sha256(battery.SRC_ROM), 'battery_sha256': sha256(battery.RIG_ROM)}}
        (HISTORY / tid).mkdir(parents=True)
        (HISTORY / tid / 'meta.json').write_text(json.dumps(meta, indent=1))
    tdir = HISTORY / meta['id']
    log = tdir / 'games.jsonl'
    games = {}
    if log.exists():
        for line in log.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:  # torn/NUL-padded line from a killed run: that game just replays
                continue
            games[r['key']] = r
    if sha256(battery.RIG_ROM) != meta['rom']['battery_sha256']:
        raise SystemExit('build/cpu_battery/battery.nds changed since this tournament started; rebuild the '
                         'original or start a new tournament')
    print(f'{meta["id"]}: {len(meta["decks"])} {meta["pool"]} decks, {meta["rounds"]} Swiss rounds, '
          f'top {meta["cut"]}, best of {best_of(meta, "s")} (Swiss) / {best_of(meta, "b")} (top cut); '
          f'{len(games)} games already recorded', flush=True)
    t0, n = time.time(), [0]
    while True:
        need, state = simulate(meta, games)
        write_reports(tdir, meta, games, state)
        if not need:
            break
        print(f'{state["stage"]}: {len(need)} games', flush=True)

        def on_result(g, res, k):
            key, x, y, seed = g
            row = {'key': key, 'a': x, 'b': y, 'turbo': meta['pool'] == 'turbo', 'seed': seed, **res}
            games[key] = row
            with log.open('a') as f:
                f.write(json.dumps(row) + '\n')
            n[0] += 1
            w = battery.winner(row) if res['status'] == 'done' else None
            print(f'[w{k}] {key}: {res["status"]}, winner {(x, y)[w] if w is not None else "-"} '
                  f'| {n[0]} games, {n[0] / (time.time() - t0) * 3600:.0f}/h', flush=True)

        play_matches(meta, need, games, on_result, a.jobs, a.timeout, pool)
    s = summary(meta, state)
    (tdir / 'summary.json').write_text(json.dumps(s, indent=1))
    hist = HISTORY / 'history.jsonl'
    if not hist.exists() or not any(json.loads(line)['id'] == meta['id'] for line in hist.read_text().splitlines()):
        with hist.open('a') as f:
            f.write(json.dumps({k: s[k] for k in ('id', 'finished', 'pool', 'decks', 'rounds', 'cut', 'swiss_best_of', 'cut_best_of',
                                                  'rom', 'champion', 'placements')}) + '\n')
    print(f'champion: {state["champion"]}  ({tdir})')
    ratings()


ELO = 400 / math.log(10)  # Elo points per logit: +200 = 76% expected


def collect_games():
    """[(build, pool, side-0 deck, side-1 deck, side-0 score)] from the tournament folders only.
    Score 1 / 0, or 0.5 for an undecided game; hangs and crashes carry no result and are dropped."""
    out = []
    for mp in sorted(HISTORY.glob('*/meta.json')):
        meta = json.loads(mp.read_text())
        path = mp.parent / 'games.jsonl'
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if r['status'] != 'done':
                continue
            w = battery.winner(r)
            out.append((meta['rom']['battery_sha256'], meta['pool'], r['a'], r['b'], 0.5 if w is None else 1.0 - w))
    return out


def fit(games, prior=0.1):
    """Bradley-Terry with a side-0 term: P(side 0 wins) = sigmoid(s_a - s_b + h), all games at once (no order
    effects, unlike sequential Elo). MAP by Newton with a weak Gaussian prior (precision `prior`) so undefeated
    decks stay finite. Returns ({deck: (s, se)}, h, h_se) in logits."""
    import numpy as np
    decks = sorted({g[0] for g in games} | {g[1] for g in games})
    ix = {d: i for i, d in enumerate(decks)}
    n = len(decks)
    a = np.array([ix[g[0]] for g in games])
    b = np.array([ix[g[1]] for g in games])
    y = np.array([g[2] for g in games])
    X = np.zeros((len(games), n + 1))
    X[np.arange(len(games)), a] += 1
    X[np.arange(len(games)), b] -= 1
    X[:, n] = 1
    th = np.zeros(n + 1)
    P = prior * np.eye(n + 1)
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ th))
        g = X.T @ (y - p) - P @ th
        H = X.T @ (X * (p * (1 - p))[:, None]) + P
        step = np.linalg.solve(H, g)
        th += step
        if np.abs(step).max() < 1e-9:
            break
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return {d: (th[i], se[i]) for d, i in ix.items()}, th[n], se[n]


def ratings(_=None):
    """data/cpu_tournaments/ratings/<build>_<pool>.md/.csv: one table per ROM build and pool."""
    import csv
    games = collect_games()
    groups = {}
    for build, pool, x, y, s in games:
        groups.setdefault((build, pool), []).append((x, y, s))
    out_dir = HISTORY / 'ratings'
    out_dir.mkdir(parents=True, exist_ok=True)
    for (build, pool), gs in sorted(groups.items()):
        strength, h, h_se = fit(gs)
        mean = sum(s for s, _ in strength.values()) / len(strength)
        rec = {d: [0, 0, 0] for d in strength}
        for x, y, s in gs:
            for d, v in ((x, s), (y, 1 - s)):
                rec[d][0 if v == 1 else 1 if v == 0 else 2] += 1
        rows = sorted(((d, 1500 + ELO * (s - mean), 1.96 * ELO * se) for d, (s, se) in strength.items()),
                      key=lambda r: -r[1])
        stem = out_dir / f'{build[:12]}_{pool}'
        with stem.with_suffix('.csv').open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['rank', 'deck', 'rating', 'pm95', 'games', 'wins', 'losses', 'draws', 'win_pct'])
            for i, (d, r, pm) in enumerate(rows, 1):
                wn, ls, dr = rec[d]
                w.writerow([i, d, round(r), round(pm), wn + ls + dr, wn, ls, dr, round(100 * (wn + dr / 2) / (wn + ls + dr), 1)])
        side0 = 100 / (1 + math.exp(-h))
        lines = [f'# Ratings: {pool}, build {build[:12]}', '',
                 f'{len(gs)} games, {len(rows)} decks, from every tournament game on this build. '
                 f'Bradley-Terry fit on an Elo scale (1500 = average; +200 = 76% expected). '
                 f'Side 0 (first player) advantage: {ELO * h:+.0f} ± {1.96 * ELO * h_se:.0f} '
                 f'({side0:.1f}% between equal decks). ± is a 95% range: overlapping ranges are not a real gap.', '',
                 '| # | deck | rating | ±95 | games | W-L-D | win % |', '|---|---|---|---|---|---|---|']
        for i, (d, r, pm) in enumerate(rows, 1):
            wn, ls, dr = rec[d]
            lines.append(f'| {i} | {d} | {r:.0f} | {pm:.0f} | {wn + ls + dr} | {wn}-{ls}-{dr} | '
                         f'{100 * (wn + dr / 2) / (wn + ls + dr):.1f} |')
        stem.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'{stem.with_suffix(".md")}: {len(gs)} games, {len(rows)} decks, side-0 {ELO * h:+.0f}')


def selftest(_=None):
    """Whole tournaments on fake games: the stronger deck (higher index) wins 70% of games, some games hang."""
    for n_decks, cut in ((221, 32), (84, 32), (9, 4)):
        decks = [f'd{i:03d}' for i in range(n_decks)]
        meta = {'id': f'self{n_decks}', 'decks': decks, 'rounds': math.ceil(math.log2(n_decks)), 'cut': cut,
                'swiss_best_of': SWISS_BO, 'cut_best_of': CUT_BO}
        games, waves = {}, 0
        while True:
            need, state = simulate(meta, games)
            if not need:
                break
            waves += 1
            assert waves < 100, 'tournament does not terminate'
            for key, x, y, seed in need:
                assert key not in games
                if seed % 50 == 0:
                    games[key] = {'status': 'hang', 'a': x, 'b': y}
                    continue
                strong = 0 if x > y else 1
                w = strong if seed % 10 < 7 else 1 - strong
                games[key] = {'status': 'done', 'a': x, 'b': y, 'lp': [0, 8000][::-1] if w == 0 else [0, 8000],
                              'deck_left': [10, 10]}
        st = state['standings']
        for ms, bye in state['rounds']:
            seen = [d for m in ms for d in (m.x, m.y)] + ([bye] if bye else [])
            assert sorted(seen) == sorted(decks), 'a round did not pair every deck exactly once'
            assert all(m.decided for m in ms)
        assert all(st.mp[d] == meta['rounds'] for d in decks), 'some deck missed a round'
        rematches = sum(len(o) - len(set(o)) for o in st.opp.values()) // 2
        sizes = [len(ms) for ms in state['bracket']]
        assert sizes == [cut // 2 ** (i + 1) for i in range(int(math.log2(cut)))], sizes
        assert state['champion'] in state['final'][:cut]
        for m in [m for ms, _ in state['rounds'] for m in ms] + [m for ms in state['bracket'] for m in ms]:
            assert m.win <= len(m.played) <= m.best_of or any(w is None for _, w in m.played), (m.stage, m.played)
        assert {m.best_of for ms, _ in state['rounds'] for m in ms} == {3}, 'Swiss must be best of 3'
        assert {m.best_of for ms in state['bracket'] for m in ms} == {5}, 'the top cut must be best of 5'
        top = int(state['champion'][1:])
        print(f'{n_decks} decks, top {cut}: {len(games)} games in {waves} waves, {rematches} forced rematches, '
              f'champion {state["champion"]} (strength rank {n_decks - top}), Swiss #1 {state["final"][0]}')
    assert bracket_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]

    class FakeWorker:
        """Answers at once; every 50th seed hangs, ending its batch as a real worker does."""
        def __init__(self, k):
            pass

        def batch(self, pairs, timeout, emit):
            for i, (seed, _, _, _) in enumerate(pairs):
                if seed % 50 == 0:
                    emit(i, {'status': 'hang'})
                    return i + 1
                emit(i, {'status': 'done', 'lp': [8000, 0] if seed % 3 else [0, 8000], 'deck_left': [9, 9]})
            return len(pairs)

    decks = [f'd{i:02d}' for i in range(13)]
    meta = {'id': 'sched', 'decks': decks, 'rounds': 4, 'cut': 4, 'pool': 'regular'}
    games, stages = {}, 0

    def record(g, res, k):
        assert g[0] not in games, f'{g[0]} played twice'
        games[g[0]] = {'a': g[1], 'b': g[2], **res}

    while True:
        need, state = simulate(meta, games)
        if not need:
            break
        stages += 1
        assert stages < 50, 'scheduler does not converge'
        play_matches(meta, need, games, record, 3, 0, {d: (b'', False) for d in decks}, FakeWorker)
        assert not [g for g in simulate(meta, games)[0] if g[0].split('/')[0] == need[0][0].split('/')[0]], \
            'a stage still needs games after play_matches returned'
    assert 'champion' in state
    print(f'scheduler: {len(games)} games, {stages} stages (1 per Swiss round / bracket round), '
          f'champion {state["champion"]}')
    import random
    rnd = random.Random(7)
    true = {f'd{i:02d}': rnd.gauss(0, 1) for i in range(40)}
    names = sorted(true)
    games = []
    for _ in range(4000):
        x, y = rnd.sample(names, 2)
        games.append((x, y, float(rnd.random() < 1 / (1 + math.exp(-(true[x] - true[y] + 0.3))))))
    est, h, _ = fit(games)
    rank = lambda m: {d: i for i, d in enumerate(sorted(m, key=m.get))}
    rt, re = rank(true), rank({d: s for d, (s, _) in est.items()})
    rho = 1 - 6 * sum((rt[d] - re[d]) ** 2 for d in names) / (len(names) * (len(names) ** 2 - 1))
    assert rho > 0.9 and abs(h - 0.3) < 0.15, (rho, h)
    print(f'ratings: rank correlation {rho:.3f} with true strengths, side-0 term {h:.2f} (true 0.30)')
    print('selftest ok')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('run')
    p.add_argument('--pool', choices=('regular', 'turbo'))
    p.add_argument('--rounds', type=int, help='Swiss rounds (default: ceil(log2(decks)))')
    p.add_argument('--cut', type=int, default=32, help='single-elimination top cut (power of two)')
    p.add_argument('--swiss-bo', type=int, default=SWISS_BO, help='games per Swiss match (best of N, odd)')
    p.add_argument('--cut-bo', type=int, default=CUT_BO, help='games per top-cut match (best of N, odd)')
    p.add_argument('--id', help='tournament id (default: <date>_<pool>); an existing id resumes')
    p.add_argument('--decks', help='comma-separated fnmatch patterns: a smaller pool, for tests')
    p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--timeout', type=float, default=900)
    p.set_defaults(fn=run)
    sub.add_parser('ratings').set_defaults(fn=ratings)
    sub.add_parser('selftest').set_defaults(fn=selftest)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
