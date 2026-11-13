/* CPU-vs-CPU battery rig. Replaces the boot callback and the duel-exit
 * callback with rig_boot. The host writes a batch of pairings into the save
 * file before boot; the rig plays them in order and writes each result back
 * with the game's own backup calls, so melonDS can run with the JIT (no GDB).
 * The duel itself runs in the ROM's View Mode spectator path (story_config
 * flags 1): both sides CPU, pads ignored, no result panel.
 *
 * Save layout (battery.py mirrors it): header {magic, n, done, 0} at BASE,
 * pairing i {seed, chara, turbo, deck[2][0xc0]} at PAIR(i), result i at RES(i).
 * The game formats a save without its ID at boot (header 'wcs2011...' from 0);
 * a formatted save leaves 0x684-0x8500 as 0xff, and its bodies sit at 0x8500
 * and 0xb838 (body_save), so the battery uses 0x1000-0x5dd0. */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
#define REG(a) (*(volatile u32 *)(a))
#define PLAYER(s) (0x0229ac94u + (s) * 0xb3cu)
#define DUEL_LAUNCH 0x02019359u
#define CFG_SEED REG(0x020b8bec)
#define CFG_FIRST REG(0x020b8c14)
#define CFG_CONTROL ((volatile u32 *)0x020b8bf4)
#define LAUNCH_STEP REG(0x020b8834)
/* Turbo Duel = duel_mode_reset arg0 4 (-> 0x020b8808) plus mode word 3 and
 * menu id 0x2002, as in the turbo savestates rom_ov5_canary.ml2/.ml4;
 * normal duels have 0 / 0 / 0x2001 (ml1). */
#define DUEL_KIND REG(0x020b880c)
#define MENU_ID REG(0x020b8f3c)
#define DECK_REC ((volatile u8 *)0x020b8c18)
#define DUEL_BLOCK 0x0229dd14u /* state block read by the duel-end step 0x0219d230 */
#define MAX_PAIRS 24
#define BASE 0x1000u
#define PAIR(i) (BASE + 0x10 + (i) * 0x188)
#define RES(i) (PAIR(MAX_PAIRS) + (i) * sizeof(struct Result))

extern void body_init(void);
extern void load_side(u32 side, u32 chara);
extern void duel_mode_reset(u32, u32);
extern void set_callback(u32);
extern int backup_read(u32 off, void *dst, u32 size);
extern int backup_write(u32 off, const void *src, u32 size);
/* Card prop / intid tables are loaded on demand (pattern at 0x0202da4a);
 * load_side's card_index aborts on a NULL intid table without them. */
extern int card_prop_loaded(void), card_intid_loaded(void);
extern void card_prop_load(void), card_intid_load(void);

struct Pair { u32 seed; u16 chara, turbo; u8 deck[2][0xc0]; };
/* stats[side][drawn, summoned, activated][deck slot]: main 0-59, extra 60-74 */
enum { DRAWN, SUMMONED, ACTIVATED };
struct Result { u32 status, lp[2], deck_left[2], duel[32]; u16 mode[2]; u8 stats[2][3][76]; };
struct Rig {
    u32 magic, state, booted, read_ok;
    u32 hdr[4];
    struct Pair pair;
    struct Result res;
};
u32 rig_story_config; /* View Mode story_config, filled in by battery.py build */
struct Rig rig = {0x54544142u}; /* 'BATT' */
static u32 setup[99]; /* View Mode struct StorySetup, 396 B */

/* Duel command queue 0x021c3bc8 (KB event.animation_command_queue), replaced
 * whole: battery.py points its head here. Same append; --probe also logs. */
#define HW(a) (*(volatile u16 *)(a))
#ifdef PROBE
/* Probe dump, battery batch of 1 only: log at save 0x8600 (free until the
 * game's first body_save), count at 0x7700, both player structs at 0x6000. */
struct Ev { u16 op, a, b, c; u8 turn, phase, deck[2], hand[2], pad[2]; };
static struct Ev evlog[1536];
static u32 n_ev[2]; /* kept, seen */
static void probe_flush(void)
{
    backup_write(0x7700, n_ev, sizeof(n_ev));
    backup_write(0x8600, evlog, n_ev[0] * sizeof(struct Ev));
    backup_write(0x6000, (const void *)PLAYER(0), 2 * 0xb3c);
}
#endif

