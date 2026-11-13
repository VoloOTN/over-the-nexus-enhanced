"""Scrape curated card categories from the Yu-Gi-Oh! Fandom wiki.

Each card page carries a ``cardtable-categories`` block of hand-curated semantic
labels — "Activates upon attack declaration", "Negates attacks", "1 non-Tuner
Synchro Material", "Supports DARK" — which is exactly the vocabulary this model
has been reverse-engineering out of card text with regexes all session.

Access notes, both found the hard way:

* the rendered page is **403** to any scraper, browser User-Agent or not;
* ``api.php?action=query&prop=categories`` returns MediaWiki *maintenance*
  categories ("Card pages with an unofficial Thai name"), not these;
* ``api.php?action=parse&prop=text`` returns the rendered HTML and is **not**
  blocked, but renders one page per request (~2 s each).
* ``api.php?action=query&prop=revisions`` returns the page SOURCE, 50 pages per
  request, and the categories are plain ``{{CardTable2}}`` parameters there
  (``GROUPS``).  That is the route used here; ``--compare`` re-checks it against
  everything cached.

Polite by construction: one request at a time (50 pages per request), a delay between them, and every
result cached to disk so a re-run costs nothing and an interrupted run resumes.

    uv run python -m otn_enhanced.deckgen.wiki_categories [--limit N]
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from otn_enhanced.deckgen import resources as _res

#: Via resources so the path follows a PyInstaller bundle when frozen.
CACHE = _res.wiki_categories()
API = "https://yugioh.fandom.com/api.php"
UA = {"User-Agent": "deckgen-tagger/0.1 (Over the Nexus ROM research; polite, cached)"}
DELAY = 0.35  # seconds between requests

_STRIP = re.compile(r"<[^>]+>")
#: Split the block at each <dt>, then take EVERY <dd> that follows it.
#:
#: A group with several values renders them as sibling <dd> elements, so a
#: `<dt>…</dt>\s*<dd>…</dd>` pattern silently keeps only the first.  It cost
#: Catastor "Destroys battling monster at the start of the Damage Step" and
#: "Does not require specific Synchro Materials" — the second of which is
#: exactly the generic-material signal `power.w_extra_generic` was built for.
_SECTION = re.compile(r"<dt[^>]*>(.*?)</dt>(.*?)(?=<dt[^>]*>|\Z)", re.S)
_DD = re.compile(r"<dd[^>]*>(.*?)</dd>", re.S)


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", _STRIP.sub("", s)).replace("&amp;", "&").strip()


#: {{CardTable2}} parameter (trailing digits dropped: action1, action2, ...) -> the group label the rendered
#: `cardtable-categories` block shows.  Derived from, and checked against, 1426 pages fetched the old way
#: (action=parse): with comment stripping and the "(series)" / "(archetype)" display trim, every one matched.
GROUPS = {"action": "Actions", "anti-supports": "Anti-supports", "anti-supports_archetypes": "Anti-supports archetypes",
          "archseries": "Archetypes and series", "attack": "Attack categories", "banished": "Banished categories",
          "counter": "Counters", "fm_for": "Fusion Material for", "life_points": "LP", "mentions": "Mentions",
          "misc": "Miscellaneous", "m/s/t": "Monster/Spell/Trap categories",
          "related_to_archseries": "Related to archetypes and series", "stat_change": "Stat changes",
          "summoning": "Summoning categories", "supports": "Supports", "supports_archetypes": "Supports archetypes",
          "sm_for": "Synchro Material for"}
BATCH = 50  # titles per request: the MediaWiki API maximum for anonymous clients


def _cardtable_params(wikitext: str) -> dict[str, str] | None:
    """Top-level `| key = value` pairs of the page's {{CardTable2}}, or None if it has none."""
    w = re.sub(r"<!--.*?-->", "", wikitext, flags=re.S)    # comments can wrap whole `| key = ...` lines
    m = re.search(r"\{\{\s*CardTable2", w)
    if not m:
        return None
    i, depth, key, buf, out = m.end(), 1, None, "", {}
    while i < len(w):
        two = w[i:i + 2]
        if two in ("{{", "[["):
            depth += 1; buf += two; i += 2; continue
        if two in ("}}", "]]"):
            depth -= 1
            if depth == 0:
                break
            buf += two; i += 2; continue
        if w[i] == "|" and depth == 1:
            if key:
                out[key] = buf
            eq, nl = w.find("=", i), w.find("\n", i)
            key = w[i + 1:eq].strip() if eq != -1 and (nl == -1 or eq < nl) else None
            buf = ""
            i = eq + 1 if key else i + 1
            continue
        buf += w[i]; i += 1
    if key:
        out[key] = buf
    return out


