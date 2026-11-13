"""
LZ Compression/Decompression for Nintendo DS files.

Supports LZ10, LZ11, and LZ5 (lz5bg) compression formats commonly used in NDS games.
"""

import bisect
import struct
from pathlib import Path
from typing import Union


class LZCompressionError(Exception):
    """Exception raised for LZ compression/decompression errors."""
    pass


def decompress(data: bytes) -> bytes:
    """
    Decompress LZ-compressed data.
    
    Automatically detects the compression type from the header byte:
    - 0x10: LZ10 (standard LZ77)
    - 0x11: LZ11 (extended LZ77)
    - 0x50: LZ5 (lz5bg format)
    
    Args:
        data: Compressed data bytes
        
    Returns:
        Decompressed data bytes
        
    Raises:
        LZCompressionError: If decompression fails
    """
    if len(data) < 4:
        raise LZCompressionError("Data too short to contain LZ header")

    compression_type = data[0]

    # Fast-path for known header bytes
    if compression_type == 0x10:
        return decompress_lz10(data)
    elif compression_type == 0x11:
        return decompress_lz11(data)
    elif compression_type == 0x50:
        return decompress_lz5(data)

    # Fallback behaviour: be forgiving with unknown header bytes. Some PAC
    # entries may be uncompressed NITRO blobs or use unexpected header bytes.
    # 1) If the payload already looks like a NITRO container, return as-is.
    possible_magics = {b"RGCN", b"RLCN", b"RECN", b"RNAN", b"NARC"}
    if len(data) >= 4 and data[0:4] in possible_magics:
        return data

    # 2) Try common LZ headers by forcing the header byte and attempt
    # decompression. If any attempt yields a buffer starting with a NITRO
    # magic, accept it.
    for try_hdr in (0x11, 0x10, 0x50):
        try:
            trial = bytes([try_hdr]) + data[1:]
            out = None
            if try_hdr == 0x11:
                out = decompress_lz11(trial)
            elif try_hdr == 0x10:
                out = decompress_lz10(trial)
            else:
                out = decompress_lz5(trial)

            if out and len(out) >= 4 and out[0:4] in possible_magics:
                return out
        except LZCompressionError:
            continue

    # Nothing matched — raise a helpful error including the unknown byte.
    raise LZCompressionError(f"Unknown compression type: 0x{compression_type:02X}")


def decompress_lz10(data: bytes) -> bytes:
    """
    Decompress LZ10 (standard LZ77) compressed data.
    
    Format:
    - Byte 0: 0x10 (compression type)
    - Bytes 1-3: Decompressed size (little endian, 24-bit)
    - Bytes 4+: Compressed data
    
    Args:
        data: LZ10 compressed data
        
    Returns:
        Decompressed data
    """
    if data[0] != 0x10:
        raise LZCompressionError("Not LZ10 compressed data")
    
    # Get decompressed size (24-bit little endian)
    decompressed_size = data[1] | (data[2] << 8) | (data[3] << 16)
    
    # Handle extended size header (if size is 0, next 4 bytes contain size)
    pos = 4
    if decompressed_size == 0:
        if len(data) < 8:
            raise LZCompressionError("Invalid extended header")
        decompressed_size = struct.unpack_from('<I', data, 4)[0]
        pos = 8
    
    output = bytearray()
    
    while len(output) < decompressed_size and pos < len(data):
        flags = data[pos]
        pos += 1
        
        for i in range(8):
            if len(output) >= decompressed_size:
                break
            if pos >= len(data):
                break
                
            if flags & (0x80 >> i):
                # Compressed block (back reference)
                if pos + 1 >= len(data):
                    break
                    
                byte1 = data[pos]
                byte2 = data[pos + 1]
                pos += 2
                
                # Length: upper 4 bits of byte1 + 3
                length = ((byte1 >> 4) & 0x0F) + 3
                # Displacement: lower 4 bits of byte1 << 8 | byte2, + 1
                disp = ((byte1 & 0x0F) << 8) | byte2
                disp += 1
                
                # Copy from back reference
                for _ in range(length):
                    if len(output) >= decompressed_size:
                        break
                    if disp > len(output):
                        output.append(0)
                    else:
                        output.append(output[-disp])
            else:
                # Literal byte
                output.append(data[pos])
                pos += 1
    
    return bytes(output)


