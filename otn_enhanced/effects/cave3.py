"""ov3 compaction allocator: static slots inside step 0's freed runs (pool_blocks.FREE_RUNS).

The ov3 twin of ov5_cave.py's CAVE_* constants. One constant per slot, its size in the comment
as `(0xNN bytes)`; a stub laid across several runs by the fragment splitter gets one constant per
fragment. check_allocations parses this file and aborts the build if a slot leaves its run or
overlaps another. ov3 is resident in every duel mode (mem.ov3_resident_all_modes), puzzles
included -- that is the point of the move.

⚠️ pool_blocks.py is FROZEN from the first claim here: regenerating it renumbers / moves runs.
⚠️ Addresses are stock-EU ov3; ov3 code never moves in the chain (only cls rows shift).
"""

import copy
import re
import struct

from otn_enhanced.asm.effect_shim import ThumbAssembler
from otn_enhanced.asm.effect_verify import assert_thumb1_only

# Koa'ki Meiru Wall's cls3 +0C condition, invoked from ov3 0x0224A8B8. Exact fit (88 B stub in an 88 B run).
CAVE3_KMW_COND = 0x0221B848  # (0x58 bytes) koaki_meiru_wall

# Tour Guide's three stubs. Callers all ov3: cls1 +14 via find_event_handler, criteria h via 0x02243FA4,
# filter via the hand/Deck builders' blx r4 (0x0223C13E / 0x0223BDFA).
CAVE3_TG_FILTER = 0x021F1E24  # (0x26 bytes) tour_guide
CAVE3_TG_SELECTOR = 0x021D858C  # (0x3e bytes) tour_guide
CAVE3_TG_NEGATE = 0x02213D74  # (0x0e bytes) tour_guide  (NOT 0x021DED78: that run entry is a REDIRECTS old, so ov3_compact.verify rightly flags the pointer)

# Gravekeeper's Recruiter's search filter + cloned wrapper. Wrapper via the criteria h (ov3 0x02243FA4),
# filter via the builder's blx r4 (ov3 0x0223BDFA). Wrapper base MUST be 4-aligned (verbatim
# `ldr r2,[pc,#8]`).
CAVE3_GK_FILTER = 0x021DEFC8  # (0x30 bytes) gravekeepers_recruiter
CAVE3_GK_WRAPPER = 0x02215188  # (0x24 bytes) gravekeepers_recruiter

# The shared tg_table trampolines + their tables, and T.G. Striker / Warwolf / Rush Rhino's own stubs.
# Hook sites all ov3 BLs; cls2 +0C via the ov3 invoker 0x0224AD94; wrappers via 0x02243FA4.
# ThumbAssembler stubs need a 4-aligned base. The ARMLATCH word is runtime RAM in the ov3 image (works in
# a puzzle).
CAVE3_TGSH_SSTABLE = 0x021DF390  # (0x80 bytes) tg_shared  hand-SS {cid,pad,cond} rows, zero-terminated
CAVE3_TGSH_ARMTRAMP = 0x021FAC78  # (0x3c bytes) tg_shared  leave-arm trampoline (hook 0x021C8216)
CAVE3_TGSH_REGTRAMP = 0x021F1E4C  # (0x48 bytes) tg_shared  End-Phase invoke trampoline (hook 0x02256716)
CAVE3_TGSH_SSTRAMP = 0x021F1398  # (0x34 bytes) tg_shared  hand-SS trampoline (hook 0x0224C026)
CAVE3_TGSH_ARMLIST = 0x021FC2BC  # (0x10 bytes) tg_shared  u16 cid list, zero-terminated
CAVE3_TGSH_REGLIST = 0x0220A0D2  # (0x10 bytes) tg_shared  u16 cid list, zero-terminated
CAVE3_TGS_COND = 0x021E7778  # (0x2a bytes) tg_striker  hand-SS condition
CAVE3_TGS_FILTER = 0x021E8328  # (0x28 bytes) tg_striker  E2 except-self filter
CAVE3_TGS_WRAPPER = 0x022183E0  # (0x24 bytes) tg_striker  E2 cloned wrapper
CAVE3_TGW_ARMHOOK = 0x021F1D54  # (0x30 bytes) tg_warwolf  E1 SS-commit arm hook
CAVE3_TGW_E1COND = 0x021E7574  # (0x18 bytes) tg_warwolf  E1 cls2 +0C latch gate
CAVE3_TGW_ENUMREG = 0x021F11F4  # (0x28 bytes) tg_warwolf  E1 enumeration registration
CAVE3_TGW_E2SEARCH = 0x021DD82C  # (0x28 bytes) tg_warwolf  E2 COMMIT cid swap
CAVE3_TGW_FILTER = 0x021E7738  # (0x28 bytes) tg_warwolf  E2 except-self filter
CAVE3_TGW_WRAPPER = 0x021F4C88  # (0x24 bytes) tg_warwolf  E2 cloned wrapper
CAVE3_TGW_ARMLATCH = 0x021DAFF0  # (0x04 bytes) tg_warwolf  RUNTIME latch word (ov3 RAM; unproven as RAM)
CAVE3_TGR_FILTER = 0x021F1EC8  # (0x28 bytes) tg_rush_rhino  E2 except-self filter
CAVE3_TGR_WRAPPER = 0x021F7E24  # (0x24 bytes) tg_rush_rhino  E2 cloned wrapper

