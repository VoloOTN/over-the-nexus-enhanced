# The Monarchs Masterplan (0x0D6A, donor Speed Spell - Faustian Bargain) -- findings
Status 2026-11-11: CLAUSE 1 ONLY built (cards/masterplan.py, in the combined ROM, sha cbb20ce5...).  Banished trigger NOT built.  AWAITING IN-GAME TEST; nothing user-confirmed.
- C1 "Send 1 Monarch Spell/Trap from your Deck to the GY, except Masterplan": cls0 {Foolish Burial's resolver 0x02208DD5, 0, cond 0x021F0B19, 0, 0} over cls0 phantom 0x0E30 + virtual Deck row 0xFFD6
  {0x6D, 0x0223CAF5 (Deck set-code add handler, type 2 = the flags of Foolish's 0x0223CAD9), 0x2C}.  Foolish Burial's own row = {0xFFFF, 0x0223CAD9, 0x2} (read this session).
- CPU row: the donor owns none; phantom row 0x02391B28 (cid 0x0EA9) repurposed as {0x3C000 | cid = 0x3CD6A, always-true 0x023107C1}.  (0x3D000 | cid is WRONG below 0x1000: bit 12 pollutes the cid; the loc/param base is 0x3C000.)
- CPU evidence: cardtest rows now finds the row; mirror (March/Return/Tenacity kit): drawn 14 / activated 0; a GDB probe on the cond 0x021F0B18 / resolver 0x02208DD4 saw no 0xD6A call in one seed -> the CPU
  does not play it yet (UNEXPLAINED: cond false, or the AI never selects the row); the human path is untested.
- NOT BUILT: banished trigger = target an opposing face-up monster, add a same-Attribute 2400/1000 monster from Deck or GY, then optionally Normal Summon one of six named Monarchs (needs the Dragon Rulers
  'if banished' virtual registry + a Deck-or-GY add + the Double Summon grant restricted to named cards).
