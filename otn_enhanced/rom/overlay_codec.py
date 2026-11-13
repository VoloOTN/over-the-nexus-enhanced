"""Codec for ARM9 overlay files in NDS ROMs.

Overlays are loaded via ``ndspy.rom.NintendoDSRom.loadArm9Overlays()``
which returns ``ndspy.code.Overlay`` objects.  The raw file data stored
in the ROM is code-compressed; ``loadArm9Overlays`` transparently
decompresses so ``overlay.data`` is always the *decompressed* payload.

This codec presents overlay metadata as editable JSON and round-trips
the decompressed binary through a base64 blob stored in *meta* (not in
the text, which would be enormous for large overlays).

Encode produces **decompressed** bytes.  The caller (nds_dash) is
responsible for saving the overlay back into the ROM via the
``ndspy.code.Overlay.save(compress=…)`` API.
"""

from __future__ import annotations

import base64
import json
from typing import Any


def decode_overlay(
    decompressed_data: bytes,
    *,
    overlay_id: int,
    compressed_size: int,
    ram_address: int,
    ram_size: int,
    bss_size: int,
    static_init_start: int,
    static_init_end: int,
    flags: int,
    compressed: bool,
    file_id: int,
    verify_hash: bool,
) -> tuple[str, dict[str, Any]]:
    """Decode an ARM9 overlay into a JSON metadata view.

    Parameters
    ----------
    decompressed_data:
        The decompressed overlay payload (``overlay.data``).
    overlay_id, compressed_size, … :
        Attributes copied from the ``ndspy.code.Overlay`` object.

    Returns
    -------
    (json_text, meta)
        *json_text* is a human-readable JSON string showing overlay
        metadata.  *meta* carries everything needed to reconstruct the
        overlay for staging / saving.
    """
    info: dict[str, Any] = {
        "format": "overlay.v1",
        "overlay_id": overlay_id,
        "file_id": file_id,
        "ram_address": f"0x{ram_address:08X}",
        "decompressed_size": len(decompressed_data),
        "compressed_size": compressed_size,
        "ram_size": ram_size,
        "bss_size": bss_size,
        "static_init_start": f"0x{static_init_start:08X}",
        "static_init_end": f"0x{static_init_end:08X}",
        "flags": f"0x{flags:08X}",
        "compressed": compressed,
        "verify_hash": verify_hash,
    }

    meta: dict[str, Any] = {
        "format": "overlay.v1",
        "overlay_id": overlay_id,
        "file_id": file_id,
        "compressed": compressed,
        "ram_address": ram_address,
        "ram_size": ram_size,
        "bss_size": bss_size,
        "compressed_size": compressed_size,
        "static_init_start": static_init_start,
        "static_init_end": static_init_end,
        "flags": flags,
        "verify_hash": verify_hash,
        "data_b64": base64.b64encode(decompressed_data).decode("ascii"),
    }

    return json.dumps(info, indent=2), meta


def encode_overlay(text: str, meta: dict[str, Any] | None = None) -> bytes:
    """Encode overlay JSON / meta back to decompressed overlay bytes.

    The *text* parameter is the (possibly-edited) JSON from the editor.
    Currently only the ``data_b64`` field in *meta* is used to recover
    the binary content; the text serves as informational metadata.

    If ``data_b64`` is present directly in *text* (parsed JSON), it
    takes priority so users *can* supply a new binary blob via the
    editor if they wish.

    Returns
    -------
    bytes
        **Decompressed** overlay data.
    """
    # Try to extract data_b64 from the edited text first
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "data_b64" in parsed:
            return base64.b64decode(parsed["data_b64"])
    except (json.JSONDecodeError, Exception):
        pass

    # Fall back to meta
    if meta and "data_b64" in meta:
        return base64.b64decode(meta["data_b64"])

    raise ValueError(
        "No overlay binary data available.  "
        "Upload a replacement overlay file or include data_b64 in the JSON."
    )