# XX-Saber pair. Both BL hook sites are ov3 (0x022482B2 / 0x021C9F1C). Best fit, 4-aligned.
CAVE3_BOGGART = 0x021D8614  # (0x18 bytes) boggart_knight  Synchro-material remap stub (verbatim, PIC)
CAVE3_DS_ARMTRAMP = 0x021F5AD4  # (0x1c bytes) darksoul  any-leave arming trampoline (hook 0x021C9F1C)

# The Karakuri pair + what they ride. Haipa's two stubs, maiden's SHARED attack-target gate + admit list
# (Haipa/Ninishi clause 2 need it; maiden's own stubs stay in ov5), Ninishi's seven and Scrap Raptor's seven
# C1b stubs, which FRONT Ninishi's grant sites. Every hook is an ov3 BL; Ninishi's cls1 +04/+0C via
# find_event_handler 0x0224A118. Best fit, 4-aligned, no base at a REDIRECTS old.
CAVE3_NS_FIELD = 0x021F12B8  # (0x80 bytes) ninishi  granter lookup without the summoned-this-turn gate
CAVE3_NS_ARM = 0x021D8754  # (0x64 bytes) ninishi  site 1 granter arm (Dverg + donor)
CAVE3_SR_NSARM = 0x021C74CC  # (0x3c bytes) scrap_raptor  site 1 front, chains CAVE3_NS_ARM
CAVE3_NS_PRED = 0x0220AEC8  # (0x30 bytes) ninishi  site 3 Nordic|Karakuri predicate
CAVE3_SR_NSFIELD = 0x021F17DC  # (0x2c bytes) scrap_raptor  site 3 field front, chains CAVE3_NS_FIELD
CAVE3_ATKTGT_GATE = 0x0221B4A0  # (0x28 bytes) atktgt_gate (SHARED: ninishi/haipa/maiden)  attack-target gate hook (BL 0x021C6624)
CAVE3_NIN_POSRES = 0x021F5A70  # (0x26 bytes) ninishi  clause 2 resolver (cls1 +04)
CAVE3_HAIPA_MUSTATK = 0x021D85CC  # (0x24 bytes) karakuri_haipa (SHARED w/ ninishi)  must-attack remap
CAVE3_SR_NSSPENT = 0x0221AE54  # (0x24 bytes) scrap_raptor  site 2 front, chains CAVE3_NS_SPENT
CAVE3_SR_NSPRED = 0x021F10B4  # (0x24 bytes) scrap_raptor  site 3 pred front, chains CAVE3_NS_PRED
CAVE3_SR_NSCOUNT = 0x021F94C8  # (0x20 bytes) scrap_raptor  site 3 counter -> announce skip
CAVE3_HAIPA_BPFLIP = 0x02209E10  # (0x1c bytes) karakuri_haipa  end-of-BP flip -> Arm B
CAVE3_NS_SPENT = 0x0221D7CC  # (0x1c bytes) ninishi  site 2 spent check
CAVE3_SR_NSPOST = 0x021F10D8  # (0x18 bytes) scrap_raptor  site 4 spent post (kind 2)
CAVE3_NS_MATCH = 0x021F3E08  # (0x14 bytes) ninishi  site 4 granter match
CAVE3_SR_NSMATCH = 0x021FAE58  # (0x14 bytes) scrap_raptor  site 4 match front, tail-jumps CAVE3_NS_MATCH
CAVE3_ATKTGT_LIST = 0x021DEFFC  # (0x08 bytes) atktgt_gate (SHARED: ninishi/haipa/maiden)  admit list, 3 u16 cids + 0 (FULL)
CAVE3_NIN_POSCOND = 0x021C7508  # (0x04 bytes) ninishi  clause 2 condition (cls1 +0C)