def decompress_lz11(data: bytes) -> bytes:
    """
    Decompress LZ11 (extended LZ77) compressed data.
    
    LZ11 extends LZ10 with variable-length encoding for longer matches.
    
    Args:
        data: LZ11 compressed data
        
    Returns:
        Decompressed data
    """
    if data[0] != 0x11:
        raise LZCompressionError("Not LZ11 compressed data")
    
    # Get decompressed size
    decompressed_size = data[1] | (data[2] << 8) | (data[3] << 16)
    
    pos = 4
    if decompressed_size == 0:
        if len(data) < 8:
            raise LZCompressionError("Invalid extended header")
        decompressed_size = struct.unpack_from('<I', data, 4)[0]
        pos = 8
    
    output = bytearray()
    
    while len(output) < decompressed_size and pos < len(data):
        flags = data[pos]
        pos += 1
        
        for i in range(8):
            if len(output) >= decompressed_size:
                break
            if pos >= len(data):
                break
                
            if flags & (0x80 >> i):
                # Compressed block
                if pos >= len(data):
                    break
                    
                indicator = data[pos] >> 4
                
                if indicator == 0:
                    # 3-byte encoding: length = 0x11 to 0x110
                    if pos + 2 >= len(data):
                        break
                    length = ((data[pos] & 0x0F) << 4) | (data[pos + 1] >> 4)
                    length += 0x11
                    disp = ((data[pos + 1] & 0x0F) << 8) | data[pos + 2]
                    disp += 1
                    pos += 3
                elif indicator == 1:
                    # 4-byte encoding: length = 0x111 to 0x10110
                    if pos + 3 >= len(data):
                        break
                    length = ((data[pos] & 0x0F) << 12) | (data[pos + 1] << 4) | (data[pos + 2] >> 4)
                    length += 0x111
                    disp = ((data[pos + 2] & 0x0F) << 8) | data[pos + 3]
                    disp += 1
                    pos += 4
                else:
                    # 2-byte encoding: length = 1 to 0x10
                    if pos + 1 >= len(data):
                        break
                    length = indicator + 1
                    disp = ((data[pos] & 0x0F) << 8) | data[pos + 1]
                    disp += 1
                    pos += 2
                
                # Copy from back reference
                for _ in range(length):
                    if len(output) >= decompressed_size:
                        break
                    if disp > len(output):
                        output.append(0)
                    else:
                        output.append(output[-disp])
            else:
                # Literal byte
                output.append(data[pos])
                pos += 1
    
    return bytes(output)


def decompress_lz5(data: bytes) -> bytes:
    """
    Decompress LZ5 (lz5bg) compressed data.
    
    LZ5 is similar to LZ10 but with header byte 0x50.
    Used for background graphics in some NDS games.
    
    Args:
        data: LZ5 compressed data
        
    Returns:
        Decompressed data
    """
    if data[0] != 0x50:
        raise LZCompressionError("Not LZ5 compressed data")
    
    # LZ5 uses same algorithm as LZ10, just different header
    # Create a copy with LZ10 header to reuse the algorithm
    modified_data = bytes([0x10]) + data[1:]
    return decompress_lz10(modified_data)


