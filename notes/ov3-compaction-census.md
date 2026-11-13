# ov3 compaction census (generated -- do not edit)

`python -m otn_enhanced.tools.ov3_compaction.census` -- stock `rom.nds`, chain `rom_all_patches.nds`.
Supply is code-structure evidence (scans), NOT in-game proof.

## Summary

| item | value |
|---|---:|
| phantom_dead_stock | 9804 |
| phantom_dead_chain | 7508 |
| phantom_dead_both | 7508 |
| phantom_dead_runs | 118 |
| dup_groups | 25 |
| dup_bytes | 1368 |
| ledger_free | 52 |
| supply_total | 8928 |
| demand_slots | 406 |
| demand_code_slots | 337 |
| demand_used | 29848 |
| demand_zero_reserved | 9484 |
| demand_by_method | {'hand': 3520, 'asm': 26328} |
| fit_placed | 115 |
| fit_bytes | 8220 |

## Largest dead runs (phantom-only, dead in stock AND chain)

| addr | bytes |
|---|---:|
| 0x02212330 | 244 |
| 0x021F0F9C | 240 |
| 0x021F1BFC | 220 |
| 0x021F1B2C | 206 |
| 0x0220A570 | 206 |
| 0x0220995C | 202 |
| 0x021F18F8 | 182 |
| 0x0221AB78 | 168 |
| 0x02220B3C | 166 |
| 0x021F16E4 | 160 |
| 0x021FADB8 | 158 |
| 0x021F19B0 | 148 |
| 0x021D86C8 | 138 |
| 0x021F12B8 | 130 |
| 0x021DF390 | 128 |
| 0x021F573C | 124 |
| 0x021F6AE0 | 124 |
| 0x0220A30C | 116 |
| 0x021F53CC | 114 |
| 0x021FB5D4 | 114 |
| 0x0221D760 | 106 |
| 0x021E1BBC | 104 |
| 0x0220A018 | 104 |
| 0x0221EAA8 | 104 |
| 0x02209A28 | 102 |

## Duplicate function groups (first = canonical)

| bytes | copies |
|---:|---|
| 284 | 0x0214D89C, 0x0214DE00 |
| 48 | 0x0214D86C, 0x0214DDD0, 0x0214E274, 0x0214E6E8, 0x0214EAA4 |
| 12 | 0x02163BD8, 0x02163C5C, 0x021640FC, 0x021641D4, 0x02164424, 0x021644A4, 0x02164508, 0x0216456C, 0x021647B0 |
| 4 | 0x0214CC70, 0x021514F4, 0x0215EC60, 0x02169F5C, 0x0216D59C, 0x02171118, 0x0217139C, 0x021713A0, 0x02172214, 0x0217A414, 0x02184B80, 0x0218CF44, 0x0218CF48, 0x0218E2C0, 0x021945C8, 0x021945CC, 0x02194650, 0x0219482C, 0x0228F9A8, 0x0228F9AC, 0x0228F9B0 |
| 20 | 0x0214D580, 0x0214DA1C, 0x0214DF80, 0x0214E424, 0x0214E898 |
| 68 | 0x021C7484, 0x021C74C8 |
| 64 | 0x02150B0C, 0x02150DF8 |
| 60 | 0x021AD760, 0x021AE58C |
| 60 | 0x021C69D0, 0x021D1F48 |
| 52 | 0x021F03B4, 0x021F0418 |
| 48 | 0x0220D9D0, 0x022183DC |
| 12 | 0x021C0BA8, 0x021C192C, 0x021C1938, 0x021C1944 |
| 32 | 0x0223DE04, 0x0223E7C0 |
| 28 | 0x021792F0, 0x0217930C |
| 28 | 0x0223CE64, 0x0223ECEC |
| 20 | 0x0214CC44, 0x0214CC58 |
| 20 | 0x021F3A28, 0x021F944C |
| 20 | 0x0221B48C, 0x02226760 |
| 8 | 0x0218C384, 0x0218E7C4, 0x02192008 |
| 8 | 0x021942D8, 0x021945C0, 0x021945D0 |
| 16 | 0x021A879C, 0x021A87AC |
| 16 | 0x021D86B8, 0x021DED78 |
| 16 | 0x021DB224, 0x021DFFC8 |
| 4 | 0x0219D31C, 0x021BA0F4, 0x02256C9C, 0x0225BB68 |
| 4 | 0x0220C270, 0x0224A110, 0x0224BC10 |