# Mara + Mystic Piper + Wattcobra. Callers all ov3: Mara = 4 BL sites inside ov3; Piper = cls3
# +04/+0C/+10 via find_event_handler; Wattcobra = criteria h + builder blx r4 (the GK Recruiter path).
CAVE3_MARA_VALID = 0x021F16E4  # (0xa0 bytes) mara  validator hand-branch hook (site 0x02249BEE)
CAVE3_MARA_SEND = 0x021D86C8  # (0x88 bytes) mara  Synchro step-5 hand-send hook (site 0x0226395C)
CAVE3_MARA_COUNT = 0x02223298  # (0x3c bytes) mara  level_sum completion hook (site 0x02249714)
CAVE3_MARA_FIRST = 0x021F143C  # (0x28 bytes) mara  Mara-first hook (site 0x02249B92)
CAVE3_PIPER_RES = 0x02220BE4  # (0x48 bytes) mystic_piper  cls3 +04 resolver
CAVE3_PIPER_COND = 0x021F4BF4  # (0x26 bytes) mystic_piper  cls3 +0C once-per-turn condition
CAVE3_PIPER_COST = 0x0220A27C  # (0x18 bytes) mystic_piper  cls3 +10 cost (turn-log post + Tribute)
CAVE3_WATT_FILTER = 0x0220A518  # (0x40 bytes) wattcobra  set-code+monster+DEF filter
CAVE3_WATT_WRAPPER = 0x021F95BC  # (0x24 bytes) wattcobra  cloned deck-search wrapper (4-aligned)

# Orient Dragon + Shooting Quasar + Hyper Librarian. Callers all ov3: 3 BL hook sites, cls2/cls3 via
# find_event_handler, populate h via 0x02243FA4, Quasar LEAVE via the CAVE3_TGSH_ARMTRAMP literal.
CAVE3_OD_TRIG = 0x021F1464  # (0x1c bytes) orient_dragon  Synchro-trigger list trampoline (BL site ov3 0x022658FC)
CAVE3_QSR_PRED = 0x021F1698  # (0x34 bytes) shooting_quasar  Synchro-only material gate (BL site ov3 0x022482B6)
CAVE3_QSR_COND = 0x021D8630  # (0x2c bytes) shooting_quasar  cls3 +0C HOPT condition (find_event_handler)
CAVE3_QSR_RES = 0x021D865C  # (0x24 bytes) shooting_quasar  cls3 +04 HOPT resolver (find_event_handler)
CAVE3_QSR_EXSEL = 0x021F4C3C  # (0x2c bytes) shooting_quasar  populate h Extra-Deck selector (verbatim clone, 4-aligned)
CAVE3_QSR_LEAVE = 0x022379EC  # (0x60 bytes) shooting_quasar  leave action, BX from CAVE3_TGSH_ARMTRAMP's literal
CAVE3_LIB_HOOK = 0x021F1BFC  # (0xd8 bytes) hyper_librarian  enumeration register hook (BL site ov3 0x02265D00)
CAVE3_LIB_DRAW_RES = 0x021F2718  # (0x50 bytes) hyper_librarian  cls2 +04 chain-draw resolver (find_event_handler)
CAVE3_LIB_LATCH = 0x021DD854  # (0x04 bytes) hyper_librarian  RUNTIME once-per-summon latch word (ov3 RAM, cf. TGW_ARMLATCH)
CAVE3_LIB_SCRATCH = 0x021F95E0  # (0x20 bytes) hyper_librarian  RUNTIME recorder telemetry (ov3 RAM)
CAVE3_ARMORY_BURN = 0x021F1648  # (0x28 bytes) armory_arm  code=0x0C GY-gate bypass (BL site ov3 0x02204E42)

# Elder of the Six Samurai, Shien's Dojo, Naturia Pineapple, Amazoness Heirloom. Callers all ov3: Elder via
# the ov3 hand-SS trampoline's table (hook 0x0224C026); Dojo LVL = cls3 +0C (find_event_handler), CRIT =
# criteria h (0x02243F74), CB = builder blx r4 (0x0223BDFA); Pineapple COND/RES = cls2 +0C/+04, RACE = BL
# site 0x021B8ACC; Heirloom POST = BL site 0x022517C6, FILTER = cls1 +08. Best fit, 4-aligned.
CAVE3_ELDER_SSCOND = 0x021FC26C  # (0x2a bytes) elder_six_samurai  hand-SS condition (tg hand-SS table row)
CAVE3_DOJO_LVL = 0x02209BE0  # (0x5c bytes) shiens_dojo  cls3 +0C Level-bound writer: row BY CID at runtime, no United draw-N gate
CAVE3_DOJO_CB = 0x021F1670  # (0x24 bytes) shiens_dojo  set-code OR predicate (builder blx r4)
CAVE3_DOJO_CRIT = 0x0221D970  # (0x24 bytes) shiens_dojo  criteria h clone using CAVE3_DOJO_CB
CAVE3_PINE_COND = 0x022177CC  # (0x5c bytes) naturia_pineapple  cls2 +0C
CAVE3_PINE_RES = 0x0221D948  # (0x28 bytes) naturia_pineapple  cls2 +04
CAVE3_PINE_RACE = 0x021F189C  # (0x58 bytes) naturia_pineapple  race resolver hook (BL site 0x021B8ACC)
CAVE3_HEIRLOOM_POST = 0x021D85F0  # (0x14 bytes) amazoness_heirloom  Thorn||Heirloom compare (BL site 0x022517C6)
CAVE3_HEIRLOOM_FILTER = 0x021FA618  # (0x24 bytes) amazoness_heirloom  cls1 +08 battled-target filter