def _categories(params: dict[str, str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for k, raw in params.items():
        group = GROUPS.get(re.sub(r"\d+$", "", k))
        if not group:
            continue
        for line in raw.split("\n"):
            v = re.sub(r"^\s*\*\s*", "", line).strip()
            v = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", v)   # [[link|text]] -> text
            v = re.sub(r"\s*\([^)]*\)$", "", v).strip()              # "Summoned Skull (series)" displays as "Summoned Skull"
            if v and v not in out.setdefault(group, []):
                out[group].append(v)
    return {g: vs for g, vs in out.items() if vs}


def fetch_many(titles: list[str]) -> dict[str, dict[str, list[str]] | None]:
    """{title: category groups, or None if there is no card page} -- BATCH titles per request.

    Reads each page's wikitext (action=query&prop=revisions) instead of rendering it (action=parse): the
    categories are plain {{CardTable2}} parameters, and the query API takes 50 titles at once where parse
    takes one, so a full run is ~80 requests instead of ~4000."""
    out: dict[str, dict[str, list[str]] | None] = {}
    for n in range(0, len(titles), BATCH):
        chunk = titles[n:n + BATCH]
        q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "revisions", "rvprop": "content",
                                    "rvslots": "main", "redirects": "1", "titles": "|".join(chunk)})
        data = json.loads(urllib.request.urlopen(urllib.request.Request(f"{API}?{q}", headers=UA), timeout=60)
                          .read().decode("utf-8", "replace"))["query"]
        fwd = {r["from"]: r["to"] for k in ("normalized", "redirects") for r in data.get(k, [])}
        pages = {p["title"]: p for p in data.get("pages", {}).values()}
        for t in chunk:
            t2 = t
            for _ in range(4):                       # normalized -> redirect -> ...
                t2 = fwd.get(t2, t2)
            page = pages.get(t2)
            params = (_cardtable_params(page["revisions"][0]["slots"]["main"]["*"])
                      if page and "revisions" in page else None)
            out[t] = None if params is None else _categories(params)
        if n + BATCH < len(titles):
            time.sleep(DELAY)
    return out


def fetch(title: str) -> dict[str, list[str]] | None:
    """Category groups for one page, or None if there is no card page there."""
    return fetch_many([title])[title]


def fetch_rendered(title: str) -> dict[str, list[str]] | None:
    """The OLD route: render the page (action=parse) and scrape the categories block.  ~2 s a page; kept as the
    oracle `--compare` checks fetch_many against."""
    url = (f"{API}?action=parse&format=json&prop=text&redirects=1&page="
           + urllib.parse.quote(title))
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=30
        ).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    data = json.loads(raw)
    if "error" in data:
        return None
    html = data.get("parse", {}).get("text", {}).get("*", "")
    if "cardtable" not in html:
        # No card infobox at all: wrong page, or a disambiguation stub.
        return None
    m = re.search(r'cardtable-categories(.{0,6000})', html, re.S)
    if not m:
        # The page IS the card and simply has no categories to list.  That is the
        # normal state of a Normal Monster -- a vanilla has no effect to
        # categorise -- and treating the empty dict as "not found" sent 44 of the
        # first 100 misses down the retry path for nothing.
        return {}
    out: dict[str, list[str]] = {}
    for group, body in _SECTION.findall(m.group(1)):
        g = _text(group)
        vals: list[str] = []
        for dd in _DD.findall(body):
            # A single <dd> may still hold a <ul> or <br>-separated list.
            for part in re.split(r"<br\s*/?>|</li>\s*<li>", dd):
                v = _text(part)
                if v and v not in vals:
                    vals.append(v)
        if g and vals:
            out[g] = vals
    return out


