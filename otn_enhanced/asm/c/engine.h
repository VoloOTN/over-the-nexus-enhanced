/* Engine interface for C effect stubs (EU BYYP). Addresses live in engine_syms.txt, each tied to a KB fact.
 * Mirrors asm/effect_builder.py: PRIMITIVES, CTX_FIELDS and the Deck-top geometry. */
#ifndef ENGINE_H
#define ENGINE_H

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed short s16;
typedef signed int s32;

/* The stub's entry point: linked first, at the slot address. */
#define ENTRY __attribute__((section(".text.entry")))

/* Effect context (R0 at entry), effect_builder.CTX_FIELDS. */
typedef struct EffectCtx {
    u16 cid;              /* +0x00 */
    u8 controller;        /* +0x02 */
    u8 race;              /* +0x03 */
    u8 trigger_type;      /* +0x04 */
    u8 trigger_category;  /* +0x05 */
    u8 slot_phase;        /* +0x06 */
    u8 cost_ran;          /* +0x07: 0 at the menu offer-check, 1 once the cost has run (descriptor) */
    u8 unk8[4];
    u8 card_instance;     /* +0x0C */
} EffectCtx;

/* SPLICE_SHIM (asm/c/shim.S): the engine's live r0-r7 at the hook site. */
typedef struct Regs { u32 r[8]; } Regs;

#define CID(w) ((w) & 0x3FFF)

/* The card a draw will take: player struct 0x0229AC94 + side * 0xB3C, Deck top at +0x304.
 * Draws are queued, so read this BEFORE drawing. */
#define DECK_TOP(side) (*(volatile u32 *)(0x0229AF98 + (side) * 0xB3C))

