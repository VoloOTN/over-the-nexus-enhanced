"""One deck against the field: DECK plays every other deck of its pool (regular or turbo) on the battery ROM,
up to --duels duels, then reports how it ranks against the rest.

Duels go out in rounds: each round meets every opponent once, in a shuffled order, with the first player
alternating, so a cap short of a full round is still a spread sample. Round r puts DECK first against the
i-th opponent (alphabetical) when i + r is even, so two rounds give every opponent one duel each seat. A rerun with the same --id resumes; a larger --duels extends it.

Percentile: a Bradley-Terry fit (tournament.fit) over this gauntlet plus every tournament game played on the
same battery ROM and pool, so opponents' strength comes from the tournaments; percentile = share of the pool
rated below DECK. With no tournament on this build yet, only the win % against the field is reported (in a
full round robin the average deck scores 50%).

Output in data/cpu_gauntlets/<id>/: meta.json, games.jsonl, report.md, summary.json, card_stats.csv (DECK's
cards only: drawn / summoned / activated over its duels).

    run DECK [--duels N] [--id ID] [--jobs 6]
"""
import argparse
import datetime
import difflib
import json
import random
import time

from otn_enhanced.tools.cpu_battery import battery, tournament as T

HOME = battery.REPO / 'data' / 'cpu_gauntlets'


def schedule(deck, opps, n):
    """[(key, deck_first, opponent, round)]: the first n duels, round by round."""
    out, r = [], 0
    ix = {o: i for i, o in enumerate(sorted(opps))}
    while len(out) < n:
        order = sorted(opps)
        random.Random(T.h32('gauntlet', deck, r)).shuffle(order)
        out += [(f'{r}/{o}', (ix[o] + r) % 2 == 0, o, r) for o in order]
        r += 1
    return out[:n]


def score(rows, deck):
    """Deck's (wins, losses, draws) in finished duels; hangs/crashes are not results."""
    w = l = d = 0
    for r in rows:
        if r['status'] != 'done':
            continue
        x = battery.winner(r)
        if x is None:
            d += 1
        elif (r['a'], r['b'])[x] == deck:
            w += 1
        else:
            l += 1
    return w, l, d


def percentile(meta, rows):
    """(percentile, rating, ±95, reference games, decks rated) or None without tournament games on this build."""
    ref = [(x, y, s) for b, p, x, y, s in T.collect_games()
           if b == meta['rom']['battery_sha256'] and p == meta['pool']]
    if not ref:
        return None
    mine = [(r['a'], r['b'], 0.5 if battery.winner(r) is None else 1.0 - battery.winner(r))
            for r in rows if r['status'] == 'done']
    strength, _, _ = T.fit(ref + mine)
    deck = meta['deck']
    s, se = strength[deck]
    mean = sum(v for v, _ in strength.values()) / len(strength)
    below = sum(v < s for d, (v, _) in strength.items() if d != deck)
    return 100 * below / (len(strength) - 1), 1500 + T.ELO * (s - mean), 1.96 * T.ELO * se, len(ref), len(strength)