# W Nebula Meteorite. Callers all ov3: cls0 +04/+08/+0C and cls2 +04/+08 via find_event_handler (table
# literals ov3 0x0224A3A0 / 0x0224A398 only), +08 via 0x0224A924; populate h -> WRAPPER via ov3 0x02243FA4,
# FILTER via the builder's blx r4 0x0223BDFA. The End-Phase rider resolver (292 B) is split A/B (`b` A->B).
# ThumbAssembler stubs at 4-aligned bases.
CAVE3_WNM_CHECK = 0x022222A0  # (0x28 bytes) w_nebula_meteorite  LIGHT+Reptile monster core
CAVE3_WNM_FILTER = 0x02209A28  # (0x26 bytes) w_nebula_meteorite  populate deck filter (CHECK + Lv>=7)
CAVE3_WNM_WRAPPER = 0x021E1BBC  # (0x24 bytes) w_nebula_meteorite  cloned Botanical deck-search wrapper (4-aligned)
CAVE3_WNM_COND = 0x02212220  # (0x40 bytes) w_nebula_meteorite  cls0 +0C any face-down monster
CAVE3_WNM_SUB_ACT = 0x021D8684  # (0x0c bytes) w_nebula_meteorite  cls0 +08 per-zone eligibility (mask 0x118)
CAVE3_WNM_SUB_RIDER = 0x021FA63C  # (0x3c bytes) w_nebula_meteorite  cls2 +08 per-zone eligibility
CAVE3_WNM_RES_ACT = 0x021F184C  # (0x4e bytes) w_nebula_meteorite  cls0 +04 flip-all + arm rider
CAVE3_WNM_RIDER_A = 0x0220A018  # (0x68 bytes) w_nebula_meteorite  cls2 +04 rider FSM, fragment A (dispatch + 0x80)
CAVE3_WNM_RIDER_B = 0x0220995C  # (0xc0 bytes) w_nebula_meteorite  rider FSM, fragment B (0x7F..0x7C + finish)

# Safe Zone. All three are BL detours over native ov3 code: 0x021984EC (protection chain), 0x021B05CC
# (targeting), 0x021A69CC (direct attack). C1 covers either side (Attack Position: cls0 +08 -> SZ_FILTER);
# 'your opponent' = Safe Zone's CONTROLLER's opponent (SZ_SIDE reads the rider node's source).
CAVE3_SZ_PROTECT = 0x021F4C68  # (0x1c bytes) safe_zone  battle-protection rider query (BL site 0x021984EC)
CAVE3_SZ_TARGET = 0x021F5778  # (0x40 bytes) safe_zone  C3/C4: opponent (of Safe Zone's controller) can't target/destroy (BL site 0x021B05CC)
CAVE3_SZ_DIRECT = 0x022222C8  # (0x38 bytes) safe_zone  C5: no direct attack for a monster on Safe Zone's controller's side (BL site 0x021A69CC)
CAVE3_SZ_FILTER = 0x0220A640  # (0x10 bytes) safe_zone  C1 cls0 +08: face-up Attack Position monster, either side (mask 0xC94)
CAVE3_SZ_SIDE = 0x021F6AE0  # (0x60 bytes) safe_zone  helper: (side, slot) -> controller of the Safe Zone rider, or -1

# Junk Servant. Condition stub reached only through the ov3 hand-SS trampoline's table (hook 0x0224C026), as Elder.
CAVE3_JS_SSCOND = 0x02209A50  # (0x2c bytes) junk_servant  hand-SS condition: canSS AND face-up Junk count

# Unknown Synchron + the SHARED ss_commit_hook it rides (later arms follow the live BL at 0x022692F2).
# COND via the ov3 hand-SS trampoline table (hook 0x0224C026); HOOK via BLs over native ov3 0x022692F2 /
# 0x022693A0; TABLE read only by HOOK (its literal).
CAVE3_UNKSYN_SSCOND = 0x021E1BE0  # (0x40 bytes) unknown_synchron  hand-SS condition (once-per-Duel log query)
CAVE3_SSCOMMIT_HOOK = 0x0221EAA8  # (0x4c bytes) ss_commit_hook  SHARED SS-commit stamp over BL 0x02244D08
CAVE3_SSCOMMIT_TABLE = 0x02212260  # (0x20 bytes) ss_commit_hook  {u16 cid, u16 kind, u32 damage} rows, 0-terminated