def compress(data: bytes, compression_type: int = 0x10) -> bytes:
    """
    Compress data using LZ compression.
    
    Args:
        data: Raw data to compress
        compression_type: 0x10 for LZ10, 0x11 for LZ11, 0x50 for LZ5
        
    Returns:
        Compressed data
    """
    if compression_type == 0x10:
        return compress_lz10(data)
    elif compression_type == 0x11:
        return compress_lz11(data)
    elif compression_type == 0x50:
        return compress_lz5(data)
    else:
        raise LZCompressionError(f"Unknown compression type: 0x{compression_type:02X}")


def _prefix_index(data: bytes) -> dict:
    """{3-byte prefix: [every position holding it, ASCENDING]}.

    Both compressors need a >= 3-byte match, so a window position whose next three bytes differ
    can never win -- it is skipped by the `length >= 3` test regardless. Indexing lets the search
    visit only real candidates instead of all 4096 window positions.

    ⚠️ ASCENDING order is load-bearing, not incidental. The compressors keep the FIRST longest
    match they see (the update is strictly `>`), which for an ascending scan is the OLDEST, i.e.
    the largest displacement. Iterate a bucket in any other order and equal-length matches pick a
    different displacement -- still a valid LZ stream, but no longer byte-identical to the ROM
    the oracle produced.
    """
    out: dict = {}
    for k in range(len(data) - 2):
        out.setdefault(data[k:k + 3], []).append(k)
    return out


def compress_lz10(data: bytes) -> bytes:
    """
    Compress data using LZ10 (standard LZ77) compression.
    
    Args:
        data: Raw data to compress
        
    Returns:
        LZ10 compressed data
    """
    output = bytearray()
    
    # Header
    output.append(0x10)
    size = len(data)
    if size < 0x1000000:
        output.append(size & 0xFF)
        output.append((size >> 8) & 0xFF)
        output.append((size >> 16) & 0xFF)
    else:
        output.extend([0, 0, 0])
        output.extend(struct.pack('<I', size))

    pos = 0
    prefix_at = _prefix_index(data)

    while pos < len(data):
        # Build a block of up to 8 tokens
        flags = 0
        block = bytearray()
        
        for i in range(8):
            if pos >= len(data):
                break
            
            # Try to find a match
            best_length = 0
            best_disp = 0
            
            # Search window: up to 4096 bytes back
            search_start = max(0, pos - 0x1000)
            
            # Minimum match length is 3
            # Invariant across the search: depends on `pos`, never on `search_pos`.
            max_length = min(18, len(data) - pos)  # Max length is 18 (15 + 3)

            # Candidates only -- see _prefix_index and the longer note in compress_lz11.
            cand = prefix_at.get(data[pos:pos + 3]) if max_length >= 3 else None
            lo = bisect.bisect_left(cand, search_start) if cand else 0
            hi = bisect.bisect_left(cand, pos) if cand else 0
            for ci in range(lo, hi):
                search_pos = cand[ci]
                length = 0

                while length < max_length:
                    if data[search_pos + length] != data[pos + length]:
                        break
                    length += 1
                    # Handle overlapping matches
                    if search_pos + length >= pos:
                        # For overlapping, we can still match by using already-written bytes
                        while length < max_length:
                            ref_pos = search_pos + (length % (pos - search_pos))
                            if data[ref_pos] != data[pos + length]:
                                break
                            length += 1
                        break
                
                if length >= 3 and length > best_length:
                    best_length = length
                    best_disp = pos - search_pos
                    if length >= 18:  # Maximum possible length
                        break
            
            if best_length >= 3:
                # Encode as back reference
                flags |= (0x80 >> i)
                length_encoded = best_length - 3
                disp_encoded = best_disp - 1
                
                byte1 = ((length_encoded & 0x0F) << 4) | ((disp_encoded >> 8) & 0x0F)
                byte2 = disp_encoded & 0xFF
                
                block.append(byte1)
                block.append(byte2)
                pos += best_length
            else:
                # Encode as literal
                block.append(data[pos])
                pos += 1
        
        output.append(flags)
        output.extend(block)
    
    return bytes(output)