## Demand: largest cave slots

| slot | used | method | users | flags |
|---|---:|---|---|---|
| CAVE_SL_SELECT | 844 | asm | patch_sea_lancer |  |
| CAVE_ARCH_RES | 604 | asm | patch_animadorned_archosaur |  |
| CAVE_OJ_COST | 580 | asm | patch_ojamassimilation |  |
| CAVE_UCT_C2RES | 524 | asm | patch_ultimate_conductor_tyranno |  |
| CAVE_OQ_C2RES | 504 | asm | patch_overtex_qoatlus |  |
| CAVE_SL_EQUIP | 500 | hand | apply_all_patches, patch_sea_lancer |  |
| CAVE_NAST_RES2 | 488 | asm | patch_ninjitsu_art_super_transformation |  |
| CAVE_WK_RES | 448 | asm | patch_wattkyuki |  |
| CAVE_MISC_RES | 420 | asm | patch_miscellaneousaurus |  |
| CAVE_OJ_HANDLER | 416 | asm | patch_ojamassimilation |  |
| CAVE_EVA_COST | 396 | asm | patch_eva |  |
| CAVE_ROWHOOK | 340 | asm | criteria_row_hook, patch_accel_synchro_stardust_dragon |  |
| CAVE_OJ_RES | 340 | asm | patch_ojamassimilation |  |
| CAVE_WK_HAND | 332 | asm | patch_wattkyuki |  |
| CAVE_LP_C2COST | 316 | asm | patch_lightpulsar, timing_class_hook |  |
| CAVE_WNM_RES_RIDER | 292 | asm | patch_w_nebula_meteorite |  |
| CAVE_JSP_RES | 292 | asm | patch_junk_speeder |  |
| CAVE_TIMINGHOOK | 292 | asm | patch_grandsoil, patch_masked_hero_dark_law, patch_overtex_qoatlus |  |
| CAVE_JS_COST | 276 | asm | criteria_row_hook, patch_jet_synchron |  |
| CAVE_EW_RECORD | 268 | asm | patch_eclipse_wyvern |  |
| CAVE_DEP_COST | 268 | asm | patch_double_evolution_pill |  |
| CAVE_LP_C2COND2 | 260 | asm | patch_lightpulsar |  |
| CAVE_OS_RES | 260 | asm | patch_obedience_schooled |  |
| CAVE_MISC_COST | 256 | asm | patch_miscellaneousaurus |  |
| CAVE_OVI_C2RES | 256 | asm | patch_souleating_oviraptor |  |
| CAVE_OJ_GYSEL | 236 | asm | patch_ojamassimilation |  |
| CAVE_REVSYN_VALID | 232 | asm | patch_revolution_synchron |  |
| CAVE_EVA_RES | 220 | asm | patch_eva |  |
| CAVE_LIB_HOOK | 216 | hand | apply_all_patches, patch_hyper_librarian |  |
| CAVE_TSH_MAIN | 216 | asm | patch_thunder_sea_horse |  |
| CAVE_OJ_GYRES | 216 | asm | patch_ojamassimilation |  |
| CAVE_ARCH_HELP | 212 | asm | patch_animadorned_archosaur |  |
| CAVE_PSI_C2RES | 208 | asm | patch_psi_reflector |  |
| CAVE_MISC_COND | 208 | asm | patch_miscellaneousaurus |  |
| CAVE_PX_RES | 204 | asm | patch_pyrorex |  |
| CAVE_DF_COST | 200 | asm | patch_darkflare |  |
| CAVE_AS_FOLLOW | 200 | hand | apply_all_patches, deck_send_follow_hook, patch_accel_synchron |  |
| CAVE_DEP_COND | 200 | asm | patch_double_evolution_pill |  |
| CAVE_C3_FINISH | 196 | hand | apply_all_patches, patch_grapha |  |
| CAVE_KURIBANDIT_RES | 196 | asm | patch_kuribandit |  |