void draw(u32 side, u32 count);
void reveal_top(u32 side);                 /* reveal the top of the Deck; queues display cmd 0x59 */
int is_monster(u32 cid);
int cid_level(u32 cid);
int get_race(u32 cid);
void turnlog_post(u32 side, u32 cid, u32 kind, u32 zero);
int turnlog_query(u32 side, u32 slot, u32 cid, u32 kind);
int activation_prohibited(u32 a0, u32 a1, u32 a2, u32 a3);   /* 0x021ECDA4; arity is an upper bound (walk UNKNOWN) */
u32 fn_02022E14(u32 a0, u32 a1, u32 a2);                     /* reads r0-r2; meaning unproven */
int fn_021E5060(u32 a0);                                     /* reads r0 */
int fn_021AD870(u32 a0, u32 a1, u32 a2);                     /* reads r0 and r2 */
int count_live_slots(u32 side);                              /* 0x021ACF68 */
int zone_predicate(u32 a0, u32 a1, u32 a2, u32 mask);         /* 0x021D6E40, mask in r3 */
void fn_02235604(u32 a0);                                    /* reads r0 */
int tribute_tag(u32 ctx);                                    /* 0x021E50CC */
int ns_counter(u32 a0);                                      /* 0x021B9514 */
int fn_021F842C(u32 a0);                                     /* reads none of r0-r3 */
int fn_021F5A1C(u32 a0);                                     /* reads none of r0-r3 */
int summon_restriction_class(u32 cid);                       /* 0x020231C8 */
void ss_from_pick(u32 a0, u32 a1, u32 a2);                   /* 0x02204730, reads r0-r2 */
int fn_020235F0(u32 a0);                                     /* set-code thunk, reads r0 */
u32 zone_cid_at(u32 a0, u32 a1);                             /* 0x021A36EC, reads r0-r1 */
int fn_021D2B88(u32 a0, u32 a1, u32 a2, u32 a3);             /* arity bounded at 4 */
int negate_resolver(u32 ctx, u32 a1);                        /* 0x022062F8, reads r0-r1 */
int can_take_ignition(u32 ctx);                              /* 0x021F06E8 */
int acting_zone_check(u32 desc);                             /* 0x021D2C1C */
void desc_fill_from_locator(u32 desc);                       /* 0x021D2D18 */
void change_position(u32 desc, u32 side, u32 zone, u32 a3, u32 s4);   /* 0x021C5324, 5th arg on the stack */
int criteria_registrar(u32 side, u32 cid, u32 pred, u32 list, u32 s4, u32 s5);   /* 0x0223C6AC, 6 args */
void set_lp(u32 side, u32 lp);                               /* 0x021CF8F4 */
int endphase_post(u32 a0, u32 cid);                          /* 0x02253F88 */
u32 fn_021A37D8(u32 a0, u32 a1, u32 a2, u32 a3);             /* reads r0, r1, r3 */
int fn_0202ABC8(u32 cid);                                    /* reads r0 */
int extra_deck_enum(u32 side, u32 cid, u32 filter, s32 *key, u32 s4, u32 s5);   /* 0x0223BE40, 6 args */
int fn_021ACFE8(u32 a0, u32 a1, u32 a2, u32 a3);             /* reads r0-r3 */
u32 fn_021A25A0(u32 a0, u32 a1);                             /* reads r0-r1 */
int key_presence(u32 a0, u32 a1, u32 key);                   /* 0x021A1430, attached-key presence */
int fn_021F03B4(u32 ctx);                                    /* reads r0 */
int fn_021F0820(u32 ctx);                                    /* hand-discard ignition gate, reads r0 */
int costless_you_can(EffectCtx *e, u32 a1);                  /* 0x021E50DC */
int you_can_tag(EffectCtx *e, u32 a1);                       /* 0x021E51E4, wraps 0x021E50DC */
int self_gy_banish_cost(u32 ctx);                            /* 0x021E5708 */
int deck_resolver(u32 a0, u32 a1, u32 a2, u32 a3);           /* 0x02207EF4, reads r0-r3 */
int opt_rider(u32 ctx);                                      /* 0x021F01C0, the 0x0FB6 once-per-turn rider */
u32 fn_021D2D78(u32 a0);                                     /* reads r0 */
int fn_02023EE4(u32 a0);                                     /* set-code thunk, reads r0 */
int criteria_probe(u32 ctx);                                 /* 0x021F05A8 */
int fn_021F6DD8(u32 a0, u32 a1, u32 a2, u32 a3);             /* reads r0-r3 */
int fn_02232CB0(u32 ctx);                                    /* reads r0 */
int fn_021F7374(u32 a0, u32 a1);                             /* reads r0-r1 */
int fn_021F0A38(u32 a0, u32 a1);                             /* reads r0-r1 */
int fn_0224A114(void);                                       /* leaf: return 2 */
int cost_settled(u32 a0, u32 a1, u32 a2, u32 a3);            /* 0x021D2BC8, reads r0-r3 */
int reveal_cost(u32 a0, u32 a1, u32 a2, u32 a3);             /* 0x021EAAA0, reads r0, r1, r3 */
void fn_021D2598(u32 side, u32 a1);                          /* reads r0-r1 */
int draw_condition(u32 ctx);                                 /* 0x021F069C */
void draw_resolver(u32 ctx);                                 /* 0x022065B8, per-cid draw count */
int fn_0223BFD4(u32 a0, u32 cid, u32 a2, u32 cb, u32 s4, u32 s5, u32 s6);   /* 7 args (3 on the stack) */
int fn_021F0B18(u32 ctx);                                    /* reads r0 */
int deck_walker(u32 side, u32 cid, u32 filter, s32 *key, u32 s4, u32 s5);   /* 0x0223BC3C, 6 args (2 on the stack) */

void mill_top_n(u32 ctx, u32 side, u32 n);                   /* 0x021D2148, reads r0-r2 */
int fn_021F2460(u32 a0, u32 a1);                             /* reads r0-r1 */
u32 row_param_provider(u32 ctx);                             /* 0x02234E78, reads r0 */
int criteria_count(u32 side, u32 cid, u32 param, u32 a3);    /* 0x02243FE0, arity bounded at 4 */

int fn_021E6FD8(u32 a0);                                     /* reads r0 */