def compress_lz11(data: bytes) -> bytes:
    """
    Compress data using LZ11 (extended LZ77) compression.
    
    LZ11 can encode longer matches than LZ10.
    
    Args:
        data: Raw data to compress
        
    Returns:
        LZ11 compressed data
    """
    output = bytearray()
    
    # Header
    output.append(0x11)
    size = len(data)
    if size < 0x1000000:
        output.append(size & 0xFF)
        output.append((size >> 8) & 0xFF)
        output.append((size >> 16) & 0xFF)
    else:
        output.extend([0, 0, 0])
        output.extend(struct.pack('<I', size))

    pos = 0
    prefix_at = _prefix_index(data)

    while pos < len(data):
        flags = 0
        block = bytearray()

        for i in range(8):
            if pos >= len(data):
                break

            best_length = 0
            best_disp = 0

            search_start = max(0, pos - 0x1000)

            # Invariant across the search: depends on `pos`, never on `search_pos`. Computing
            # it per search position was ~200M redundant min()/len() calls per ROM build.
            max_length = min(0x10110, len(data) - pos)  # LZ11 max length

            # Only positions sharing the next THREE bytes can produce a match, because a match
            # shorter than 3 fails the `length >= 3` test below. `prefix_at` lists exactly those,
            # so the window scan visits candidates instead of all 4096 positions.
            #
            # EXACTNESS. Buckets are built in ASCENDING position order and scanned ascending,
            # and the winner test is strictly `>`, so the OLDEST longest match still wins --
            # the identical record the full linear scan chose. Positions absent from the bucket
            # could only have matched < 3 bytes, which never updated `best_length` anyway.
            #
            # (An earlier attempt pruned *inside* the full scan instead, testing the byte at
            # best_length. It was exact but SLOWER -- 87 s vs 75 s -- because the compare loop
            # already breaks on the first byte for almost every position, so the test merely
            # duplicated work. Measured, not reasoned.)
            cand = prefix_at.get(data[pos:pos + 3]) if max_length >= 3 else None
            lo = bisect.bisect_left(cand, search_start) if cand else 0
            hi = bisect.bisect_left(cand, pos) if cand else 0
            for ci in range(lo, hi):
                search_pos = cand[ci]
                length = 0

                while length < max_length:
                    if data[search_pos + length] != data[pos + length]:
                        break
                    length += 1
                    if search_pos + length >= pos:
                        while length < max_length:
                            ref_pos = search_pos + (length % (pos - search_pos))
                            if data[ref_pos] != data[pos + length]:
                                break
                            length += 1
                        break
                
                if length >= 3 and length > best_length:
                    best_length = length
                    best_disp = pos - search_pos
            
            if best_length >= 3:
                flags |= (0x80 >> i)
                disp_encoded = best_disp - 1
                
                if best_length <= 0x10:
                    # 2-byte encoding
                    length_encoded = best_length - 1
                    byte1 = (length_encoded << 4) | ((disp_encoded >> 8) & 0x0F)
                    byte2 = disp_encoded & 0xFF
                    block.extend([byte1, byte2])
                elif best_length <= 0x110:
                    # 3-byte encoding
                    length_encoded = best_length - 0x11
                    byte1 = (length_encoded >> 4) & 0x0F
                    byte2 = ((length_encoded & 0x0F) << 4) | ((disp_encoded >> 8) & 0x0F)
                    byte3 = disp_encoded & 0xFF
                    block.extend([byte1, byte2, byte3])
                else:
                    # 4-byte encoding
                    length_encoded = best_length - 0x111
                    byte1 = 0x10 | ((length_encoded >> 12) & 0x0F)
                    byte2 = (length_encoded >> 4) & 0xFF
                    byte3 = ((length_encoded & 0x0F) << 4) | ((disp_encoded >> 8) & 0x0F)
                    byte4 = disp_encoded & 0xFF
                    block.extend([byte1, byte2, byte3, byte4])
                
                pos += best_length
            else:
                block.append(data[pos])
                pos += 1
        
        output.append(flags)
        output.extend(block)
    
    return bytes(output)


