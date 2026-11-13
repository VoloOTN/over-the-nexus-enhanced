# Tutorials

Each folder is one job, written as steps you can follow without prior context. Every `HOWTO.md` has the same
shape: **Goal**, **Before you start**, **Steps**, **Worked example**, **Check it**, **Pitfalls**.

All commands run from the repo root with the project venv:

```
uv run python -m otn_enhanced.<module>
```

## Start here

| If you want to... | Read |
|---|---|
| Build the ROM, or prove a change did not break it | [building-and-verifying](building-and-verifying/HOWTO.md) |
| Pick the card that will carry a new effect | [donor-cards](donor-cards/HOWTO.md) |
| Write the code an effect runs | [effect-writing](effect-writing/HOWTO.md) |
| Wire that code into the engine's tables | [effect-insertion](effect-insertion/HOWTO.md) |
| Hook a shared engine routine instead of a table | [trampolines](trampolines/HOWTO.md) |
| Decide where injected code lives | [caves-and-allocation](caves-and-allocation/HOWTO.md) |
| Compose with other cards' hooks, or order steps | [shared-hooks-and-ordering](shared-hooks-and-ordering/HOWTO.md) |
| Change stats, name, description or archetype | [card-text-and-stats](card-text-and-stats/HOWTO.md) |
| Change card art or a field background | [art-tweaks](art-tweaks/HOWTO.md) |
| Add a card at a brand-new cid | [new-cards](new-cards/HOWTO.md) |
| Change packs, decks, banlists, unlocks, rewards | [data-patches](data-patches/HOWTO.md) |
| Find out why an effect fails in-game | [debugging-in-game](debugging-in-game/HOWTO.md) |
| Port an existing card onto `EffectBuilder` | [rewriting-a-card-onto-effectbuilder](rewriting-a-card-onto-effectbuilder/HOWTO.md) |

## The shortest path to a new card

1. `donor-cards`: choose a donor and gather the evidence.
2. `effect-writing` then `effect-insertion`: code, then table rows.
3. `card-text-and-stats`: what the player sees.
4. `building-and-verifying`: build a single-card ROM, run `verify`.
5. Load it in melonDS. **Only an in-game test shows the card works**; a passing `verify()` does not.

## Ground rules that apply to every tutorial

- The EU ROM (`BYYP`) is the only target. Addresses are EU. The US build has a different overlay-3 layout.
- Keep the donor's cid. Changing a cid breaks the deck editor and menu lookups.
- Injected code is Thumb-1 only. The CPU is ARMv5TE; Thumb-2 freezes it.
- Every table insert is count-neutral: drop a phantom cid to make room.
- Do not record a card as confirmed unless it was tested in-game.