# Life Stream Dragon + the SHARED summon_trigger_hook (apply(ov3=True) repoints the one site 0x02265900;
# static ARMS, so Accel Synchro Stardust Dragon / Junk Speeder keep their arm). LSD hooks = BLs over native
# ov3 0x02248AB8 / 0x021BACCC / 0x021CE89C / 0x021CF00E / 0x0225CAC8 / 0x0225CAF2 / 0x021CC656; RES = cls1 +04
# via find_event_handler.
CAVE3_SUMMONTRIG = 0x0221D760  # (0x30 bytes) summon_trigger_hook  SHARED proper-Summon trigger (site 0x02265900)
CAVE3_LSD_DMG = 0x021F53CC  # (0x30 bytes) life_stream_dragon  C2 Des Wombat arm detour (0x021BACCC)
CAVE3_LSD_RES = 0x021FB5D4  # (0x28 bytes) life_stream_dragon  C1 cls1 +04 set LP 4000
CAVE3_LSD_MAT = 0x0221EAF4  # (0x1c bytes) life_stream_dragon  C0 THIRD cid-tree entry (0x02248AB8)
CAVE3_LSD_DEC = 0x02236EA8  # (0x1c bytes) life_stream_dragon  C3 substitute decide switch (0x021CE89C)
CAVE3_LSD_ACK = 0x021FC298  # (0x1c bytes) life_stream_dragon  C3 Yes-consumer switch (0x021CF00E)
CAVE3_LSD_STEP9 = 0x021F944C  # (0x14 bytes) life_stream_dragon  C3 UI step 9 (0x0225CAC8 / 0x0225CAF2)
CAVE3_LSD_SURV = 0x02226760  # (0x14 bytes) life_stream_dragon  C3 executor survive leaf (0x021CC656)

# Sea Lancer. The multi-select is SELECT (prologue + `bl` into the native tail 0x02235912, Soul Charge's
# shape) and the equip resolver is cls3 +04 = native 0x022186E5 + four cid-gated detours (LOCSEL / ARR1 /
# ARR2 / ZONE at 0x022187A2 / 0x022187C8 / 0x022187FC / 0x02218854). cls3 +0C/+14 + criteria h via ov3
# invokers; ATK / ATKRESET = BLs over native ov3 0x021B75F8 / 0x021B44EC. ATKFLAG is a runtime RAM word
# (Warwolf ARMLATCH precedent).
CAVE3_SL_LOCATE = 0x021FB5FC  # (0x48 bytes) sea_lancer  banished locator (0x021A2510 lift, count +0x1C / array +0x7B4)
CAVE3_SL_COND = 0x0221D790  # (0x34 bytes) sea_lancer  cls3 +0C donor cond (desc[+7] gated) AND >=1 candidate
CAVE3_SL_CRIT = 0x021F53FC  # (0x28 bytes) sea_lancer  criteria h: Unicorn Beacon clone with the race list
CAVE3_SL_ARR2 = 0x0220A30C  # (0x20 bytes) sea_lancer  resolver detour 0x022187FC: GY/banished array, 2nd re-read
CAVE3_SL_ATK = 0x0220A32C  # (0x20 bytes) sea_lancer  E3 flat +1000 gate (BL site 0x021B75F8)
CAVE3_SL_LOCSEL = 0x0220A34C  # (0x1c bytes) sea_lancer  resolver detour 0x022187A2: GY locator or banished LOCATE by cid
CAVE3_SL_ARR1 = 0x021F5758  # (0x20 bytes) sea_lancer  resolver detour 0x022187C8: GY/banished array, 1st re-read
CAVE3_SL_ZONE = 0x021F573C  # (0x1c bytes) sea_lancer  resolver detour 0x02218854: source zone 0xE / 0xF by cid
CAVE3_SL_SELECT = 0x021DAFD8  # (0x14 bytes) sea_lancer  cls3 +14 multi-select: prologue + Barcha (r4,r6) + native tail
CAVE3_SL_RACELIST = 0x021DED78  # (0x10 bytes) sea_lancer  {Fish 8, Sea Serpent 5, Aqua 14, 0}
CAVE3_SL_ATKRESET = 0x021DFFC8  # (0x10 bytes) sea_lancer  E3 per-computation flag reset (BL site 0x021B44EC)
CAVE3_SL_ATKFLAG = 0x021BA0F4  # (0x04 bytes) sea_lancer  E3 runtime grant flag (RAM word, starts 0)

# The Seal of Orichalcos. Its C4/C6 cls0 record slots, reached only via find_event_handler (+04/+0C) and the
# per-zone invoker 0x0224A924 (+08), both ov3 (W Nebula's path). FILT/COND are the ov5 builders re-based
# unchanged; RES is Ancient Forest's shape.
CAVE3_SEAL_FILT = 0x0220AEFC  # (0x10 bytes) seal_of_orichalcos  C4 cls0 +08: Special Hurricane filter, own side (4-aligned: pc literal)
CAVE3_SEAL_COND = 0x021F5424  # (0x1a bytes) seal_of_orichalcos  C6 cls0 +0C: kind-5 turn-log query -> 0 / 2
CAVE3_SEAL_RES = 0x021F19B0  # (0x38 bytes) seal_of_orichalcos  C4+C6 cls0 +04: Ancient Forest shape -- stock Field resolver 0x02204C7C (opponent's Field Spell) then phase 0x78: post kind 5 + destroy 0x022048FC
# C3's stub is self-contained (no dependency on Obedience Schooled's zero-filled host 0x02237E1C). Its only
# caller is the retargeted BL @0x021A65E2 (ov3, Pixie Ring's attack-target block).
CAVE3_SEAL_C3 = 0x021F6B40  # (0x1c bytes) seal_of_orichalcos  C3 presence 'Pixie Ring OR the Seal' (BL site 0x021A65E2; 4-aligned: pc literal)

