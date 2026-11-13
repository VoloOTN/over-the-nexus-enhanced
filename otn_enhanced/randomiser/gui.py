"""tkinter front end."""
from __future__ import annotations

import queue
from pathlib import Path

from otn_enhanced.randomise.cardprop import DEFAULT_CAPS
from otn_enhanced.randomise.config import Config, Progress, random_seed
from otn_enhanced.randomise.packs import PACK_MODE_ALL, PACK_MODE_ONLY_LAST, PACK_MODE_STOCK
from otn_enhanced.randomise.run import run, selftest
from otn_enhanced.randomise.seedpile import DECKGEN_UNAVAILABLE, deckgen_available
from otn_enhanced.randomiser.paths import default_seed_pile


def launch_gui(initial: Config | None = None) -> int:
    import threading
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    cfg = initial or Config()
    root = tk.Tk()
    root.title("Over the Nexus Randomiser")
    root.minsize(720, 640)

    rom_in = tk.StringVar(value=cfg.rom_in)
    rom_out = tk.StringVar(value=cfg.rom_out)
    seed = tk.StringVar(value=cfg.seed or random_seed())
    v_attr = tk.BooleanVar(value=cfg.randomise_attribute)
    v_race = tk.BooleanVar(value=cfg.randomise_race)
    v_level = tk.BooleanVar(value=cfg.randomise_level)
    v_synchro = tk.BooleanVar(value=cfg.randomise_synchro_level)
    v_atk = tk.BooleanVar(value=cfg.randomise_atk)
    v_def = tk.BooleanVar(value=cfg.randomise_def)
    v_balanced = tk.BooleanVar(value=cfg.balanced)
    v_packs = tk.StringVar(value=cfg.pack_mode)
    v_puzzles = tk.BooleanVar(value=cfg.zero_puzzle_lp)
    v_puzzle_lp = tk.StringVar(value=str(cfg.puzzle_lp))
    v_decks = tk.BooleanVar(value=cfg.randomise_decks)
    v_nobl = tk.BooleanVar(value=cfg.no_banlist)
    v_pile = tk.StringVar(value=cfg.seed_pile_path or default_seed_pile())
    v_duelists = tk.BooleanVar(value=False)
    v_verbose = tk.BooleanVar(value=False)
    v_dry = tk.BooleanVar(value=False)
    v_report = tk.BooleanVar(value=True)
    cap_vars = {band: tk.StringVar(value=str(limit)) for band, limit in DEFAULT_CAPS.items()}

    pad = {"padx": 6, "pady": 3}

    # --- ROM paths ---
    files = ttk.LabelFrame(root, text="ROM")
    files.pack(fill="x", **pad)

    def pick_in():
        path = filedialog.askopenfilename(
            title="Input ROM", filetypes=[("NDS ROM", "*.nds"), ("All files", "*.*")])
        if path:
            rom_in.set(path)
            if not rom_out.get():
                p = Path(path)
                rom_out.set(str(p.with_name(p.stem + "_randomised.nds")))

    def pick_out():
        path = filedialog.asksaveasfilename(
            title="Output ROM", defaultextension=".nds",
            filetypes=[("NDS ROM", "*.nds")])
        if path:
            rom_out.set(path)

    ttk.Label(files, text="Input ROM").grid(row=0, column=0, sticky="w", **pad)
    ttk.Entry(files, textvariable=rom_in, width=62).grid(row=0, column=1, **pad)
    ttk.Button(files, text="Browse...", command=pick_in).grid(row=0, column=2, **pad)
    ttk.Label(files, text="Output ROM").grid(row=1, column=0, sticky="w", **pad)
    ttk.Entry(files, textvariable=rom_out, width=62).grid(row=1, column=1, **pad)
    ttk.Button(files, text="Browse...", command=pick_out).grid(row=1, column=2, **pad)
    ttk.Label(files, text="Seed").grid(row=2, column=0, sticky="w", **pad)
    ttk.Entry(files, textvariable=seed, width=24).grid(row=2, column=1, sticky="w", **pad)

    # --- properties ---
    props = ttk.LabelFrame(root, text="Card properties")
    props.pack(fill="x", **pad)
    ttk.Checkbutton(props, text="Attribute (DARK / LIGHT / WIND / EARTH / FIRE / WATER)",
                    variable=v_attr).grid(row=0, column=0, columnspan=3, sticky="w", **pad)
    ttk.Checkbutton(props, text="Type / Race (Dragon, Spellcaster, ...)",
                    variable=v_race).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
    ttk.Checkbutton(props, text="Level (1-12)", variable=v_level
                    ).grid(row=2, column=0, sticky="w", **pad)
    synchro_cb = ttk.Checkbutton(props, text="...including Synchro monsters (2-12)",
                                 variable=v_synchro)
    synchro_cb.grid(row=3, column=0, sticky="w", padx=28, pady=3)
    ttk.Checkbutton(props, text="ATK (0-5000, step 50)", variable=v_atk
                    ).grid(row=4, column=0, sticky="w", **pad)
    ttk.Checkbutton(props, text="DEF (0-5000, step 50)", variable=v_def
                    ).grid(row=5, column=0, sticky="w", **pad)

    balanced_cb = ttk.Checkbutton(props, text="Balanced mode -- cap ATK/DEF by level",
                                  variable=v_balanced)
    balanced_cb.grid(row=6, column=0, sticky="w", **pad)

    caps_frame = ttk.Frame(props)
    caps_frame.grid(row=7, column=0, columnspan=3, sticky="w", padx=28)
    for col, (band, var) in enumerate(cap_vars.items()):
        ttk.Label(caps_frame, text=f"Lv {band[0]}-{band[1]}").grid(row=0, column=col, padx=4)
        ttk.Entry(caps_frame, textvariable=var, width=6).grid(row=1, column=col, padx=4)

    def sync_enabled(*_):
        synchro_cb.state(["!disabled"] if v_level.get() else ["disabled"])
        stats_on = v_atk.get() or v_def.get()
        balanced_cb.state(["!disabled"] if stats_on else ["disabled"])
        state = "normal" if (stats_on and v_balanced.get()) else "disabled"
        for child in caps_frame.winfo_children():
            if isinstance(child, ttk.Entry):
                child.configure(state=state)

    for var in (v_level, v_atk, v_def, v_balanced):
        var.trace_add("write", sync_enabled)

    # --- packs ---
    packs = ttk.LabelFrame(root, text="Booster packs")
    packs.pack(fill="x", **pad)
    ttk.Radiobutton(packs, text="Leave unlock conditions as shipped",
                    variable=v_packs, value=PACK_MODE_STOCK).pack(anchor="w", **pad)
    ttk.Radiobutton(packs, text="Unlock all packs from the start",
                    variable=v_packs, value=PACK_MODE_ALL).pack(anchor="w", **pad)
    ttk.Radiobutton(packs, text="Only pack 60 unlocked (1-59 locked)",
                    variable=v_packs, value=PACK_MODE_ONLY_LAST).pack(anchor="w", **pad)

    # --- puzzles ---
    puzzles = ttk.LabelFrame(root, text="Duel puzzles")
    puzzles.pack(fill="x", **pad)
    ttk.Checkbutton(puzzles, text="Set opponent LP in tume01-10 (avoids soft-locks)",
                    variable=v_puzzles).grid(row=0, column=0, sticky="w", **pad)
    ttk.Label(puzzles, text="LP").grid(row=0, column=1, sticky="e", **pad)
    ttk.Entry(puzzles, textvariable=v_puzzle_lp, width=8).grid(row=0, column=2, sticky="w", **pad)

    # --- decks + duelists ---
    extras = ttk.LabelFrame(root, text="Decks and duelists")
    extras.pack(fill="x", **pad)
    decks_cb = ttk.Checkbutton(
        extras, text="Regenerate every deck (generated now, from the randomised stats)",
        variable=v_decks)
    decks_cb.grid(row=0, column=0, sticky="w", **pad)
    ttk.Label(extras, text="seed pile").grid(row=1, column=0, sticky="w", padx=28)
    ttk.Entry(extras, textvariable=v_pile, width=48).grid(row=2, column=0,
                                                          sticky="w", padx=28)
    ttk.Label(extras, text="Slow: the card pool is rebuilt from the new properties, "
                           "then every deck is built. Uses all cores.",
              foreground="#888", wraplength=560
              ).grid(row=3, column=0, sticky="w", padx=28, pady=2)

    have_deckgen = deckgen_available()
    if not have_deckgen:
        decks_cb.state(["disabled"])
        ttk.Label(extras, wraplength=560, foreground="#a33", text=DECKGEN_UNAVAILABLE
                  ).grid(row=4, column=0, sticky="w", padx=28, pady=2)

    ttk.Checkbutton(extras, text="Build decks without banlist restrictions",
                    variable=v_nobl).grid(row=7, column=0, sticky="w", **pad)

    duelists_cb = ttk.Checkbutton(extras, text="Unlock all CPU duelists",
                                  variable=v_duelists)
    duelists_cb.grid(row=5, column=0, sticky="w", **pad)
    duelists_cb.state(["disabled"])
    ttk.Label(extras, text="not solved yet -- placeholder", foreground="#888"
              ).grid(row=6, column=0, sticky="w", padx=28, pady=2)

    # --- run ---
    actions = ttk.Frame(root)
    actions.pack(fill="x", **pad)
    ttk.Checkbutton(actions, text="Dry run", variable=v_dry).pack(side="left", **pad)
    ttk.Checkbutton(actions, text="Show every card below",
                    variable=v_verbose).pack(side="left", **pad)
    ttk.Checkbutton(actions, text="Write report file",
                    variable=v_report).pack(side="left", **pad)
    run_btn = ttk.Button(actions, text="Randomise")
    run_btn.pack(side="right", **pad)
    test_btn = ttk.Button(actions, text="Self-test")
    test_btn.pack(side="right", **pad)

    prog_frame = ttk.Frame(root)
    prog_frame.pack(fill="x", **pad)
    status = ttk.Label(prog_frame, text="ready", anchor="w")
    status.pack(fill="x")
    bar = ttk.Progressbar(prog_frame, mode="determinate", maximum=100, value=0)
    bar.pack(fill="x", pady=(2, 0))

    out = scrolledtext.ScrolledText(root, height=14, wrap="none")
    out.pack(fill="both", expand=True, **pad)

    # Every UI update from the worker goes through this queue, drained by the main
    # thread in _pump below.  Not even root.after is safe to call off-thread --
    # it registers a Tcl command and raises "main thread is not in main loop" --
    # so the worker touches nothing but the queue.
    ui_q: "queue.Queue" = queue.Queue()

    def _pump() -> None:
        try:
            while True:
                ui_q.get_nowait()()
        except queue.Empty:
            pass
        except Exception:  # noqa: BLE001 -- a bad update must not stop the pump
            pass
        root.after(50, _pump)

    def emit(msg: str) -> None:
        ui_q.put(lambda: (out.insert("end", msg + "\n"), out.see("end")))

    def _tk_error(exc, val, tb):
        """Surface a callback exception instead of losing it.

        Tkinter's default prints the traceback to stderr -- and a --windowed
        PyInstaller build has no stderr, so a broken callback looked exactly like
        the button doing nothing at all.
        """
        import traceback
        text = "".join(traceback.format_exception(exc, val, tb))
        out.insert("end", "INTERNAL ERROR in a UI callback:\n" + text + "\n")
        out.see("end")
        status.configure(text="internal error")
        messagebox.showerror("Randomiser", f"{val}\n\nSee the log pane for details.")

    root.report_callback_exception = _tk_error

    class GuiProgress(Progress):
        """Drives the bar from the worker thread, via root.after."""

        def __init__(self):
            self.total = 0
            self.done = 0
            self.label = ""

        def stage(self, label: str, total: int = 0) -> None:
            self.total, self.done, self.label = total, 0, label

            def go():
                bar.stop()
                if total:
                    bar.configure(mode="determinate", maximum=total, value=0)
                    status.configure(text=f"{label}  0/{total}")
                else:
                    # Unknown length (the pool rebuild): march the bar rather than
                    # show a figure the tool cannot honestly know.
                    bar.configure(mode="indeterminate")
                    bar.start(12)
                    status.configure(text=label + "  ...")
            ui_q.put(go)

        def step(self, n: int = 1) -> None:
            self.done = min(self.done + n, self.total) if self.total else self.done + n
            if not self.total:
                return
            d, tot, lbl = self.done, self.total, self.label
            ui_q.put(lambda: (bar.configure(value=d),
                              status.configure(text=f"{lbl}  {d}/{tot}")))

        def finish(self) -> None:
            def go():
                bar.stop()
                bar.configure(mode="determinate", maximum=100, value=100)
                status.configure(text="done")
            ui_q.put(go)

    def collect() -> Config:
        caps = {}
        for band, var in cap_vars.items():
            caps[band] = int(var.get())
        return Config(
            rom_in=rom_in.get().strip(),
            rom_out=rom_out.get().strip(),
            seed=seed.get().strip() or "0",
            randomise_attribute=v_attr.get(),
            randomise_race=v_race.get(),
            randomise_level=v_level.get(),
            randomise_synchro_level=v_synchro.get() and v_level.get(),
            randomise_atk=v_atk.get(),
            randomise_def=v_def.get(),
            balanced=v_balanced.get(),
            caps=caps,
            pack_mode=v_packs.get(),
            zero_puzzle_lp=v_puzzles.get(),
            puzzle_lp=int(v_puzzle_lp.get() or 0),
            randomise_decks=v_decks.get() and have_deckgen,
            seed_pile_path=v_pile.get().strip(),
            no_banlist=v_nobl.get(),
            unlock_duelists=False,
            dry_run=v_dry.get(),
            no_report=not v_report.get(),
        )

    def work(fn):
        # Everything that touches Tk happens on the main thread: the setup here,
        # before the worker starts, and the teardown via root.after.
        run_btn.state(["disabled"])
        test_btn.state(["disabled"])
        out.delete("1.0", "end")
        bar.stop()
        bar.configure(mode="determinate", maximum=100, value=0)
        status.configure(text="starting...")

        def wrapped():
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 -- report, never kill the window
                import traceback
                detail = traceback.format_exc()
                emit(f"ERROR: {exc}")
                emit(detail)
                ui_q.put(lambda: (bar.stop(),
                                  status.configure(text="failed"),
                                  messagebox.showerror("Randomiser", str(exc))))
            finally:
                ui_q.put(lambda: (run_btn.state(["!disabled"]),
                                  test_btn.state(["!disabled"])))
        threading.Thread(target=wrapped, daemon=True).start()

    def do_run():
        # Read every widget HERE, on the main thread.  Doing it inside the worker
        # means calling Tk from another thread, which raises "main thread is not in
        # main loop" -- and in a --windowed build that surfaced as the button
        # simply doing nothing.
        gp = GuiProgress()
        try:
            cfg_now = collect()
            verbose_now = v_verbose.get()
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Randomiser", f"Check the settings: {exc}")
            return
        work(lambda: run(cfg_now, sink=emit, verbose=verbose_now, progress=gp))

    def do_test():
        path = rom_in.get().strip()
        pile_now = v_pile.get().strip() or None
        if not path:
            messagebox.showerror("Randomiser", "Pick an input ROM first.")
            return
        work(lambda: selftest(path, sink=emit, pile_path=pile_now))
        # The self-test loads the deckgen pool to validate seed-pile card names,
        # which takes the better part of a minute with nothing to report yet.  A
        # marching bar is the difference between "working" and "broken".
        gp = GuiProgress()
        gp.stage("running the self-test (validating the seed pile takes a moment)")

    run_btn.configure(command=do_run)
    test_btn.configure(command=do_test)

    sync_enabled()
    _pump()
    root.mainloop()
    return 0