def _norm(s: str) -> str:
    """Fold a card name to letters+digits, lowercased."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _lost(name: str) -> str:
    """The ROM's unencodable character (Skiel/Wisel "Infinity", Fiendish Engine "Omega") can reach us as U+FFFD
    OR as a raw C1 control byte (0x80-0x9F), depending on how the pool decoded it.  Fold both to U+FFFD: a C1
    byte otherwise normalises away, and 'Meklord Emperor Skiel <0x90>' matched the BASE card's page."""
    return re.sub(r"[-]", "�", name)


def same_card(rom: str, title: str) -> bool:
    """Is `title` the same card as the ROM's `rom`, allowing for how ROM spells it?

    A bare "search and take hit #1" is not safe: it answered
    ``Rock Ogre Grotto #1`` with ``Rock Ogre Grotto 1 (DDM)`` -- a *Dungeon Dice
    Monsters* page, a different game entirely.  Silently tagging a card from the
    wrong game is the same failure as the Cyber Dragon -> Proto-Cyber Dragon
    mis-resolve, so a repair is only accepted when the two names agree modulo
    punctuation and case.  That still admits every real repair seen:
    "Ice barrier"/"Ice Barrier" and "Kamakiri #1"/"Kamakiri 1"; it rejects the
    "(DDM)" suffix, because a disambiguator means it is *not* the same page.
    """
    rom = _lost(rom)
    par = re.search(r"\(([^)]*)\)\s*$", title)
    if par and par.group(1).strip().lower() not in _CARD_PAREN:
        # A parenthetical is a disambiguator -- "(DDM)", "(DM4)", "(anime)" -- so
        # the page is a different game or medium, never the base card.  Checked
        # BEFORE the wildcard branch below: normalising drops the brackets, and
        # the greedy wildcard then happily matched 'Fiendish Engine Omega (DDM)'
        # against 'Fiendish Engine <U+FFFD>'.
        return False
    if par:
        # Compare against the bare title: "(card)" survives _norm as letters and
        # would never equal the ROM name.
        title = title[:par.start()]
    if ALIASES.get(rom) == title:
        return True
    if "�" not in rom:
        return _norm(rom) == _norm(title)
    # Five ROM names carry an unencodable byte -- 'Fiendish Engine �' (Omega),
    # 'Meklord Emperor Wisel �' (Infinity), 'C� Chulainn'.  The lost character is
    # unrecoverable from the ROM, so let it stand for a run of characters and
    # require everything else to line up.
    #
    # Compare on a symbol-PRESERVING fold.  `_norm` drops anything outside
    # [a-z0-9], which deleted the very "∞" this needs to match -- and worse, it
    # made 'Meklord Emperor Wisel �' compare EQUAL to the base card 'Meklord
    # Emperor Wisel', a different card that would have been tagged silently.
    # Requiring one-or-more characters keeps the base card rejected.
    # EXACTLY one character: U+FFFD is one replacement char standing for one
    # un-decodable char.  `.+` let 'Meklord Emperor Wisel �' match 'Meklord
    # Emperor Wisel - Synchro Absorption' -- a different card, again silently.
    pat = "".join(r"." if ch == "�" else re.escape(ch) for ch in _norm_sym(rom))
    return re.fullmatch(pat, _norm_sym(title), re.S) is not None