# Uni-Zombie. BL'd from the shared can-attack gate @0x021A4BC8, which every attack in every mode runs.
CAVE3_UZ_ATK = 0x021F18F8  # (0x40 bytes) uni_zombie  can-attack gate hook (BL site 0x021A4BC8): Misfortune OR (lock && !Zombie)

# Sakitama. C3's ADDITIONAL Normal Summon rides the shared granter machinery, so these are on EVERY Normal
# Summon's path -> ov3, never ov5. Six fronts chain Raptor's CAVE3_SR_* (-> ninishi's CAVE3_NS_*);
# granter/spent key K = 0x3E50.
CAVE3_SK_NSARM = 0x02212330  # (0x3c bytes) sakitama  site 1 front (0x021B9634): Spirit && grant(0x13E5,1) && !node(K) -> K
CAVE3_SK_NSPRED = 0x0221236C  # (0x48 bytes) sakitama  site 3 pred front (0x02261E3E): Spirit && grant live -> pool = K
CAVE3_SK_NSFIELD = 0x022123B4  # (0x30 bytes) sakitama  site 3 field front (0x02261E68): K -> grant node ? 0 : -1
CAVE3_SK_NSCOUNT = 0x022123E4  # (0x20 bytes) sakitama  site 3 counter front (0x02261E92): pool K -> 0 (grant spent, not the NS)
CAVE3_SK_NSSPENT = 0x02212404  # (0x20 bytes) sakitama  site 2 front (0x021B9F9C): node(K) -> "has Normal Summoned"
CAVE3_SK_FILTER = 0x021F0F9C  # (0x3c bytes) sakitama  C3 resolver filter: Spirit in hand -> 0x10 (Normal Summon)
CAVE3_SK_SELECT = 0x021F0FD8  # (0x1c bytes) sakitama  filter-selector front (BL site 0x0220D81C): 0x13E5 -> FILTER
CAVE3_SK_NSMATCH = 0x021F0FF4  # (0x14 bytes) sakitama  site 4 match front (0x0226515C): K -> Z, r1 = K

# nikitama: six fronts on the shared Normal-Summon path, each chaining Sakitama's CAVE3_SK_* (full chain) or
# Raptor's CAVE3_SR_* (compact base); grant G = 0x3E52 kind 1, spent key K = 0x3E51. GYNODE fronts the
# sent-to-GY chain node 0x021D13C2 (every cid in its interval runs it).
CAVE3_NK_NSARM = 0x021F1B2C  # (0x3c bytes) nikitama  site 1 front (0x021B9634): Spirit && grant(G,1) && !node(K) -> K
CAVE3_NK_NSPRED = 0x021F1B68  # (0x48 bytes) nikitama  site 3 pred front (0x02261E3E): Spirit && grant live -> pool = K
CAVE3_NK_NSFIELD = 0x021F1BB0  # (0x30 bytes) nikitama  site 3 field front (0x02261E68): K -> grant node ? 0 : -1
CAVE3_NK_NSCOUNT = 0x0220A570  # (0x20 bytes) nikitama  site 3 counter front (0x02261E92): pool K -> 0
CAVE3_NK_NSSPENT = 0x0220A590  # (0x20 bytes) nikitama  site 2 front (0x021B9F9C): node(K) -> "has Normal Summoned"
CAVE3_NK_NSMATCH = 0x0220A5B0  # (0x14 bytes) nikitama  site 4 match front (0x0226515C): K -> Z, r1 = K
CAVE3_NK_GYNODE = 0x0220A5C4  # (0x1c bytes) nikitama  sent-to-GY node front (0x021D13C2): 0x0FE3 -> accept 0x021D1938

# Infernoble Knight Maugis. ov3, not ov5: both chains run on every GY send / trigger for the cids routed
# through these nodes, puzzles included.
CAVE3_IK_M_GYNODE = 0x021FAE44  # (0x10 bytes) infernoble  sent-to-GY node front (0x021D13F6, tests Gilfer 0x13E3): 0x139A -> Z (caller's bne falls to accept)
CAVE3_IK_M_MISS = 0x021F1994  # (0x1a bytes) infernoble  miss-timing node front (0x021EE10C): 0x139A -> Z (never miss), else prev