/* Disguise, the Copycat Hero / Cursed Copycat Noble Arms (cards/c/disguise_*.c) */
void rider_attach(u32 side, u32 zone, u32 key, u32 kind, u32 value);   /* 0x021C479C, value = 5th arg ([sp]) */
int pick_validate(u32 desc, u32 idx, u32 *loc);              /* 0x022349B0: target idx -> *loc = zone<<8 | side */
int revalidate(u32 desc, u32 side, u32 zone);                /* 0x0224A924: re-runs the record's +08 filter */
int level_of_zone(u32 side, u32 zone);                       /* 0x021B8064: CURRENT Level */
u32 zone_card_resolve(u32 side, u32 zone);                   /* 0x021A3320: CURRENT cid/name (honours 0x1D43) */
int race_bit_test(u32 side, u32 zone, u32 race);             /* 0x021B8E30: current race mask & (1 << race) */
int is_tuner_rt(u32 side, u32 zone);                         /* 0x021A1C7C: static Tuner OR granted (0x1E40) */
u32 equip_target_of(u32 side, u32 zone);                     /* 0x021A0DF8: S/T card -> holder zone<<8|side */
int spell_type(u32 cid);                                     /* 0x0202ABE8: Spell/Trap subtype (3 = Equip; Oliver GET_SPELLTYPE) */
int handss_res(u32 desc, u32 a1);                             /* 0x02206ABC: native hand self-SS resolver (summons in 0x80, ends 0x7F) */
int cur_attribute(u32 side, u32 zone, u32 zero);             /* 0x021B8E48: CURRENT Attribute (DNA Transplant aware) */
void equip_relink(u32 equip_loc, u32 new_target_loc);        /* 0x021C4BF0: Equip Shot's move-an-equip (u16 zone<<8|side) */
void destroy_at(u32 desc, u32 side, u32 zone);               /* 0x021CF388: destroy the card at (side, zone) */
int zone_active(u32 side, u32 zone);                          /* 0x021A32B4: card present in that field zone and not disabled */
int deck_ss(u32 desc, u32 a1);                               /* 0x02206CAC: native 'SS 1 monster from your Deck' machine */
void gy_to_hand(u32 desc, u32 side, u32 card_word_ptr);    /* 0x021C7038: GY -> hand; r2 = pointer to the card word in the GY list */
void ban_to_hand(u32 desc, u32 side, u32 card_word_ptr);   /* 0x021C7068: banished -> hand; r2 = pointer into the banished list */
void chain_open(void);                                     /* 0x021D28A4: phase 0x80 of the native add-target resolver */
void chain_close(void);                                    /* 0x021D2964: its closing call */
void send_zeroed_cid(u32 desc, u32 side, u32 zone);       /* 0x021CF740: field -> GY with NO acting cid (kind 0, desc[0] zeroed around the post); the cost-region 'send' */
int field_cost_machine(u32 desc, u32 a1);                /* 0x021E712C: native 'send 1 card from the field to the GY' cost (record +08 = filter); Gearfried C3 */

/* Our own stubs, callable as slot_<ledger name> (asm/cc.py emits every slot). Declare one only when a stub calls it,
 * with the callee stub's measured arity (c_callee_audit.arg_regs). */
int slot_CAVE3_SR_NSCOUNT(u32 a0);
int slot_CAVE3_SK_NSCOUNT(u32 a0);
int slot_CAVE3_DENKO_LOCK(void);
int slot_CAVE3_RUL_FINDK(u32 cid);
u32 slot_CAVE_RUL_KBASE(u32 a0);
int slot_CAVE3_NS_FIELD(u32 side, u32 cid, u32 a2);
int slot_CAVE3_SK_NSFIELD(u32 side, u32 cid);
int slot_CAVE3_SR_NSFIELD(u32 side, u32 cid);
int slot_CAVE_DR_C3_SS(u32 a0, u32 a1);
int slot_CAVE_BF_C3FIND(u32 ctx);
int slot_CAVE_UZ_MASK(u32 ctx);
int slot_CAVE_IK_T_LEGAL(u32 a0);
int slot_CAVE3_WNM_CHECK(u32 cid);
int slot_CAVE_RAIDEN_ONFIELD(u32 a0);

#endif

/* Block Dragon CPU payment (cards/c/block_dragon.c) */
void gy_banish(u32 side, u32 gy_word_ptr, u32 zero);          /* 0x021C7104: GY -> banished, ptr = &player GY word */
void hand_banish(u32 side, u32 hand_index);                   /* 0x021C6E98: hand -> banished, by hand INDEX */