#: Parentheticals that still mean "this card".  Everything else -- (anime),
#: (DDM), (manga), (DM1), (WC10), (character), (Japanese) -- is a different
#: game, medium or entity.  The bare title is often the SET or ARCHETYPE page,
#: which is why "Light of Destruction (card)" must be reachable at all.
_CARD_PAREN = frozenset({"card", "spell card", "trap card", "monster card"})

#: ROM name -> wiki title, for **mistranslations** rather than typos.  No
#: mechanical rule can find these: the ROM's localisation simply chose a
#: different English name, so the strings have no edit-distance relationship and
#: search returns nothing useful.  User-supplied, and the only acceptable source
#: -- do not guess an alias from a plausible-looking search hit.
ALIASES = {
    "Crystal Counter": "Counter Gem",        # user, 2026-07-30
    "Synchronized Realm": "Synch Realm",     # user, 2026-07-30 (ROM spells it -ized)
}


def _norm_sym(s: str) -> str:
    """Fold, but keep symbols: strips only spacing and the punctuation the ROM
    varies, so "∞" / "Ω" / "ú" survive to be matched against U+FFFD."""
    return re.sub(r"[\s,.'\-・･_#]", "", s.lower())


def search_title(name: str) -> str | None:
    """Ask the wiki to find the page for a name the ROM spells wrong.

    The ROM writes "Trishula, Dragon of the Ice **b**arrier" -- MediaWiki titles
    are case-sensitive past the first letter, so the exact lookup 404s.  Rather
    than curate a typo list (the user knows of no others, but absence of evidence
    is not evidence of absence), let the wiki's search resolve it and record what
    it chose so the mapping is auditable.
    """
    url = (f"{API}?action=query&format=json&list=search&srlimit=8&srsearch="
           + urllib.parse.quote(name))
    try:
        hits = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=30
        ).read().decode("utf-8", "replace"))["query"]["search"]
    except Exception:  # noqa: BLE001
        return None
    for h in hits:
        if same_card(name, h["title"]):
            return h["title"]
    return None


def candidates(name: str) -> list[str]:
    """Page titles to try, best first.

    "If you cannot find the equivalent Speed Spell, just use the original card":
    Turbo Duel cards are printed as ``Speed Spell - X`` and often have no page of
    their own, so the base card is the fallback.
    """
    name = _lost(name)
    # A known mistranslation has exactly one right answer: try it first and do
    # not dilute it with guesses.
    if name in ALIASES:
        return [ALIASES[name]]
    out = [name]
    # The ROM writes "#N"; wiki titles drop the "#".  Search alone did not save
    # 'Rock Ogre Grotto #1' -- its top hits were all other-game pages.
    if "#" in name:
        out.append(name.replace("#", ""))
    # Halfwidth katakana stand in for the interpunct: 'Summon Reactor ｷSK'.
    if re.search(r"[｡-ﾟ]", name):
        out.append(re.sub(r"[｡-ﾟ]+", "・", name))
        out.append(re.sub(r"[｡-ﾟ]+", "", name))
    # The character the ROM could not encode.  Search does not surface these
    # pages -- for Granel/Skiel it offered the base card and the anime one -- so
    # ask for them by name.
    if "�" in name:
        out.extend(name.replace("�", ch) for ch in "∞Ωαβ")
    # A bare name that is also a set/archetype resolves to the wrong page type.
    out.append(f"{name} (card)")
    if name.startswith("Speed Spell - "):
        out.append(name[len("Speed Spell - "):])
    # The ROM writes "Elemental Hero"; the wiki uses "Elemental HERO".  Redirects
    # cover most casing, but not all.
    for a, b in (("Elemental Hero", "Elemental HERO"),
                 ("Evil Hero", "Evil HERO"),
                 ("Destiny Hero", "Destiny HERO"),
                 ("Masked Hero", "Masked HERO"),
                 ("Vision Hero", "Vision HERO")):
        if a in name:
            out.append(name.replace(a, b))
    return out