# NEXT C5: Trap-from-hand gate front. bl @0x021ECAA0 inside 0x021EC93C (hand-Trap permission) -> here:
# Delta Crow 0x201C's native arm (3 Blackwings) + 0x1B22 "you control no cards" (Gorz's 0x021ACF28(side) == 0).
# ov3 on purpose: that gate runs for every Trap in hand, puzzles too. Sits in the run at 0x0221AB78 (unclaimed).
CAVE3_NEXT_HANDGATE = 0x0221AB78  # (0x40 bytes) next  hand-Trap gate front (site 0x021ECAA0)


# Dragon Rulers family: the "virtual registry" hooks -- ov3 because EVERY card's record / criteria /
# hand-offer / banish lookups pass through them (an ov5 hop would break every card in the puzzle editor).
# Only ruler cids are diverted into ov5.
CAVE3_RUL_H1 = 0x021F1008  # (0x54 bytes) dragon_rulers  find_event_handler miss tail 0x0224A86A -> virtual record
CAVE3_RUL_H6 = 0x021F105C  # (0x30 bytes) dragon_rulers  GY->banished cid gate 0x021C71C8 (chains to Eclipse Wyvern's stub)
CAVE3_RUL_FINDK = 0x021F19E8  # (0x24 bytes) dragon_rulers  (cid) -> k in CAVE3_RUL_LIST or -1
CAVE3_RUL_H7 = 0x021F1A0C  # (0x28 bytes) dragon_rulers  0x021D1300 per-cid switch entry 0x021D1B98 -> banish leaf
CAVE3_RUL_H2 = 0x021F1BE0  # (0x14 bytes) dragon_rulers  criteria resolver miss tail 0x02243F24 -> virtual index
CAVE3_RUL_H4 = 0x021F4C1A  # (0x1e bytes) dragon_rulers  ARM9 0x02023566 LIST-B bsearch BL -> + ruler (hand offer)
CAVE3_RUL_LIST = 0x0220A368  # (0x12 bytes) dragon_rulers  u16 ruler cid list (k order), zero-terminated
CAVE3_RUL_H3 = 0x0220A5E0  # (0x2c bytes) dragon_rulers  criteria invoker row compute 0x02243F62 -> virtual row
CAVE3_RUL_H5 = 0x0220A60C  # (0x28 bytes) dragon_rulers  End-Phase registry row 154 resolver (0x02253F89 per big ruler)
CAVE3_RUL_EPLIST = 0x0221AE78  # (0x0a bytes) dragon_rulers  u16 big-ruler cid list, zero-terminated
CAVE3_RUL_MISS = 0x0221AC08  # (0x18 bytes) dragon_rulers  never-miss-timing front at 0x021E510A (ruler -> 0, else 0x021EE0E0)
# Dragon Rulers C4 from the FIELD: H8 = the leave dispatcher's mask-table bsearch BL @0x021C810C. One stub split
# over two runs (cave3.asm_split).
CAVE3_RUL_H8A = 0x02220BCC  # (0x14 bytes) dragon_rulers  H8 front: ruler -> ov5 CAVE_RUL_LEAVE (dest 0xF -> virtual mask row), else H8B
CAVE3_RUL_H8B = 0x021F1A34  # (0x08 bytes) dragon_rulers  H8 native tail: pop args, bl 0x02022E44, return
CAVE3_RUL_PC0 = 0x02220B3C  # (0x60 bytes) dragon_rulers  4 x precheck {baby cid -> 1}, summon list site 0x02268090
CAVE3_RUL_PC4 = 0x02220B9C  # (0x30 bytes) dragon_rulers  2 x precheck {baby cid -> 1}, attack list site 0x021A4AC6
CAVE3_RUL_PC6 = 0x021FADB8  # (0x30 bytes) dragon_rulers  2 x precheck {baby cid -> 1}, attack list site 0x021A4AC6

# Denko Sekka. Both fronts sit on gates EVERY card passes (S/T Set legality 0x021A1B20, activation-prohibited
# predicate 0x021ECDA4) -> ov3, never ov5.
CAVE3_DENKO_LOCK = 0x021F1938  # (0x5c bytes) denko_sekka  lock(): a side has face-up 0x0FE8 in zones 0..4 AND no Set card in 5..10
CAVE3_DENKO_FIG = 0x021FADE8  # (0x48 bytes) denko_sekka  C2b front @0x021ED614 (Cursed Fig bl): Set S/T in 5..10 && lock -> prohibited
CAVE3_DENKO_SET = 0x0221ABB8  # (0x10 bytes) denko_sekka  C2a front @0x021A1B4C (0x021A1B20 tail bl 0x020235F0): || lock -> cannot Set

# Sekka's Light. C3's front sits on all 3 BLs to the activation-prohibited predicate 0x021ECDA4 (0x021EDA2E /
# 0x021D6B5C / 0x021FC116), which EVERY card passes -> ov3, never ov5.
CAVE3_SEKKA_LOCK = 0x0221ABC8  # (0x40 bytes) sekkas_light  stock || (kind-5 0x10E6 node on actor && cid != 0x10E6 && !monster)