static int slot_of(u32 side, u32 cid)
{
    const u8 *rec = rig.pair.deck[side];
    const u16 *main = (const u16 *)(rec + 0xc), *extra = (const u16 *)(rec + 0xa2);
    u32 i, n = *(const u32 *)rec, x = *(const u32 *)(rec + 8);
    for (i = 0; i < n && i < 60; i++) if (main[i] == cid) return i;
    for (i = 0; i < x && i < 15; i++) if (extra[i] == cid) return 60 + i;
    return -1;
}

static void count(u32 side, u32 cid, u32 what)
{
    int k = slot_of(side, cid);
    if (k >= 0 && rig.res.stats[side][what][k] < 255)
        rig.res.stats[side][what][k]++;
}

/* cid of the card whose ref ((inst << 1) | side) is r: scan that player's card words */
static u32 cid_of_ref(u32 r)
{
    u32 o, w, base = PLAYER(r & 1);
    for (o = 0; o < 0xb3c; o += 4) {
        w = REG(base + o);
        if ((w & 0x3fff) >= 0xd48 && (w & 0x3fff) < 0x2600 &&
            ((w & 0x7fffffff) >> 23) * 2 + ((w >> 14) & 1) == r)
            return w & 0x3fff;
    }
    return 0;
}

/* Opcodes from notes/cpu-battery-findings.md "Duel command opcodes" */
static void tally(u32 op, u32 a, u32 b)
{
    u32 side = op >> 15 & 1, i, d;
    if (rig.state != 2)
        return;
    switch (op & 0x7fff) {
    case 0x56: /* draw b cards: the top is deck[0] */
        d = REG(PLAYER(side) + 0x10);
        for (i = 0; i < b && i < d; i++)
            count(side, REG(PLAYER(side) + 0x304 + 4 * i) & 0x3fff, DRAWN);
        break;
    case 0x2b: count(side, a, SUMMONED); break; /* Normal Summon, a = cid */
    case 0x2c: count(side, cid_of_ref(b), SUMMONED); break; /* Special Summon, b = ref */
    case 0x2d: count(side, b, ACTIVATED); break; /* effect activation, b = cid */
    }
}

void cmd_push(u32 op, u32 a, u32 b, u32 c)
{
    u32 n;
    tally(op, a, b);
#ifdef PROBE
    static u32 after_draw;
    if (after_draw && n_ev[0] < 1536) {
        /* which end of the deck is the top: the newest hand card after a draw */
        u32 s = after_draw - 1, h = REG(PLAYER(s) + 0xc);
        struct Ev *e = &evlog[n_ev[0]++];
        e->op = 0x7f01 | s << 15;
        e->a = h ? REG(PLAYER(s) + 0x124 + 4 * (h - 1)) & 0x3fff : 0;
        e->b = h ? REG(PLAYER(s) + 0x124) & 0x3fff : 0;
        e->c = h;
        after_draw = 0;
    }
    if ((op & 0x7fff) == 0x56 && n_ev[0] + 1 < 1536) {
        u32 s = op >> 15, d = REG(PLAYER(s) + 0x10);
        struct Ev *e = &evlog[n_ev[0]++];
        e->op = 0x7f00 | s << 15;
        e->a = d ? REG(PLAYER(s) + 0x304 + 4 * (d - 1)) & 0x3fff : 0;
        e->b = d ? REG(PLAYER(s) + 0x304) & 0x3fff : 0;
        e->c = d;
        after_draw = s + 1;
    }
    if (n_ev[0] < 1536) {
        struct Ev *e = &evlog[n_ev[0]++];
        e->op = op; e->a = a; e->b = b; e->c = c;
        e->turn = REG(0x0229dd54);
        e->phase = REG(0x0229dd5c) | REG(0x0229dd48) << 4;
        e->deck[0] = REG(PLAYER(0) + 0x10); e->deck[1] = REG(PLAYER(1) + 0x10);
        e->hand[0] = REG(PLAYER(0) + 0xc); e->hand[1] = REG(PLAYER(1) + 0xc);
    }
    n_ev[1]++;
#endif
    if (REG(0x02299114 + 8) == 3)
        return;
    n = REG(0x0229a360 + 8);
    if (n >= 0x100)
        return;
    HW(0x02299b68 + n * 8) = op;
    HW(0x02299b6a + n * 8) = a;
    HW(0x02299b6c + n * 8) = b;
    HW(0x02299b6e + n * 8) = c;
    REG(0x0229a360 + 8) = n + 1;
}

#ifdef FRAMES
/* Experiment build: frames per duel, and frames with a duel command queued or running (the
 * CMD_COUNT / CMD_STATE pair CardWorkshop's w11fast step.c tests). Reported over duel[30] / duel[31]. */