#: Every name-resolution case learned the hard way.  ``(rom_name, wiki_title,
#: is_same_card)``.  Run with ``--selftest``; these are pure-function checks and
#: need no network.
RESOLVE_CASES = (
    # The ROM typo the user reported: lowercase "barrier".
    ("Trishula, Dragon of the Ice barrier", "Trishula, Dragon of the Ice Barrier", True),
    # Systematic: the ROM writes "#N", the wiki writes "N".
    ("Flying Kamakiri #1", "Flying Kamakiri 1", True),
    ("Mystical Sheep #1", "Mystical Sheep 1", True),
    ("Steel Ogre Grotto #2", "Steel Ogre Grotto 2", True),
    # Wrong GAME.  Search hit #1 for "Rock Ogre Grotto #1" is a Dungeon Dice
    # Monsters page; accepting it tags a card that is not this card.
    ("Rock Ogre Grotto #1", "Rock Ogre Grotto 1 (DDM)", False),
    ("Rock Ogre Grotto #1", "Rock Ogre Grotto 1", True),
    # Wrong CARD, the classic: a substring match is not an identity match.
    ("Cyber Dragon", "Proto-Cyber Dragon", False),
    ("Dupe Frog", "Frog the Jam", False),
    # "(card)" IS the card page -- the bare title is the SET or ARCHETYPE.
    ("Light of Destruction", "Light of Destruction (card)", True),
    ("Ancient Gear", "Ancient Gear (card)", True),
    ("Ancient Gear", "Ancient Gear (anime)", False),
    # U+FFFD stands for a lost character and must match a REAL one, never
    # nothing: the base card is a different card from the "Infinity" version.
    ("Meklord Emperor Wisel �", "Meklord Emperor Wisel ∞", True),
    # U+FFFD stands for exactly ONE character, so the English spelling-out is a
    # non-match; the wiki title uses the real symbol.
    ("Meklord Emperor Wisel �", "Meklord Emperor Wisel Infinity", False),
    ("Meklord Emperor Wisel �", "Meklord Emperor Wisel - Synchro Absorption", False),
    ("Meklord Emperor Wisel �", "Meklord Emperor Wisel", False),
    # ...and the same lost character arriving as a raw C1 byte instead of U+FFFD.
    ("Meklord Emperor Skiel ", "Meklord Emperor Skiel", False),
    ("Meklord Emperor Skiel ", "Meklord Emperor Skiel ∞", True),
    ("Meklord Emperor Wisel �", "Meklord Emperor Wisel (anime)", False),
    ("Fiendish Engine �", "Fiendish Engine Ω", True),
    ("C� Chulainn the Awakened", "Cú Chulainn the Awakened", True),
    # The wildcard must NOT reach through a disambiguator.
    ("Fiendish Engine �", "Fiendish Engine Omega (DDM)", False),
    # Mistranslations: no mechanical rule finds these, only the user.
    ("Crystal Counter", "Counter Gem", True),
    ("Synchronized Realm", "Synch Realm", True),
    ("Crystal Counter", "Crystal Tree", False),
)