# Fire Formation - Tenki. Front on the criteria resolver MISS tail 0x02243F24 (every criteria lookup in every
# mode -> ov3): cid 0x1777 -> virtual index 0x5B00 (Rulers' H3 maps it to ov5 CAVE_TENKI_ROW), else tail
# CAVE3_RUL_H2.
CAVE3_TENKI_H2 = 0x021FAE30  # (0x14 bytes) fire_formation_tenki  0x02243F24 front: 0x1777 -> 0x5B00, else CAVE3_RUL_H2

# Sacred Sword of Seven Stars. Second front on the criteria resolver miss tail 0x02243F24, AHEAD of Tenki's:
# cid 0x130A -> virtual index 0x5F00 (Rulers' H3 maps it to ov5 CAVE_SSS_ROW), else tail CAVE3_TENKI_H2.
CAVE3_SSS_H2 = 0x021F16CC  # (0x14 bytes) sacred_sword_seven_stars  0x02243F24 front: 0x130A -> 0x5F00, else CAVE3_TENKI_H2

def asm_split(frags: list[tuple[int, int, ThumbAssembler]]) -> list[bytes]:
    """Assemble one logical stub laid across several runs: frags = [(base, size, builder)].

    *builder* is an EffectBuilder / ThumbAssembler. Labels are
    global across fragments. Each fragment carries its own literal pool (an `ldr =` in two
    fragments costs a word in each). Leave a fragment / reach another one with `b label`
    (+-2 KB) or `bl_label(label)` (far; CLOBBERS LR -- only after `push {..,lr}`)."""
    syms: dict[str, int] = {}
    for base, _, prog in frags:
        lab = {k: base + off for k, off in prog._layout()[1].items()}
        dup = syms.keys() & lab.keys()
        assert not dup, f"label(s) defined in two fragments: {sorted(dup)}"
        syms.update(lab)
    out = []
    for base, size, prog in frags:
        own = prog._layout()[1].keys()
        c = copy.copy(prog)             # leave the caller's builder untouched
        items = []
        for it in prog._items:
            if it[0] == "insn" and it[2].strip() in syms and it[2].strip() not in own:
                it = ("insn", it[1], f"0x{syms[it[2].strip()]:08X}")
            elif it[0] == "bllabel" and it[1] not in own:
                it = ("bl", syms[it[1]])
            items.append(it)
        c._items = items
        out.append(_checked(base, size, c.assemble(base, pad="nop"), ""))
    return out


def _checked(base: int, size: int, blob: bytes, src: str) -> bytes:
    assert len(blob) <= size, f"fragment @{base:#010x} is {len(blob)} B > {size} B"
    assert_thumb1_only(blob, base)
    # thumb_asm drops LR from a pop list silently (thumb.pop_into_lr_footgun class)
    assert not re.search(r"\bpop\s*\{[^}]*\blr\b", src, re.I), f"pop {{..lr}} in fragment @{base:#x}"
    regs: dict[int, int] = {}          # ldr rD,[pc,#] -> value; a blx of an EVEN value enters ARM
    i, end = 0, len(blob)               # stop at the first pool word: data is not code
    while i < end - 1:
        hw = struct.unpack_from("<H", blob, i)[0]
        i += 2
        if hw & 0xF800 == 0x4800:
            lit = ((base + i + 2) & ~3) + (hw & 0xFF) * 4 - base
            if lit + 4 <= len(blob):
                regs[(hw >> 8) & 7] = struct.unpack_from("<I", blob, lit)[0]
                end = min(end, lit)
        elif hw & 0xFF87 == 0x4780:
            v = regs.get((hw >> 3) & 0xF)
            assert v is None or v & 1, f"blx to even literal {v:#x} @{base + i - 2:#x} (ARM state -> freeze)"
    return blob


OV5_BASE = 0x022C5900


def put(ov: bytearray, addr: int, blob: bytes, src: str = "") -> None:
    """Write a checked stub into its ov3 pool slot, which must be zero (step 0 ran) or hold it."""
    from otn_enhanced.rom.overlay_io import RAM_BASE
    _checked(addr, len(blob), blob, src)
    o = addr - RAM_BASE
    assert bytes(ov[o:o + len(blob)]) in (bytes(len(blob)), blob), (
        f"ov3 slot @{addr:#x} is not zero -- step 0 (ov3_compact) must run first")
    ov[o:o + len(blob)] = blob


def read_code(rom, ov, addr: int, n: int) -> bytes:
    """n bytes at RAM *addr* from ov3 (*ov*) or, at/above OV5_BASE, from overlay 5 of *rom*."""
    from otn_enhanced.rom.overlay_io import RAM_BASE
    if addr < OV5_BASE:
        return bytes(ov[addr - RAM_BASE:addr - RAM_BASE + n])
    from otn_enhanced.effects import ov5_cave
    return ov5_cave.read_cave(rom, addr, n)
