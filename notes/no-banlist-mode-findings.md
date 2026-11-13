# No-banlist mode (replace "Treat Ltd as Forb") — findings

Status: patch_no_banlist_mode SHIPPED 2026-10-05 (in-game confirmed by user 2026-10-05); step 91/94, EE build sha256 c4ee9232...25d9, sweep 80/0. patch_extra_banlists PARKED (user 2026-10-05: keep in back pocket); its cache+4 fix is AWAITING IN-GAME TEST. patch_highlander_list DROPPED.

## Confirmed (2026-10-05, savestates default_list.mln / limited_is_forbidden.mln + RAM disasm)
- melonDS .mln: main RAM at file offset 0x24.
- Menu entries are built-in list "modes" 0/1/2, all from limit201009.bin. Menu table in RAM
  0x022210EC: {mode, text id, ...} = (0,0x528)(1,0x567)(2,0x568); cursor 0x022210E4.
- Text ids: 0x514 + header+2. 0x567 "Treat Ltd as Forb", 0x568 "Up to 1 Forb Card",
  0x55F "No Forb/Ltd Card List" (unused stock string). game_indx_e/game_text_e in bin2.pac.
- limit*.bin header +2 is the NAME id (0x14 for 2010-09), not a "banned monster count"
  as limit_codec.py documents.
- load_list arm9 Thumb 0x0202AC90; list buffer 0x02121E94. Mode 1: +2=0x53, +6=1 (0x0202AD24..).
  Mode 2: +2=0x54, +6=2.
- get_limit 0x0202AD9C: listed card -> (flags&1 ? 0 : entry>>14); unlisted -> 3.
- flags bit0 is read ONLY there. Other flag readers (0x0201B10A deck check, ov 0x02152DF0,
  0x021531C4) test bit1 only.
- Per-card copy array 0x021FD1F0 (4096 B): default {3:3964,1:67,0:47,2:18}, mode 1 {3:3964,0:132}.

## Patch
- 0x0202ADD0 `00 20`->`03 20` (bit0 -> 3 copies); text 0x567 overwritten in place with "No Banlist" (0x0202AD24 left native).
- Module patch_no_banlist_mode.py. NOT in steps.STEPS (awaiting test + approval).

## Confirmed: list slots (2026-10-05, disasm of RAM in default_list.mln)
- Menu builder ov @0x02168654: loop kind 0 idx 0..2 (`cmp r6,#3` @0x021686BC), then kind 1
  idx 0..84 (`cmp r8,#0x55` @0x02168720); each gated by bitmap test 0x0202ED00.
- Bitmap = u32[] at 0x0212406C+0x23B4 (=0x02126420): word0 = built-ins (0x7 on this save),
  words 1..3 = saved lists (idx/32). All saved-list words 0 here.
- Saved lists (kind 1) load via 0x0202ED98 -> save-file system 0x0202BE4C (cartridge save,
  block-limited: "Insufficient save data blocks" strings). 0x0202ED3C validates all 85 at boot.
- Built-in loader opens ONE fixed path literal "Bin/limit201009.bin" @0x020AB848.
- Unused lists limit200609/200703/200709/200809/200909 are in bin.pac; their header +2 name ids
  give free labels (e.g. 0x12 -> 0x526 "List - September, 2009").

## Extra built-in lists (patch_extra_banlists.py) — PARKED 2026-10-05 (was briefly shipped, then pulled)
- Test ROM rom_extra_banlists_test.nds (on top of rom_no_banlist_test.nds), sha256 f90407e1…156c.
- Confirmed this session: menu builder lives in OVERLAY 8 (0x0214C840, 100% RAM match in
  default_list.mln); no shipped patch touches ov8. Path literal 0x020AB848 has exactly one
  reference (pool 0x0202AD54). Built-in enable bits: new-game init sets kind0 bits 0,1 only
  (0x0202E146/0x0202E150); bit 2 set by unlock code (0x0202EEA6/0x0202EF2E/ov 0x02167D3C).
- File header +2 names: 200609 0xC, 200703 0xD, 200709 0xE, 200809 0x10, 200909 0x12, 201009 0x14.
- Patch: load_list kind-0 block 0x0202ACCE..0x0202AD46 rewritten in place (writes path chars
  11,12 = "10" for idx 0..3, idx+2 for idx 4..7; idx 1/2 stamps preserved); ov8 0x02168678
  cmp r0,#0 -> orrs r0,r0,r6,lsr #2; 0x021686BC cmp r6,#3 -> #8. Mar 2007 not exposed.
- Expected menu: Sep 2010, No Banlist, Up to 1 Forb Card (if unlocked), Sep 2006, Sep 2007,
  Sep 2008, Sep 2009.