def compress_lz5(data: bytes) -> bytes:
    """
    Compress data using LZ5 (lz5bg) compression.
    
    Args:
        data: Raw data to compress
        
    Returns:
        LZ5 compressed data
    """
    # LZ5 uses same algorithm as LZ10, just different header byte
    compressed = compress_lz10(data)
    return bytes([0x50]) + compressed[1:]


def decompress_file(input_path: Union[str, Path], output_path: Union[str, Path] = None) -> bytes:
    """
    Decompress a file.
    
    Args:
        input_path: Path to compressed file
        output_path: Optional path to write decompressed data
        
    Returns:
        Decompressed data
    """
    input_path = Path(input_path)
    
    with open(input_path, 'rb') as f:
        compressed_data = f.read()
    
    decompressed_data = decompress(compressed_data)
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(decompressed_data)
    
    return decompressed_data


def compress_file(input_path: Union[str, Path], output_path: Union[str, Path] = None,
                  compression_type: int = 0x10) -> bytes:
    """
    Compress a file.
    
    Args:
        input_path: Path to raw file
        output_path: Optional path to write compressed data
        compression_type: 0x10 for LZ10, 0x11 for LZ11, 0x50 for LZ5
        
    Returns:
        Compressed data
    """
    input_path = Path(input_path)
    
    with open(input_path, 'rb') as f:
        raw_data = f.read()
    
    compressed_data = compress(raw_data, compression_type)
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(compressed_data)
    
    return compressed_data


def get_compression_type(data: bytes) -> str:
    """
    Get the compression type name from data.
    
    Args:
        data: Compressed data
        
    Returns:
        Compression type name or "Unknown"
    """
    if len(data) < 1:
        return "Unknown"
    
    type_map = {
        0x10: "LZ10",
        0x11: "LZ11",
        0x50: "LZ5 (lz5bg)",
        0x24: "Huffman (8-bit)",
        0x28: "Huffman (4-bit)",
        0x30: "RLE",
    }
    
    return type_map.get(data[0], f"Unknown (0x{data[0]:02X})")


# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LZ Compression/Decompression for Nintendo DS files")
    parser.add_argument("action", choices=["compress", "decompress", "info"],
                        help="Action to perform")
    parser.add_argument("input", help="Input file path")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("-t", "--type", choices=["lz10", "lz11", "lz5"], default="lz10",
                        help="Compression type (for compress action)")
    
    args = parser.parse_args()
    
    type_map = {
        "lz10": 0x10,
        "lz11": 0x11,
        "lz5": 0x50,
    }
    
    if args.action == "info":
        with open(args.input, 'rb') as f:
            data = f.read()
        print(f"File: {args.input}")
        print(f"Size: {len(data)} bytes")
        print(f"Compression type: {get_compression_type(data)}")
        if len(data) >= 4 and data[0] in (0x10, 0x11, 0x50):
            dec_size = data[1] | (data[2] << 8) | (data[3] << 16)
            if dec_size == 0 and len(data) >= 8:
                dec_size = struct.unpack_from('<I', data, 4)[0]
            print(f"Decompressed size: {dec_size} bytes")
            print(f"Compression ratio: {len(data) / dec_size * 100:.1f}%")
    
    elif args.action == "decompress":
        output_path = args.output or args.input + ".dec"
        data = decompress_file(args.input, output_path)
        print(f"Decompressed {args.input} -> {output_path}")
        print(f"Output size: {len(data)} bytes")
    
    elif args.action == "compress":
        output_path = args.output or args.input + ".lz"
        compression_type = type_map[args.type]
        data = compress_file(args.input, output_path, compression_type)
        print(f"Compressed {args.input} -> {output_path}")
        print(f"Output size: {len(data)} bytes")