extern void pad_read(void);
static u32 frames, cmd_frames;
/* Frames per current command op ([0x02299b60] & 0xfff, what the queue drain 0x021c3c3c dispatches on),
 * summed over the whole batch; written to save 0x7000 (free: battery ends 0x5dd0, game data at 0x8500). */
static u32 ophist[0x70];
/* Polls of the presentation query 0x0214b490 per code (each poll = one pass still waiting),
 * written to save 0x7200. battery.py points every Thumb call site of 0x0214b490 here. */
static u32 pollhist[0x50];
int rig_present_poll(u32 code)
{
    int busy = ((int (*)(u32))0x0214b490)(code); /* ARM function: bit 0 clear -> blx switches to ARM */
    if (busy) pollhist[code < 0x4f ? code : 0x4f]++;
    return busy;
}
void rig_frame(void)
{
    pad_read();
    if (rig.state == 2) {
        frames++;
        if (REG(0x0229a368) || REG(0x0229de28)) {
            u32 op = REG(0x02299b60) & 0xfff;
            cmd_frames++;
            ophist[op < 0x6f ? op : 0x6f]++;
        }
    }
}
#endif

#ifdef SKIP_WAIT
/* battery.py --skip-wait points chosen handlers' presentation polls (0x0214b490) here: 'done' */
int rig_present_done(u32 code)
{
    (void)code;
    return 0;
}
#endif

static void capture(void)
{
    u32 s, i;
    rig.res.status = 1;
    for (s = 0; s < 2; s++) {
        rig.res.lp[s] = REG(PLAYER(s));
        rig.res.deck_left[s] = REG(PLAYER(s) + 0x10);
    }
    for (i = 0; i < 32; i++) rig.res.duel[i] = REG(DUEL_BLOCK + 4 * i);
#ifdef FRAMES
    rig.res.duel[30] = frames;
    rig.res.duel[31] = cmd_frames;
    frames = cmd_frames = 0;
    backup_write(0x7000, ophist, sizeof(ophist));
    backup_write(0x7200, pollhist, sizeof(pollhist));
#endif
    rig.res.mode[0] = REG(0x020b8808); /* turbo flag at duel end: 4 turbo, 0 normal */
    rig.res.mode[1] = DUEL_KIND;
    backup_write(RES(rig.hdr[2]), &rig.res, sizeof(rig.res));
    rig.hdr[2]++;
    backup_write(BASE, rig.hdr, sizeof(rig.hdr));
#ifdef PROBE
    probe_flush();
#endif
}

static void launch(void)
{
    u32 s, i;
    rig.read_ok = backup_read(PAIR(rig.hdr[2]), &rig.pair, sizeof(rig.pair));
    if (!card_prop_loaded()) card_prop_load();
    if (!card_intid_loaded()) card_intid_load();
    duel_mode_reset(rig.pair.turbo ? 4 : 0, 1);
    DUEL_KIND = rig.pair.turbo ? 3 : 0;
    MENU_ID = rig.pair.turbo ? 0x2002 : 0x2001;
    for (s = 0; s < 2; s++) {
        load_side(s, rig.pair.chara);
        for (i = 0; i < 0xc0; i++) DECK_REC[s * 0xc0 + i] = rig.pair.deck[s][i];
    }
    CFG_CONTROL[0] = CFG_CONTROL[1] = 1;
    CFG_FIRST = 0;
    for (i = 0; i < 99; i++) setup[i] = 0;
    setup[0] = 1 | 1u << 16; /* version 1, flags 1 = spectate */
    setup[1] = rig.pair.seed;
    ((void (*)(const u32 *))rig_story_config)(setup);
    CFG_SEED = rig.pair.seed;
    LAUNCH_STEP = 0;
    for (i = 0; i < sizeof(rig.res.stats); i++) ((u8 *)rig.res.stats)[i] = 0;
    rig.state = 2;
    set_callback(DUEL_LAUNCH);
}

int rig_boot(void)
{
    if (!rig.booted) {
        body_init();
        rig.booted = 1;
        rig.read_ok = backup_read(BASE, rig.hdr, sizeof(rig.hdr));
        rig.state = rig.hdr[0] == rig.magic && rig.hdr[1] <= MAX_PAIRS ? 1 : 4;
    }
    if (rig.state == 2) {
        capture();
        rig.state = rig.hdr[2] < rig.hdr[1] ? 1 : 3;
    }
    if (rig.state == 1)
        launch();
    return 0;
}