def selftest() -> int:
    bad = 0
    for rom, title, want in RESOLVE_CASES:
        got = same_card(rom, title)
        if got != want:
            bad += 1
            print(f"  FAIL {ascii(rom)} vs {ascii(title)}: got {got}, want {want}")
    print(f"wiki name resolution: {len(RESOLVE_CASES) - bad}/{len(RESOLVE_CASES)} pass")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    from otn_enhanced.deckgen import cardpool

    # Five pool names contain U+FFFD; printing one to this console's cp1252
    # stdout raised UnicodeEncodeError and killed the run at 1550/3264.
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
    argv = argv or sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None

    store = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    cards = [c for c in cardpool.load_pool() if c.playable and c.name]
    # Most-played first, so an interrupted run still covers what matters.
    try:
        from otn_enhanced.deckgen import mining, training
        pr = training.PlayRate.build(mining.era_decks(cards))
        cards.sort(key=lambda c: -pr.presence.get(c.cid, 0))
    except Exception:
        pass
    # Retry anything that previously failed: a resolver fix must reach the rows
    # it was written for.
    todo = [c for c in cards
            if str(c.cid) not in store or not store[str(c.cid)].get("found")]
    # `page` records WHICH title answered, and 806 rows -- the most-played cards,
    # fetched first -- were written before that field existed.  A row with no
    # `page` cannot be audited for a wrong-card capture (the Rock Ogre Grotto
    # (DDM) failure), so `--repage` re-fetches exactly those through the current,
    # guarded resolver.
    if "--repage" in argv:
        todo = [c for c in cards
                if str(c.cid) in store and "page" not in store[str(c.cid)]]
    if limit:
        todo = todo[:limit]
    if "--compare" in argv:
        # The check this module's batched route must keep passing: re-read every cached card's page and require
        # the same categories the cache holds (most of it written by the old render-and-scrape route).
        rows = [r for r in store.values() if r.get("found") and r.get("page")]
        got = fetch_many(sorted({r["page"] for r in rows}))
        bad = [r for r in rows if got[r["page"]] != r["categories"]]
        for r in bad[:20]:
            print(f"  DIFF {r['name']!r} ({r['page']}): cached {r['categories']} vs now {got[r['page']]}")
        print(f"compare: {len(rows) - len(bad)}/{len(rows)} cached cards identical")
        return 1 if bad else 0
    print(f"{len(store)} cached, {len(todo)} to fetch", flush=True)

    def save() -> None:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(store, indent=0, ensure_ascii=False), encoding="utf-8")

    # Fast path: every card's first-choice title, BATCH to a request.  Only the misses go down the
    # one-at-a-time route below (aliases, "#N", "(card)", Speed Spell, search).
    hit = miss = 0
    pending = []
    for n in range(0, len(todo), BATCH):
        chunk = todo[n:n + BATCH]
        titles = [candidates(c.name)[0] for c in chunk]
        got = fetch_many(titles)
        for c, t in zip(chunk, titles):
            if got[t] is None:
                pending.append(c)
            else:
                store[str(c.cid)] = {"name": c.name, "categories": got[t], "found": True, "page": t}
                hit += 1
        save()
        print(f"  batch {n + len(chunk)}/{len(todo)}  found {hit}  to retry {len(pending)}", flush=True)
        time.sleep(DELAY)
    todo = pending

    for i, c in enumerate(todo, 1):
        got, via = None, None
        tries = list(candidates(c.name))
        for title in tries:
            try:
                got = fetch(title)
            except Exception as exc:  # noqa: BLE001 — never lose the cache to one page
                print(f"  !! {c.name}: {type(exc).__name__} {exc}", flush=True)
                got = None
            if got is not None:
                via = title
                break
            time.sleep(DELAY)
        if got is None:
            found = search_title(c.name)
            if found and found not in tries:
                time.sleep(DELAY)
                try:
                    got = fetch(found)
                except Exception:  # noqa: BLE001
                    got = None
                if got is not None:
                    via = found
                    print(f"  ~~ {c.name!r} -> {found!r} (via search)", flush=True)
        store[str(c.cid)] = {"name": c.name, "categories": got or {},
                             "found": got is not None, "page": via}
        hit, miss = (hit + 1, miss) if got is not None else (hit, miss + 1)
        time.sleep(DELAY)
        if i % 25 == 0 or i == len(todo):
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(store, indent=0, ensure_ascii=False),
                             encoding="utf-8")
            print(f"  {i}/{len(todo)}  found {hit}  missing {miss}", flush=True)
    CACHE.write_text(json.dumps(store, indent=0, ensure_ascii=False), encoding="utf-8")
    print(f"done: {len(store)} cards cached -> {CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