def report(gdir, meta, rows):
    deck = meta['deck']
    w, l, d = score(rows, deck)
    n = w + l + d
    first = [r for r in rows if r['a'] == deck]
    second = [r for r in rows if r['b'] == deck]
    turns = [battery.turns_of(r) for r in rows if r['status'] == 'done']
    bad = [r for r in rows if r['status'] != 'done']
    pct = percentile(meta, rows) if n else None
    s = {'id': meta['id'], 'deck': deck, 'pool': meta['pool'], 'duels': len(rows), 'wins': w, 'losses': l,
         'draws': d, 'win_pct': round(100 * (w + d / 2) / n, 1) if n else None,
         'hang_or_crash': len(bad), 'rom': meta['rom']}
    lines = [f'# Gauntlet: {deck} ({meta["pool"]})', '',
             f'{len(rows)} duels against {len(meta["opponents"])} opponents: **{w}-{l}-{d}** (W-L-D)'
             + (f', **{s["win_pct"]}%** against the field (an average deck scores 50%)' if n else '')
             + (f', {len(bad)} hang/crash' if bad else '') + '.', '']
    if pct:
        p, rating, pm, nref, ndecks = pct
        s.update(percentile=round(p, 1), rating=round(rating), rating_pm95=round(pm), reference_games=nref)
        lines += [f'**Percentile: {p:.0f}** — better than {p:.0f}% of the {ndecks - 1} other rated decks '
                  f'(rating {rating:.0f} ± {pm:.0f}; Bradley-Terry over this gauntlet and {nref} tournament '
                  f'games on the same ROM build).', '']
    else:
        lines += ['No percentile: no tournament has been played on this battery ROM and pool yet, so the '
                  'opponents\' strength is unknown. Win % against the field is the measure.', '']
    for label, rs in (('going first', first), ('going second', second)):
        a, b, c = score(rs, deck)
        if a + b + c:
            lines.append(f'- {label}: {a}-{b}-{c} ({100 * (a + c / 2) / (a + b + c):.1f}%)')
    if turns:
        lines.append(f'- average turns: {sum(turns) / len(turns):.1f}')
    per = {}
    for r in rows:
        o = r['b'] if r['a'] == deck else r['a']
        per.setdefault(o, []).append(r)
    lines += ['', '## By opponent', '', '| opponent | W-L-D | hang/crash |', '|---|---|---|']
    for o, rs in sorted(per.items(), key=lambda kv: (-score(kv[1], deck)[1], kv[0])):  # worst matchups first
        a, b, c = score(rs, deck)
        lines.append(f'| {o} | {a}-{b}-{c} | {sum(r["status"] != "done" for r in rs)} |')
    (gdir / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (gdir / 'summary.json').write_text(json.dumps(s, indent=1))
    battery.card_stats(rows, gdir / 'card_stats.csv', only=deck)
    (gdir / 'card_stats_by_deck.csv').unlink(missing_ok=True)  # one deck: the same table again
    return s


def run(a):
    pool = battery.decks(None)
    if a.deck not in pool:
        raise SystemExit(f'no deck {a.deck!r}; close: {difflib.get_close_matches(a.deck, pool, 8, 0.4)}')
    turbo = pool[a.deck][1]
    gid = a.id or f'{datetime.date.today().isoformat()}_{a.deck}'
    gdir = HOME / gid
    sha = T.sha256(battery.RIG_ROM)
    if (gdir / 'meta.json').exists():
        meta = json.loads((gdir / 'meta.json').read_text())
        if meta['deck'] != a.deck or meta['rom']['battery_sha256'] != sha:
            raise SystemExit(f'{gdir} is for {meta["deck"]} on another battery ROM; pass another --id')
    else:
        opps = sorted(k for k, (_, t) in pool.items() if t == turbo and k != a.deck)
        meta = {'id': gid, 'created': datetime.datetime.now().isoformat(timespec='seconds'), 'deck': a.deck,
                'pool': 'turbo' if turbo else 'regular', 'opponents': opps,
                'rom': {'source': str(battery.SRC_ROM.relative_to(battery.REPO)),
                        'source_sha256': T.sha256(battery.SRC_ROM), 'battery_sha256': sha}}
        gdir.mkdir(parents=True)
    meta['duels'] = a.duels or 2 * len(meta['opponents'])
    (gdir / 'meta.json').write_text(json.dumps(meta, indent=1))
    log = gdir / 'games.jsonl'
    rows = {}
    if log.exists():
        for line in log.read_text().splitlines():
            r = json.loads(line)
            rows[r['key']] = r
    plan = schedule(a.deck, meta['opponents'], meta['duels'])
    todo = [g for g in plan if g[0] not in rows]
    print(f'{gid}: {a.deck} ({meta["pool"]}) vs {len(meta["opponents"])} opponents, {meta["duels"]} duels, '
          f'{len(plan) - len(todo)} already played, {len(todo)} to play, {a.jobs} workers', flush=True)
    t0, n = time.time(), [0]
    sides = {}
    for key, first, o, r in todo:
        sides[key] = ((a.deck, o) if first else (o, a.deck)) + (T.h32('gauntlet', a.deck, o, r),)
    games = [(key, seed, turbo, pool[x][0], pool[y][0]) for key, (x, y, seed) in sides.items()]

    def on_result(key, res, k):
        x, y, seed = sides[key]
        row = {'key': key, 'a': x, 'b': y, 'turbo': turbo, 'seed': seed, **res}
        rows[key] = row
        with log.open('a') as f:
            f.write(json.dumps(row) + '\n')
        n[0] += 1
        w, l, d = score(rows.values(), a.deck)
        rate = n[0] / (time.time() - t0) * 3600
        print(f'[w{k}] {x} vs {y}: {res["status"]}, winner '
              f'{(x, y)[battery.winner(row)] if res["status"] == "done" and battery.winner(row) is not None else "-"}'
              f' | {a.deck} {w}-{l}-{d} | {n[0]}/{len(todo)}, {rate:.0f}/h, '
              f'{(len(todo) - n[0]) / max(rate, 1e-9):.1f} h left', flush=True)

    battery.play(games, a.jobs, a.timeout, False, on_result)
    keep = {g[0] for g in plan}
    s = report(gdir, meta, [r for k, r in rows.items() if k in keep])
    print(f'{a.deck}: {s["wins"]}-{s["losses"]}-{s["draws"]}, {s["win_pct"]}% vs the field'
          + (f', percentile {s["percentile"]} (rating {s["rating"]} +/- {s["rating_pm95"]})' if 'percentile' in s
             else ', no percentile (no tournament on this build yet)') + f'\n{gdir / "report.md"}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('run')
    p.add_argument('deck', help='deck name as in deck.pac, without deck/ and .ydc (e.g. wcs049_gaiza)')
    p.add_argument('--duels', type=int, help='duels to play (default: every opponent twice, once each seat)')
    p.add_argument('--id', help='folder under data/cpu_gauntlets (default: <date>_<deck>); an existing id resumes')
    p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--timeout', type=float, default=900, help='seconds before a duel counts as a hang')
    p.set_defaults(fn=run)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
