"""Converted (C / C+shim / .S) forms of shipped stubs, applied by ``build --c`` as one final step.

    uv run python -m otn_enhanced.build --c          # -> rom_all_patches_c.nds
    uv run python -m otn_enhanced.c_forms --status   # -> notes/c-migration-status.md

A form replaces one ledger slot's bytes after the whole chain has run, so no patch module changes until the
final switch-over. The step re-proves every form against the slot's bytes AS BUILT before writing it: C forms
by trace-equivalence (tools/c_equiv), ``.S`` fallbacks by byte-identity. A form that fails, or doesn't fit its
slot, aborts the build. Every converted card is AWAITING IN-GAME TEST until the user's final retest.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import NamedTuple

import ndspy.rom

ROOT = Path(__file__).resolve().parents[1]
C_OUT = "data/over_the_nexus/working/rom_all_patches_c.nds"
STATUS = ROOT / "notes" / "c-migration-status.md"


class Form(NamedTuple):
    sources: tuple[str, ...]          # repo-relative .c / .S, linked at the slot
    gate: str = "equiv"               # "equiv" (C, C+shim) or "identical" (.S fallback)
    args: tuple[int, ...] = (0x02300000,)   # entry registers for c_equiv (r0.. ; a ctx pointer by default)
    all_regs: bool = False            # splice / front returns: compare r0-r7
    frame_ok: bool = False            # the stub is declared to touch the engine frame
    runs: tuple = ()                  # extra (args, {addr: byte}) runs for input/memory-dependent branches
    returns: tuple = ()               # extra engine-call return values to sweep (a stub compares a result to them)
    mem: dict | None = None           # planted bytes for the default run (e.g. a bounded list a loop walks)
    defines: dict | None = None       # -D values for a shared template source (cards/c/tpl_*.c)


FORMS: dict[str, Form] = {
    # slot name (allocations ledger) -> converted form
    "CAVE3_PIPER_RES": Form(("otn_enhanced/cards/c/mystic_piper.c",)),   # pilot, in-game confirmed 2026-11-03
    # Phase 1 batch 1 (2026-11-03): plain functions
    "CAVE3_SEKKA_LOCK": Form(("otn_enhanced/cards/c/sekkas_light_lock.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                              runs=(((0x02300000, 0x11, 0x22, 0x33), {0x02300000: 0xE6, 0x02300001: 0x10}),)),  # cid 0x10E6
    "CAVE_RAIDEN_COST": Form(("otn_enhanced/cards/c/raiden_cost.c",)),
    "OV3_DEAD_021B2A4C": Form(("otn_enhanced/cards/c/gates_of_dark_world.c",), args=(0x1C8B, 0x11, 0x22, 0x33),
                               runs=(((0x1234, 0x11, 0x22, 0x33), None),)),
    # Phase 1 batch 2 (2026-11-03)
    "CAVE3_OD_TRIG": Form(("otn_enhanced/cards/c/orient_dragon_trig.c",), args=(0x0FCB, 0x11, 0x22, 0x33),
                           runs=(((0x1234, 0x11, 0x22, 0x33), None),)),
    "CAVE_SEKKA_RES": Form(("otn_enhanced/cards/c/draw2_resolver.c",)),
    "CAVE_SSS_RES": Form(("otn_enhanced/cards/c/draw2_resolver.c",)),
    "CAVE_NK_GAINRES": Form(("otn_enhanced/cards/c/nikitama_gainres.c",)),
    "CAVE_SR_C1COST": Form(("otn_enhanced/cards/c/sr_c1cost.c",)),
    "CAVE3_ELDER_SSCOND": Form(("otn_enhanced/cards/c/elder_six_samurai_sscond.c",), args=(0, 0x11, 0x22, 0x33),
                                runs=(((1, 0x11, 0x22, 0x33), None),)),
    # Phase 1 batch 3 (2026-11-03)
    "CAVE3_WNM_SUB_ACT": Form(("otn_enhanced/cards/c/wnm_sub_act.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE3_SZ_FILTER": Form(("otn_enhanced/cards/c/safe_zone_filter.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE3_TG_NEGATE": Form(("otn_enhanced/cards/c/tg_negate.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    # Phase 1 batch 4 (2026-11-03)
    "CAVE3_TGW_E1COND": Form(("otn_enhanced/cards/c/tgw_e1cond.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                              runs=((( 0x02300000, 0x11, 0x22, 0x33), {0x021DAFF0 + i: 0 for i in range(4)}),)),
    "CAVE3_SR_NSPOST": Form(("otn_enhanced/cards/c/sr_nspost.c",), args=(0, 0x0FF6, 0x22, 0x33),
                             runs=(((0, 0x1234, 0x22, 0x33), None),)),
    "CAVE3_PIPER_COST": Form(("otn_enhanced/cards/c/mystic_piper_cost.c",)),
    "CAVE3_SEAL_COND": Form(("otn_enhanced/cards/c/seal_cond.c",)),
    "CAVE3_SR_NSCOUNT": Form(("otn_enhanced/cards/c/sr_nscount.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                              runs=(((0x02300000, 0x11, 0x22, 0x33), {0x02261F84: 0xF6, 0x02261F85: 0x0F,
                                                                       0x02261F86: 0, 0x02261F87: 0}),)),
    # Phase 1 batch 5 (2026-11-03)
    "OV3_DEAD_02237DFC": Form(("otn_enhanced/cards/c/raiden_cost.c",)),   # Obedience Schooled cost == Raiden's
    "CAVE_CARDCAR_COST": Form(("otn_enhanced/cards/c/cardcar_d_cost.c",)),
    "CAVE_UCT_C4COND": Form(("otn_enhanced/cards/c/uct_c4cond.c",)),
    "CAVE_WR_AICLASS": Form(("otn_enhanced/cards/c/windrose_aiclass.c",), args=(0x190B, 0x11, 0x22, 0x33),
                             runs=(((0x1234, 0x11, 0x22, 0x33), None),)),
    "CAVE_NSC_C2RES": Form(("otn_enhanced/cards/c/nsc_c2res.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    # Slot-calling stubs (2026-11-03): slot_<NAME> symbols
    "CAVE3_SK_NSCOUNT": Form(("otn_enhanced/cards/c/sk_nscount.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                              runs=(((0x02300000, 0x11, 0x22, 0x33), {0x02261F84: 0x50, 0x02261F85: 0x3E, 0x02261F86: 0x00, 0x02261F87: 0x00}),)),
    "CAVE3_NK_NSCOUNT": Form(("otn_enhanced/cards/c/nk_nscount.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                              runs=(((0x02300000, 0x11, 0x22, 0x33), {0x02261F84: 0x51, 0x02261F85: 0x3E, 0x02261F86: 0x00, 0x02261F87: 0x00}),)),
    "CAVE3_DENKO_SET": Form(("otn_enhanced/cards/c/denko_set.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE3_RUL_H4": Form(("otn_enhanced/cards/c/rul_h4.c",), args=(0x1234, 0x11, 0x22, 0x33)),
    # Phase 1 batch 6 (2026-11-03)
    "CAVE_RUL_ATTR": Form(("otn_enhanced/cards/c/rul_attr.c",), args=(0x1234, 0x11, 0x22, 0x33), returns=(0x02300000,)),
    "CAVE_IK_C3COST": Form(("otn_enhanced/cards/c/ik_c3cost.c",)),
    "CAVE_IK_CR_COND2": Form(("otn_enhanced/cards/c/ik_cr_cond2.c",), runs=(
        ((0x02300000,), {0x02300003: 0x10, 0x02300004: 6}), ((0x02300000,), {0x02300003: 0x10, 0x02300004: 5}))),
    "CAVE3_HAIPA_MUSTATK": Form(("otn_enhanced/cards/c/haipa_mustatk.c",), args=(0, 1, 0x22, 0x33),
                                 returns=(0x0FC8, 0x0FFD)),
    "CAVE3_QSR_RES": Form(("otn_enhanced/cards/c/qsr_res.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    # Phase 1 batch 7 (2026-11-03)
    "CAVE3_PIPER_COND": Form(("otn_enhanced/cards/c/mystic_piper_cond.c",), mem={0x02300007: 0},
                              runs=(((0x02300000,), {0x02300007: 1}),)),
    "CAVE3_NIN_POSRES": Form(("otn_enhanced/cards/c/ninishi_posres.c",)),
    "CAVE3_SL_CRIT": Form(("otn_enhanced/cards/c/sea_lancer_crit.c",), args=(0x02300000, 1, 0x22, 0x33)),
    "CAVE3_LSD_RES": Form(("otn_enhanced/cards/c/lsd_res.c",), mem={36285292: 128, 36285293: 0, 36285294: 0, 36285295: 0},
                           runs=(((0x02300000,), {36285292: 127, 36285293: 0, 36285294: 0, 36285295: 0}),)),
    "CAVE3_RUL_H5": Form(("otn_enhanced/cards/c/rul_h5.c",), mem={35761784: 17, 35761785: 17, 35761786: 34, 35761787: 34, 35761788: 0, 35761789: 0},
                          runs=(((0x02300000,), {35761784: 0, 35761785: 0}),)),
    "CAVE3_ATKTGT_GATE": Form(("otn_enhanced/cards/c/atktgt_gate.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                               mem={35516412: 52, 35516413: 18, 35516414: 120, 35516415: 86, 35516416: 0, 35516417: 0}, returns=(0x1234, 0x5678)),
    # Phase 1 batch 8 (2026-11-03)
    "CAVE3_WNM_CHECK": Form(("otn_enhanced/cards/c/wnm_check.c",), args=(0x1234,), returns=(0x14,)),
    "CAVE_OVI_C2COST": Form(("otn_enhanced/cards/c/ovi_c2cost.c",)),
    "CAVE3_TGS_COND": Form(("otn_enhanced/cards/c/elder_six_samurai_sscond.c",), args=(0, 0x11, 0x22, 0x33),
                            runs=(((1, 0x11, 0x22, 0x33), None),)),   # same shape as Elder's
    "CAVE3_SR_NSFIELD": Form(("otn_enhanced/cards/c/sr_nsfield.c",), args=(0, 0x0FF6, 0x22, 0x33),
                              runs=(((0, 0x1234, 0x22, 0x33), None),)),
    "CAVE3_QSR_EXSEL": Form(("otn_enhanced/cards/c/qsr_exsel.c",), args=(0x02300000, 1, 0x22, 0x33),
                             runs=(((0x02300000, 1, 0x22, 0x33), {0x02300002: 5, 0x02300003: 0}),
                                   ((0x02300000, 1, 0x22, 0x33), {0x02300002: 0, 0x02300003: 0x80}))),
    "CAVE3_JS_SSCOND": Form(("otn_enhanced/cards/c/junk_servant_sscond.c",), args=(0, 0x11, 0x22, 0x33)),
    # Phase 1 batch 9 (2026-11-03)
    "CAVE3_NK_NSFIELD": Form(("otn_enhanced/cards/c/nk_nsfield.c",), args=(0, 0x3E51, 0x22, 0x33),
                              runs=(((0, 0x1234, 0x22, 0x33), None),)),
    "CAVE3_SK_NSFIELD": Form(("otn_enhanced/cards/c/sk_nsfield.c",), args=(0, 0x3E50, 0x22, 0x33),
                              runs=(((0, 0x1234, 0x22, 0x33), None),)),
    "CAVE3_TGW_ARMHOOK": Form(("otn_enhanced/cards/c/tgw_armhook.c",), args=(0, 1, 0x22, 0x33), mem={0x02298A36: 0x34, 0x02298A37: 0x12},
                               returns=(4, 5), runs=(((0, 1, 0x22, 0x33), {0x02298A36: 0x00, 0x02298A37: 0x00}),)),
    "CAVE_TSH_SSGATE": Form(("otn_enhanced/cards/c/tsh_ssgate.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_AZURE_PROT": Form(("otn_enhanced/cards/c/azure_prot.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_JW_C1_COND": Form(("otn_enhanced/cards/c/jw_c1_cond.c",)),
    "CAVE_SC_COST": Form(("otn_enhanced/cards/c/soul_charge_cost.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    # Phase 1 batch 10 (2026-11-03)
    "CAVE_ASSD_C1_COND": Form(("otn_enhanced/cards/c/assd_c1_cond.c",)),
    "CAVE_PSI_COND": Form(("otn_enhanced/cards/c/psi_cond.c",)),
    "CAVE_ASSD_C1_SLOT4": Form(("otn_enhanced/cards/c/assd_c1_slot4.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_PSI_SLOT4": Form(("otn_enhanced/cards/c/psi_slot4.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_ASSD_C2_COST": Form(("otn_enhanced/cards/c/assd_c2_cost.c",)),
    "CAVE_ASSAULT_C2COST": Form(("otn_enhanced/cards/c/assault_c2cost.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    # Phase 1 batch 15 (2026-11-03)
    "CAVE_NK_DRAWRES": Form(("otn_enhanced/cards/c/nk_drawres.c",)),
    "CAVE_NSC_SLOT4": Form(("otn_enhanced/cards/c/tpl_tag_post.c",), args=(0x02300000, 0x11, 0x22, 0x33), defines={"TAG": "you_can_tag", "LOG_CID": "0x1106", "KIND": 1}),
    "CAVE_NSC_C2COST": Form(("otn_enhanced/cards/c/tpl_post_then.c",), defines={"LOG_CID": "0x1106", "KIND": 2, "THEN": "tribute_tag((u32)e)"}),
    "CAVE_NEXT_COST": Form(("otn_enhanced/cards/c/next_cost.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_IK_O_HANDH": Form(("otn_enhanced/cards/c/ik_o_handh.c",), args=(0x02300000, 1, 0x22, 0x33)),
    "CAVE_IK_C2COND": Form(("otn_enhanced/cards/c/tpl_opt_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                            defines={"LOG_CID": "0x53A3", "KIND": 1, "NEXT": "fn_021F0B18((u32)e)"}),
    "CAVE_IK_C2SLOT4": Form(("otn_enhanced/cards/c/tpl_tag_post.c",), args=(0x02300000, 0x11, 0x22, 0x33), defines={"TAG": "you_can_tag", "LOG_CID": "0x53A3", "KIND": 1}),
    # Phase 1 batch 14 (2026-11-03)
    "CAVE_GS_SLOT4": Form(("otn_enhanced/cards/c/tpl_tag_post.c",), args=(0x02300000, 0x11, 0x22, 0x33), defines={"TAG": "you_can_tag", "LOG_CID": "0x1110", "KIND": 1}),
    "CAVE_ML_COND": Form(("otn_enhanced/cards/c/tpl_opt_const.c",), defines={"LOG_CID": "0x1C1A", "KIND": 1, "RET": 2}),
    "CAVE_PX_COND": Form(("otn_enhanced/cards/c/tpl_opt_const.c",), defines={"LOG_CID": "0x181F", "KIND": 1, "RET": 1}),
    "CAVE_PX_SLOT4": Form(("otn_enhanced/cards/c/tpl_tag_post.c",), args=(0x02300000, 0x11, 0x22, 0x33), defines={"TAG": "you_can_tag", "LOG_CID": "0x181F", "KIND": 1}),
    "CAVE_WR_COND": Form(("otn_enhanced/cards/c/tpl_opt_const.c",), defines={"LOG_CID": "0x190B", "KIND": 1, "RET": 2}),
    "CAVE_UZ_COND": Form(("otn_enhanced/cards/c/uni_zombie_cond.c",), mem={0x02300007: 0}, runs=(((0x02300000,), {0x02300007: 1}),)),
    "CAVE_SK_COST": Form(("otn_enhanced/cards/c/sakitama_cost.c",), mem={0x02300003: 0xB}, runs=(((0x02300000,), {0x02300003: 4}),)),
    "CAVE_NK_GAINCOND": Form(("otn_enhanced/cards/c/nk_gaincond.c",), mem={0x02300007: 0}, runs=(((0x02300000,), {0x02300007: 1}),)),
    "CAVE_NK_DRAWCOND": Form(("otn_enhanced/cards/c/nk_drawcond.c",)),
    # Phase 1 batch 13 (2026-11-03): shared templates, -D per slot
    "CAVE_OQ_C3COND": Form(("otn_enhanced/cards/c/tpl_opt_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                            defines={"LOG_CID": "0x10A5", "KIND": 2, "NEXT": "fn_021F0820((u32)e)"}),
    "CAVE_OQ_C3SLOT4": Form(("otn_enhanced/cards/c/tpl_tag_post.c",), args=(0x02300000, 0x11, 0x22, 0x33), defines={"TAG": "you_can_tag", "LOG_CID": "0x10A5", "KIND": 2}),
    "CAVE_WU_U3COND": Form(("otn_enhanced/cards/c/tpl_opt_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                            defines={"LOG_CID": "0x1050", "KIND": 1, "NEXT": "fn_021F0A38((u32)e,a1)"}),
    "CAVE_WU_U3COST": Form(("otn_enhanced/cards/c/tpl_settled_post.c",), args=(0x02300000, 0x11, 0x22, 0x33), defines={"KIND": 1}),
    "CAVE_WU_U4COND": Form(("otn_enhanced/cards/c/tpl_opt_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                            defines={"LOG_CID": "0x1050", "KIND": 2, "NEXT": "fn_0224A114()"}),
    "CAVE_WU_U4COST": Form(("otn_enhanced/cards/c/tpl_settled_post.c",), args=(0x02300000, 0x11, 0x22, 0x33), defines={"KIND": 2}),
    "CAVE_WK_COST": Form(("otn_enhanced/cards/c/tpl_settled_post.c",), args=(0x02300000, 0x11, 0x22, 0x33), defines={"KIND": 1}),
    "CAVE_PSI_C2COST": Form(("otn_enhanced/cards/c/psi_c2cost.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_GS_COND": Form(("otn_enhanced/cards/c/tpl_opt_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                          defines={"LOG_CID": "0x1110", "KIND": 1, "NEXT": "fn_021F03B4((u32)e)"}),
    # Phase 1 batch 16 (2026-11-03)
    "CAVE_IK_T_COND": Form(("otn_enhanced/cards/c/ik_t_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_IK_RC_C2CND": Form(("otn_enhanced/cards/c/tpl_opt_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                              defines={"LOG_CID": "0xFE6", "KIND": 1, "NEXT": "fn_021F03B4((u32)e)"}),
    "CAVE_RAIDEN_EP": Form(("otn_enhanced/cards/c/raiden_ep.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE3_WNM_SUB_RIDER": Form(("otn_enhanced/cards/c/wnm_sub_rider.c",), args=(0x02300000, 0x11, 0x2, 0x33)),
    # Phase 1 batch 18 (2026-11-03)
    "CAVE_DS_COND": Form(("otn_enhanced/cards/c/ds_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_DS_COST": Form(("otn_enhanced/cards/c/ds_cost.c",)),
    "CAVE_MAIDEN_COND": Form(("otn_enhanced/cards/c/maiden_cond.c",), mem={0x02300004: 0x13}, runs=(((0x02300000,), {0x02300004: 0x14}), ((0x02300000,), {0x02300004: 0x15}))),
    "CAVE_TSH_RES": Form(("otn_enhanced/cards/c/tsh_res.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    # Phase 1 batch 12 (2026-11-03)
    "CAVE_BF_COST": Form(("otn_enhanced/cards/c/bf_cost.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_BF_C3COND": Form(("otn_enhanced/cards/c/bf_c3cond.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_SM_COND": Form(("otn_enhanced/cards/c/shadow_mist_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_SM_SLOT4": Form(("otn_enhanced/cards/c/shadow_mist_slot4.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_DL_SLOT4": Form(("otn_enhanced/cards/c/dl_slot4.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_UCT_C2COND": Form(("otn_enhanced/cards/c/uct_c2cond.c",), mem={**{0x0229DD5C: 0x02, 0x0229DD5D: 0x00, 0x0229DD5E: 0x00, 0x0229DD5F: 0x00}, 0x02300007: 0},
                             runs=(((0x02300000,), {**{0x0229DD5C: 0x04, 0x0229DD5D: 0x00, 0x0229DD5E: 0x00, 0x0229DD5F: 0x00}, 0x02300007: 0}),
                                   ((0x02300000,), {**{0x0229DD5C: 0x03, 0x0229DD5D: 0x00, 0x0229DD5E: 0x00, 0x0229DD5F: 0x00}, 0x02300007: 0}),
                                   ((0x02300000,), {**{0x0229DD5C: 0x03, 0x0229DD5D: 0x00, 0x0229DD5E: 0x00, 0x0229DD5F: 0x00}, 0x02300007: 1}))),
    "CAVE_ARCH_SLOT4": Form(("otn_enhanced/cards/c/archosaur_slot4.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_ARCH_CRIT": Form(("otn_enhanced/cards/c/archosaur_crit.c",), args=(0x02300000, 1, 0x22, 0x33)),
    # Phase 1 batch 11 (2026-11-03)
    "CAVE_CB_LOCK": Form(("otn_enhanced/cards/c/cb_lock.c",), mem={**{0x0229DD48: 0x00, 0x0229DD49: 0x00, 0x0229DD4A: 0x00, 0x0229DD4B: 0x00}, 0x02300002: 0},
                          runs=(((0x02300000,), {**{0x0229DD48: 0x01, 0x0229DD49: 0x00, 0x0229DD4A: 0x00, 0x0229DD4B: 0x00}, 0x02300002: 0}),)),
    "CAVE_DR_C3_MAIN": Form(("otn_enhanced/cards/c/dr_c3_main.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                             runs=(((0x02300000, 0x11, 0x22, 0x33), {0x02300003: 0xE}),)),
    "CAVE_SR_C1COND": Form(("otn_enhanced/cards/c/sr_c1cond.c",), mem={0x02300007: 0},
                            runs=(((0x02300000,), {0x02300007: 1}),)),
    "CAVE_SR_C2COND": Form(("otn_enhanced/cards/c/sr_c2cond.c",), mem={0x0229AA4C: 0x34, 0x0229AA4D: 0x12, 0x0229AA4E: 0x00, 0x0229AA4F: 0x00},
                            runs=(((0x02300000,), {0x0229AA4C: 0x00, 0x0229AA4D: 0x00, 0x0229AA4E: 0x00, 0x0229AA4F: 0x00}),)),
    "CAVE_OVI_COND": Form(("otn_enhanced/cards/c/ovi_cond.c",)),
    "CAVE_OVI_SLOT4": Form(("otn_enhanced/cards/c/ovi_slot4.c",), args=(0x02300000, 0x11, 0x22, 0x33)),
    "CAVE_BF_COND": Form(("otn_enhanced/cards/c/bf_cond.c",), args=(0x02300000, 0x11, 0x22, 0x33),
                          mem={0x02300007: 0}, runs=(((0x02300000, 0x11, 0x22, 0x33), {0x02300007: 1}),)),
}

# Phase 4: .S fallbacks. cards/c/s/<SLOT>.S files are generated by tools/c_s_gen.py and gated byte-identical.
for _p in sorted((ROOT / "otn_enhanced" / "cards" / "c" / "s").glob("*.S")):
    FORMS.setdefault(_p.stem, Form((_p.relative_to(ROOT).as_posix(),), gate="identical"))


def _slots() -> dict[str, dict]:
    from otn_enhanced.tools.c_corpus import _slots as ledger
    return {s["name"]: s for s in ledger()}


def check(name: str, form: Form, old: bytes, base: int, size: int) -> tuple[bytes, str]:
    """-> (new bytes, gate summary). Raises on a failed gate or a slot overflow."""
    from otn_enhanced.asm.cc import compile_c
    from otn_enhanced.tools.c_equiv import equiv
    srcs = [ROOT / p for p in form.sources]
    new = compile_c(srcs[0] if len(srcs) == 1 else srcs, base, form.defines)
    if len(new) > size:
        raise SystemExit(f"c_forms: {name} is {len(new)} B, slot is {size} B")
    if form.gate == "identical":
        if new != old[:len(new)]:
            raise SystemExit(f"c_forms: {name} .S fallback is not byte-identical to the slot")
        return new, "byte-identical"
    paths = 0
    for args, plant in ((form.args, form.mem), *form.runs):
        paths += equiv(old, new, base, args=args, ss=plant, all_regs=form.all_regs, frame_ok=form.frame_ok,
                       returns=form.returns)["paths"]
    return new, f"trace-equal, {paths} paths over {1 + len(form.runs)} runs"


def apply(src: str, out: str) -> None:
    """Build step: overwrite each FORMS slot in the session ROM after its gate passes."""
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    ovs = rom.loadArm9Overlays([3, 5])
    slots = _slots()
    for name, form in FORMS.items():
        s = slots[name]
        ov = next(o for o in ovs.values() if o.ramAddress <= s["addr"] < o.ramAddress + len(o.data))
        if not isinstance(ov.data, bytearray):
            ov.data = bytearray(ov.data)
        off = s["addr"] - ov.ramAddress
        old = bytes(ov.data[off:off + s["size"]])
        if not any(old):
            raise SystemExit(f"c_forms: {name} is empty in this build: nothing to replace")
        new, how = check(name, form, old, s["addr"], s["size"])
        ov.data[off:off + len(new)] = new
        rom.files[ov.fileID] = ov.save(compress=ov.compressed)
        print(f"  c_forms: {name} <- {', '.join(Path(p).name for p in form.sources)} ({len(new)}/{s['size']} B, {how})")
    rom.saveToFile(out)


def write_status() -> None:
    """One row per corpus stub: proposed form (c_classify), converted form, gate, size vs slot."""
    corpus = {s["name"]: s for s in json.load(open(ROOT / "scratch" / "c_corpus.json"))["slots"]}
    classes = json.load(open(ROOT / "scratch" / "c_classify.json"))
    lines = ["# C migration status", "",
             "Generated by `python -m otn_enhanced.c_forms --status` (inputs: scratch/c_corpus.json, "
             "scratch/c_classify.json). Do not hand-edit.", "",
             "Converted forms build only with `build --c`. Every converted card is **AWAITING IN-GAME TEST** until "
             "the final retest (plan decision 1).", ""]
    done = 0
    rows = []
    for c in classes:
        name, f = c["slot"], FORMS.get(c["slot"])
        if f:
            s = corpus[name]
            try:
                new, how = check(name, f, bytes.fromhex(s["bytes"]), int(s["addr"], 16), s["size"])
                gate, size = f"PASS ({how})", f"{len(new)}/{s['size']}"
                done += 1
            except (SystemExit, AssertionError, Exception) as e:   # incl. CcError: report, don't crash
                gate, size = f"FAIL: {str(e).splitlines()[0]}", f"?/{s['size']}"
            conv = ", ".join(Path(p).name for p in f.sources)
        else:
            gate, size, conv = "", f"-/{c['size']}", ""
        tight = " (tight)" if c["tight"] else ""
        rows.append(f"| {name} | {c['owner'] or ''} | {c['form']}{tight} | {conv} | {gate} | {size} |")
    lines += [f"**{done} / {len(classes)} stubs converted and gated.**", "",
              "| Slot | Owner | Proposed | Converted | Gate | Size (B) |", "|---|---|---|---|---|---:|", *rows, ""]
    STATUS.write_text("\n".join(lines), encoding="utf-8")
    print(f"{done}/{len(classes)} converted -> {STATUS.relative_to(ROOT)}")


if __name__ == "__main__":
    if "--status" in sys.argv:
        write_status()