## Bug found + fixed (2026-10-05, after shipping)
- Shipped patch_extra_banlists wrote 0x100+idx*16 to CACHE+4 = 0x02122118 (a separate struct, 13 refs,
  holds the current list name text) instead of BUFFER+4 (stock 0x0202AD3C reloads r0 = pool 0x0202AD50 =
  buffer). Proof: stock bytes 0x0202AD3C '0448' -> (0x0202AD40)+0x10 = 0x0202AD50 = 0x02121E94; savestate buf
  +4 = 0x0120 for idx 2. Fixed: strh r1,[r7,#4]. Needs in-game re-test; chain must be rebuilt.

## Highlander (patch_highlander_list.py) -- AWAITING IN-GAME TEST
- Test ROM rom_highlander_test.nds (on fixed rom_extra_banlists_test.nds), sha256 99ed32f8...b3f6.
- get_limit tail 0x0202ADBC..0x0202ADE4 rewritten same size: unlisted AND flags-bit0 return 3 - header[+7].
  All stock limit files have header+7 = 0 (verify() asserts it); idx 1/2 stamps zero it too.
- limit200809.bin: count 0, header+7 = 2 -> every card 1 copy, Forbidden included (user 2026-10-05: 'all cards go to 1').
- Text 0x524 'List - September, 2008' -> 'Highlander' in place. 2009 keeps its name (user gave none).
- Chain NOT rebuilt yet; rom_all_patches.nds still has the cache+4 bug.

## Highlander freeze (rom_highlander_test.ml1, 2026-10-05)
- User: selected Highlander, went through all prompts, froze entering the deck editor (black screen).
- Savestate: ARM9 in ABORT mode (CPSR 0x97), spsr_abt 0x2000001F (ARM), lr_abt 0x02158458; ov8 resident.
  Crash: ov8 0x02158428 sl=[0x0221BC0C] = 0x00011621 (expected heap ptr; fallback literal 0x0221C310),
  then ldr [sl+0x294] @0x02158014 -> abort.
- 0x0221BBF0..0x0221BC1B holds {u16 cid, u8 count, u8 flag} entries running OVER 0x0221BC0C:
  a fixed-size card array overflowed. Hypothesis (UNPROVEN): the 'remove cards over the limit'
  routine writes removed copies into a small buffer; Highlander removes far more than any stock list.
- List buffer itself is correct: count 0, name 0x10, +4 0x0160, flags 0x0200. Flag readers all test &2 (ruled out).

- Proven (savestate): default_list/limited_is_forbidden have 0x0221BBF0 = ffff0000 terminator + pointers
  (0x0221BC0C = 0x0221C310); Highlander state has the terminator bumped to ffff0100 and 10 entries
  appended after it (0x0FF9 x2, 0x0FFF x2, 0x1863, 0x2101, 0x1621, 0x1DAD, 0x1340, 0x1B3E).
- Over-limit removal path (ov8): driver 0x02157050..0x0215710C loops finder 0x02152F80 (first over-limit
  card across 5 deck lists, via counter 0x02152BD4 + get_limit) -> mover 0x021538D0(sl, src_list, dst_list,
  cid, [sp]=which) until none left. Mover has an early-out check 0x021534B8; destination list ids are
  globals 0x0217C9A0/0x0217C9AC/0x0217C9B0/0x0217C9B4 (= 0,3,2,1 in the freeze state).
- UNPROVEN: that the mover's destination list is the one that overflowed.

- RULED OUT (user 2026-10-05, 2nd .ml1): the remove-over-limit prompt. Still freezes with a 1-of deck / answering No.
- ROOT CAUSE (static, ov8): deck-editor builder 0x02152354..0x021523B0 walks EVERY card (0x02029E9C idx->cid)
  and appends {cid,2} to editor+0xDA00 (a card list, next list at +0x11D48 => ~4306 slots) for each card with
  get_limit < 3, with NO bound; a 2nd pass 0x021523E4 files each into the Forbidden/Limited/Semi list via
  0x021534B8. Stock lists contribute <= ~130 cards; Highlander makes every card limit 1 -> thousands.
  Any 'every card limited' design needs these paths bounded (and the category list capacities measured).
- DECISION 2026-10-05: Highlander DROPPED (user: 'if you cannot figure it out then just having 1-2 extra
  banlists is fine'). patch_highlander_list.py not shipped.

## Next Experiment
- Savestate AFTER selecting Highlander, BEFORE confirming the remove-cards prompt. One GDB session:
  bp 0x021538D0 log r1,r2,r3,[sp+0x38] per call; bp 0x021534B8 return value; dump 0x0221B990..0x0221BC20
  at the end. Expect the dst list to grow past 0x0221BBF0.
- Cheaper user test first: Highlander with a deck that is ALREADY all 1-ofs (no removals). No crash =>
  the removal path is the trigger.

## Open Questions
- "Display Forbidden/Limited List" may still list the 2010 entries under the new name (cosmetic).
- Does a save that already has mode 1 selected pick it up without re-selecting?
