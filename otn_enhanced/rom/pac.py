"""
PAC Archive Format Parser and Packer

Handles multiple PAC format variants used in Yu-Gi-Oh! NDS games.
Designed for reliable unpacking and repacking with preserved file order.

PAC Format Variants:
===================

v1 (Marker Format) - 27 files
    Used by: bin.pac, deck.pac, bin2.pac, Common.pac, tutorial.pac, trunk.pac,
             effect.pac, janken.pac, duel2d.pac, Structure.pac, RACE.pac, and 16 others.
    
    Key identifier: 0xFFFF marker on 16-byte boundary separating header from file table
    
    Structure:
        - Header (variable): Filenames separated by linebreak bytes (0x0A-0x18)
        - Marker: 0xFFFF on 16-byte aligned boundary
        - File table: 8-byte entries (4-byte address + 4-byte size)
        - Optional: 8-byte 'after' field for some entries
        - Padding to align file data section
        - File data: Sequential file contents

v2 (Simple Format) - 1 file
    Used by: puzzle.pac
    
    Key identifier: .ydq and .ydc file extensions in header
    
    Structure:
        - Header (0x0-0x100): Filenames with .ydq/.ydc extensions
        - File count (4 bytes) + padding (4 bytes)
        - File table: 8-byte entries with specialized format
            * Bytes 0-1: Unknown/flags
            * Bytes 2-3: File size (little endian)
            * Bytes 4-5: Unknown/flags
            * Bytes 6-7: File offset (little endian)
        - File data starts at 0x200

v3 (Graphics Format) - 11 files
    Used by: CharaMake.pac, Closet.pac, WiFi.pac, D_race_result.pac, Getpack.pac,
             FriendMenu.pac, FreeDuel.pac, and 4 others.
    
    Key identifier: Graphics extensions (lz5bg, lznanr, lzncer, lzncgr, lznclr, etc.)
    
    Structure:
        - Header (0x0-0x3): Usually starts with 00 00
        - Filenames scattered in header area (various encodings)
        - File table at aligned offset (0x200, 0x400, 0x600, 0x800)
        - Count: Either 4-byte at table offset, or 2-byte at offset+2
        - Entries start at offset+4, +8, or +12
        - Entry format: 8 bytes (size + address OR address + size)
        - Base offset: 0, 0x200, 0x400, 0x800, 0x1000, or 0x2000
        - File data: At calculated addresses with base offset

v4 (Single-File Format) - 2 files
    Used by: Flash.pac, RPG.pac
    
    Key identifier: Single file with filename at byte 5
    
    Structure:
        - Bytes 0-4: Unknown header
        - Bytes 5+: Null-terminated filename
        - Variable offset: Count=1 (4 bytes)
        - Variable offset: File size (4 bytes)
        - File data starts at 0x100

v6 (Length-Prefix Format) - 1 file
    Used by: cpuduel.pac
    
    Key identifier: File count at offset 0x41
    
    Structure:
        - Bytes 0-2: Unknown header
        - Bytes 3+: Length-prefixed filenames
            * Each: 1-byte length + 1-byte separator + name bytes
        - Byte 0x41: File count
        - Offset 0x48: File table (8-byte entries)
            * Bytes 0-2: Unknown/flags
            * Bytes 3-6: File size (little endian)
            * Bytes 7: Unknown/flags
        - File data starts at 0x200 with 0x200-byte alignment

Based on the comprehensive format detection from the original pac.py.
"""

import os
import sys
import math
import argparse
import logging
import tempfile
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

# Set up logger
logger = logging.getLogger('pac_new')
logger.setLevel(logging.INFO)


@dataclass
class PACFile:
    """Represents a file entry in a PAC archive."""
    name: bytes
    address: int
    size: int
    after: int = -1  # For v1 format files
    file_index: int = -1  # Index in file table for generating names
    
    def get_clean_name(self) -> str:
        """Get cleaned filename as string."""
        try:
            name_str = self.name.decode("shift-jis").split("\x00", 1)[0]
        except (UnicodeDecodeError, LookupError):
            name_str = self.name.decode("utf-8", errors="replace").split("\x00", 1)[0]
        
        # Remove non-printable and invalid filename characters
        name_str = ''.join(char for char in name_str if char.isprintable())
        invalid_chars = '<>:"/\\|?*'
        name_str = ''.join(char for char in name_str if char not in invalid_chars)
        
        # Handle empty names or names that are just whitespace
        if not name_str or not name_str.strip():
            # Use file_index if available for consistent naming
            if self.file_index >= 0:
                name_str = f"unnamed_file_{self.file_index:03d}.bin"
            else:
                name_str = f"unnamed_file_{abs(hash(self.name)):08x}.bin"
        
        return name_str


@dataclass
class PACArchive:
    """Represents a complete PAC archive."""
    data: bytes
    files: List[PACFile]
    file_names_beginning: int
    file_names: bytes
    file_data_beginning_address: int
    third: int  # Offset marker used for repacking
    format_name: str
    
    def get_files_sorted_by_address(self) -> List[PACFile]:
        """Return files sorted by their address (required for repacking)."""
        return sorted(self.files, key=lambda f: f.address)


def extract_filenames_by_extension(data: bytes, header_limit: int, extension_list: List[bytes]) -> List[bytes]:
    """Extract filenames from header by scanning for known extensions and working backwards."""
    tableOfFileNames = []
    
    for ext in extension_list:
        pos = 0
        while pos < header_limit:
            idx = data.find(ext, pos, header_limit)
            if idx == -1:
                break
            # Work backwards to find start of filename
            start = idx
            while start > 0:
                c = data[start - 1]
                if ((c >= ord('a') and c <= ord('z')) or
                    (c >= ord('A') and c <= ord('Z')) or
                    (c >= ord('0') and c <= ord('9')) or
                    c == ord('_') or c == ord('.')):
                    start -= 1
                else:
                    break
            
            filename = data[start:idx + len(ext)]
            
            # Fix: detect flag bytes that look like letters
            if len(filename) > 2:
                first = filename[0]
                second = filename[1]
                third = filename[2] if len(filename) > 2 else 0
                if ((first >= ord('a') and first <= ord('z')) or (first >= ord('A') and first <= ord('Z'))):
                    if ((second >= ord('a') and second <= ord('z')) or (second >= ord('A') and second <= ord('Z'))):
                        if third == ord('_'):
                            filename = filename[1:]
            
            # Validate filename
            if len(filename) > 0 and len(filename) < 80:
                first_char = filename[0]
                if ((first_char >= ord('a') and first_char <= ord('z')) or
                    (first_char >= ord('A') and first_char <= ord('Z'))):
                    tableOfFileNames.append(filename)
            
            pos = idx + 1
    
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for name in tableOfFileNames:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    
    return unique


def parse_format_v3(data: bytes, input_pac_file: str) -> Optional[PACArchive]:
    """
    Parse v3 (Graphics Format) - Complex format for graphics/UI files.
    
    Used by: CharaMake.pac, Closet.pac, WiFi.pac, D_race_result.pac, Getpack.pac,
             FriendMenu.pac, FreeDuel.pac, and 4 others (11 total).
    
    File Structure:
        Header (0x0-0x3):
            - Usually starts with 00 00
            - Next 2 bytes vary by file (e.g., 01 0e for CharaMake)
            - Not a reliable size indicator
        
        Filename Section (0x4-variable):
            - Filenames scattered throughout header area (up to 0x800)
            - Various encodings (Shift-JIS, UTF-8, ASCII)
            - Extensions identify graphics format:
                * lz5bg  - Compressed background graphics
                * lznanr - Compressed animation
                * lzncer - Compressed cell
                * lzncgr - Compressed character graphics
                * lznclr - Compressed color/palette
                * lznsbr - Compressed screen
                * lznmar - Compressed map
                * lznsbca - Compressed screen animation
                * lzchip - Compressed chip graphics
            - Some filenames may have flag bytes that complicate parsing
        
        File Table:
            - Located at aligned offset: 0x200, 0x400, 0x600, or 0x800
            - Count location varies:
                * 4-byte count at table offset, entries at +8 or +12
                * 2-byte count at offset+2, entries at +4 or +8
            - Entry format (8 bytes): Can be either:
                * [4-byte size][4-byte address] OR
                * [4-byte address][4-byte size]
            - Address has base offset: 0, 0x200, 0x400, 0x800, 0x1000, or 0x2000
        
        File Data:
            - Located at address = (table_entry_address + base_offset)
            - Compressed graphics data
    
    Detection Strategy:
        - File must start with 00 00
        - Must find at least one graphics extension in header
        - Searches all alignment combinations for valid file table
        - Validates entries point to valid data within file bounds
        - Uses lenient count matching (±20 or extracted_count tolerance)
        - Generates placeholder names for files that couldn't be extracted
    
    Special Handling:
        - Extracted filename count may not match table count
        - Parser is lenient and fills gaps with generated names
        - Preserves exact file table structure during repack
    
    Returns:
        PACArchive if format matches, None otherwise
    """
    logger.debug("Trying v3 (graphics) format parser...")
    tableOfFileNames = []
    tableOfFiles = []
    
    # Known file extensions for this format
    extension_list = [b'lz5bg', b'lznanr', b'lzncer', b'lzncgr', b'lznclr', b'lznsbr', b'lznmar', b'lznsbca', b'lzchip']
    
    # Check if header looks like v3 format - first 2 bytes usually 00 00
    if len(data) < 0x200:
        logger.debug("  v3: File too small (< 0x200 bytes)")
        return None
    if data[0] != 0x00 or data[1] != 0x00:
        logger.debug(f"  v3: Header doesn't start with 00 00 (got {data[0]:02x} {data[1]:02x})")
        return None
    
    header_limit = min(0x800, len(data))
    
    # Find filenames by scanning for known extensions - this is the key identifier
    tableOfFileNames = extract_filenames_by_extension(data, header_limit, extension_list)
    logger.debug(f"  v3: Found {len(tableOfFileNames)} graphics filenames")
    
    if not tableOfFileNames:
        logger.debug("  v3: No graphics extensions found, not a v3 file")
        return None  # Not a graphics format file
    
    # Find file table - look for aligned section with file count header
    # NOTE: The actual file count in the table may differ from extracted filenames
    # because some filenames may be malformed or have flag bytes we can't parse correctly.
    # We'll try to match the table count if it's close to our extracted count.
    table_offset = None
    entry_start = None
    extracted_count = len(tableOfFileNames)
    actual_file_count = None  # Will be set when we find the table
    entry_format = "size_addr"
    base_offset = 0
    
    for offset in range(0x200, 0x1000, 0x200):
        if offset + 20 > len(data):
            break
        
        count_4byte = int.from_bytes(data[offset:offset+4], 'little')
        count_2byte_at_2 = int.from_bytes(data[offset+2:offset+4], 'little')
        
        # Try both count locations with appropriate entry start offsets
        count_and_start_list = [
            (count_4byte, [offset + 12, offset + 8]),  # 4-byte count: entries at +12 or +8
            (count_2byte_at_2, [offset + 8, offset + 4]),  # 2-byte count at +2: entries at +8 or +4
        ]
        
        for count, try_starts in count_and_start_list:
            # Be lenient: allow count to be reasonable and somewhat close to extracted count
            # This handles cases where filename extraction misses some due to encoding issues
            # or includes duplicates/flag-byte variations
            if count < 1 or count > 1000 or abs(count - extracted_count) > max(20, extracted_count):
                continue
            
            for try_start in try_starts:
                for try_base in [0, 0x200, 0x400, 0x800, 0x1000, 0x2000]:
                    # Try format: (size, addr) with base offset
                    test_size = int.from_bytes(data[try_start:try_start+4], 'little')
                    test_addr_rel = int.from_bytes(data[try_start+4:try_start+8], 'little')
                    test_addr = test_addr_rel + try_base
                    if 0 < test_size < len(data) and 0 < test_addr < len(data) and test_addr + test_size <= len(data):
                        # Valid entry found - use actual count from table
                        table_offset = offset
                        entry_start = try_start
                        entry_format = "size_addr"
                        base_offset = try_base
                        actual_file_count = count
                        break
                    
                    # Try format: (addr, size) with base offset
                    test_addr_rel = int.from_bytes(data[try_start:try_start+4], 'little')
                    test_size = int.from_bytes(data[try_start+4:try_start+8], 'little')
                    test_addr = test_addr_rel + try_base
                    if 0 < test_size < len(data) and 0 < test_addr < len(data) and test_addr + test_size <= len(data):
                        # Valid entry found - use actual count from table
                        table_offset = offset
                        entry_start = try_start
                        entry_format = "addr_size"
                        base_offset = try_base
                        actual_file_count = count
                        break
                if table_offset is not None:
                    break
            if table_offset is not None:
                break
        if table_offset is not None:
            break
    
    if table_offset is None or actual_file_count is None:
        logger.debug("  v3: Could not find valid file table")
        return None
    
    logger.debug(f"  v3: Found file table at {hex(table_offset)}, entry_start={hex(entry_start)}, count={actual_file_count}, base_offset={hex(base_offset)}")
    
    # Parse file table entries using actual count from table
    # If we have fewer extracted filenames than actual files, generate dummy names
    while len(tableOfFileNames) < actual_file_count:
        # Generate placeholder name for files we couldn't extract
        idx = len(tableOfFileNames)
        ext = extension_list[idx % len(extension_list)]
        tableOfFileNames.append(f"file_{idx:03d}.{ext.decode('latin1')}".encode('latin1'))
    
    numFiles = actual_file_count
    
    for idx in range(numFiles):
        entry_offset = entry_start + (idx * 8)
        if entry_offset + 8 > len(data):
            break
        
        if entry_format == "size_addr":
            size = int.from_bytes(data[entry_offset:entry_offset+4], 'little')
            addr_rel = int.from_bytes(data[entry_offset+4:entry_offset+8], 'little')
            addr = addr_rel + base_offset
        else:
            addr_rel = int.from_bytes(data[entry_offset:entry_offset+4], 'little')
            size = int.from_bytes(data[entry_offset+4:entry_offset+8], 'little')
            addr = addr_rel + base_offset
        
        if size > 0 and addr + size <= len(data):
            pac_file = PACFile(name=tableOfFileNames[idx], address=addr, size=size)
            tableOfFiles.append(pac_file)
        else:
            pac_file = PACFile(name=tableOfFileNames[idx], address=addr, size=0)
            tableOfFiles.append(pac_file)
    
    if len(tableOfFileNames) != len(tableOfFiles):
        minCount = min(len(tableOfFileNames), len(tableOfFiles))
        tableOfFileNames = tableOfFileNames[:minCount]
        tableOfFiles = tableOfFiles[:minCount]
    
    # Convert to PACFile objects with correct names
    for i, file_entry in enumerate(tableOfFiles):
        file_entry.name = tableOfFileNames[i]
    
    fileNamesBeginning = 4
    fileNames = data[table_offset:entry_start + numFiles * 8]
    fileDataBeginningAddress = 0
    third = table_offset
    
    logger.info(f"  ✓ v3 format detected: {len(tableOfFiles)} files parsed")
    
    return PACArchive(
        data=data,
        files=tableOfFiles,
        file_names_beginning=fileNamesBeginning,
        file_names=fileNames,
        file_data_beginning_address=fileDataBeginningAddress,
        third=third,
        format_name="v3_graphics"
    )


def parse_format_v1(data: bytes, input_pac_file: str) -> Optional[PACArchive]:
    """
    Parse v1 (Marker Format) - Original PAC format with 0xFFFF boundary marker.
    
    Used by: bin.pac, deck.pac, bin2.pac, Common.pac, tutorial.pac, trunk.pac,
             effect.pac, janken.pac, duel2d.pac, Structure.pac, RACE.pac, and 16 others.
    
    File Structure:
        Header Section:
            - Filenames separated by linebreak bytes (0x0A-0x18)
            - For graphics files: uses extension-based extraction
            - For other files: linebreak-delimited names
            - All filenames must contain a period (.)
        
        Marker:
            - 0xFFFF on 16-byte aligned boundary
            - Marks end of header, start of file table
        
        File Table:
            - 8-byte entries aligned to 8-byte boundaries
            - Entry format: [4-byte address][4-byte size]
            - Address is relative to file data section start
            - Optional 8-byte 'after' field follows some entries
        
        Padding:
            - Zero-filled padding to align file data section
            - Typically aligns to 16-byte boundary
        
        File Data:
            - Sequential file contents at calculated addresses
            - Addresses from file table + file_data_beginning_address
    
    Detection:
        - Searches for 0xFFFF marker on even offsets
        - Marker must be on 16-byte boundary
        - Validates filename count matches file table entries
    
    Returns:
        PACArchive if format matches, None otherwise
    """
    logger.debug("Trying v1 (marker) format parser...")
    header = 0
    fileNamesBeginning = 0
    fileNames = 0
    fileDataBeginningAddress = 0
    third = 0
    lineBreakBytes = [0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18]
    tableOfFileNames = []
    tableOfFiles = []

    # Find 0xFFFF marker
    for i in range(0, len(data)):
        if ((i / 2) == (math.floor(i / 2))):
            if (data[i] & 0xFF == 0xFF) and (data[i + 1] & 0xFF == 0xFF):
                j = i - (i % 16)
                header = data[0:j]
                fileNamesBeginning = j
                break

    if header == 0:
        logger.debug("  v1: No 0xFFFF marker found")
        return None
    
    logger.debug(f"  v1: Found 0xFFFF marker at {hex(fileNamesBeginning)}")

    for i in range(fileNamesBeginning, len(data)):
        if ((i % 16) == (fileNamesBeginning % 16)):
            currentLine = data[i:(i + 8)]
            if (int.from_bytes(currentLine, "little") == 0):
                fileNames = data[fileNamesBeginning:i]
                third = i
                break

    # File data section starts at the next 0x200-byte (512-byte) boundary after
    # the file table.  The original scan-for-first-non-zero approach fails when
    # the first file's data starts with null bytes (e.g. card_desc_e.bin in
    # WC2008/SA bin2.pac has an 8-byte zero header), causing the base address to
    # overshoot by 0x10 and every subsequent file address to be off-by-0x10.
    fileDataBeginningAddress = ((third + 0x1FF) // 0x200) * 0x200

    # Check if this is a graphics file
    graphics_extensions = [b'lz5bg', b'lznanr', b'lzncer', b'lzncgr', b'lznclr', b'lznsbr', b'lznmar', b'lznsbca', b'lzchip']
    has_graphics = any(ext in header for ext in graphics_extensions)
    
    if has_graphics:
        tableOfFileNames = extract_filenames_by_extension(header, len(header), graphics_extensions)
    else:
        # Use lineBreakBytes parsing
        beginningOfWord = 0
        check = 0
        for i in range(0, len(header)):
            if (check == 1):
                check = 0
            else:
                currentByte = header[i]
                for j in range(15):
                    if (currentByte == lineBreakBytes[j]):
                        tableOfFileNames.append(header[beginningOfWord:i])
                        beginningOfWord = i + 2
                        check = 1

        finalCharacter = len(header) - 1
        while (header[finalCharacter - 3] & 0xFF == 0x00):
            finalCharacter = finalCharacter - 1
        tableOfFileNames.append(header[beginningOfWord:finalCharacter])

        temp = tableOfFileNames.copy()
        for k in temp:
            checkP = 0
            for j in range(len(k)):
                if (k[j] == 46):
                    checkP = 1
            if (checkP != 1):
                while (tableOfFileNames.count(k) > 0):
                    tableOfFileNames.remove(k)

    # Parse file table
    for i in range(8, len(fileNames)):
        if ((i % 8) == 0) and ((i + 8) <= len(fileNames)):
            if len(tableOfFiles) >= len(tableOfFileNames):
                break
            byteSlice = fileNames[i:(i + 8)]
            fileSize = int.from_bytes(byteSlice[4:8], "little")
            if (fileSize != 0):
                address = int.from_bytes(byteSlice[0:4], "little")
                after = -1
                if ((i + 16) <= len(fileNames)) and (int.from_bytes(fileNames[(i + 12):(i + 16)], "little") == 0):
                    after = (int.from_bytes(fileNames[(i + 8):(i + 16)], "little"))
                pac_file = PACFile(
                    name=tableOfFileNames[len(tableOfFiles)],
                    address=fileDataBeginningAddress + address,
                    size=fileSize,
                    after=after,
                    file_index=len(tableOfFiles)
                )
                tableOfFiles.append(pac_file)

    if len(tableOfFileNames) != len(tableOfFiles):
        logger.debug(f"  v1: Mismatch - {len(tableOfFileNames)} names vs {len(tableOfFiles)} files")
        return None
    
    logger.info(f"  ✓ v1 format detected: {len(tableOfFiles)} files parsed")
    
    return PACArchive(
        data=data,
        files=tableOfFiles,
        file_names_beginning=fileNamesBeginning,
        file_names=fileNames,
        file_data_beginning_address=fileDataBeginningAddress,
        third=third,
        format_name="v1_marker"
    )


def parse_format_v2(data: bytes, input_pac_file: str) -> Optional[PACArchive]:
    """
    Parse v2 (Simple Format) - Puzzle format with .ydq/.ydc extensions.
    
    Used by: puzzle.pac
    
    File Structure:
        Header (0x0-0x100):
            - Contains filenames with .ydq (deck) and .ydc (card) extensions
            - Filenames are ASCII, match regex: [a-zA-Z0-9_]+\\.yd[cq]
            - Examples: "Ynull.ydq", "kwrgp01_bin.ydq", "lghost_rd.ydq"
        
        File Table Header:
            - Located between 0x100-0x400 on 8-byte boundary
            - Format: [4-byte count][4-byte padding (0x00000000)]
            - Count must match number of extracted filenames
        
        File Table Entries (8 bytes each):
            - Byte 0-1: Unknown/flags
            - Byte 2-3: File size (16-bit little endian)
            - Byte 4-5: Unknown/flags
            - Byte 6-7: File offset (16-bit little endian)
            - If offset is 0 and not first file: use calculated aligned offset
        
        File Data:
            - Starts at 0x200
            - Files are aligned to 0x200-byte boundaries
            - Padding between files preserved during repack
    
    Detection:
        - Searches for .ydq/.ydc filenames using regex
        - Locates file table by matching count with filename count
        - Validates at least one valid file entry exists
    
    Returns:
        PACArchive if format matches, None otherwise
    """
    import re
    
    logger.debug("Trying v2 (simple) format parser...")
    
    if len(data) < 0x200:
        logger.debug("  v2: File too small")
        return None
    
    tableOfFileNames = []
    tableOfFiles = []
    
    # Extract filenames using regex - puzzle.pac uses .ydq and .ydc extensions
    filename_matches = list(re.finditer(rb'[a-zA-Z0-9_]+\.yd[cq]', data[:0x1000]))
    for m in filename_matches:
        tableOfFileNames.append(m.group())
    
    if not tableOfFileNames:
        logger.debug("  v2: No .ydq/.ydc filenames found")
        return None
    
    logger.debug(f"  v2: Found {len(tableOfFileNames)} .ydq/.ydc filenames")
    
    numFiles = len(tableOfFileNames)
    fileTableOffset = 0
    
    # Search for file count in likely locations (after filename section)
    for search_start in range(0x100, min(0x400, len(data) - 8), 8):
        count = int.from_bytes(data[search_start:search_start+4], 'little')
        next_4 = int.from_bytes(data[search_start+4:search_start+8], 'little')
        if count == numFiles and next_4 == 0:
            fileTableOffset = search_start
            break
    
    if fileTableOffset == 0:
        # Fallback: find first non-zero aligned data after a run of zeros
        in_zeros = False
        for i in range(0x100, min(0x1000, len(data) - 8), 8):
            chunk = data[i:i+8]
            if chunk == b'\x00' * 8:
                in_zeros = True
            elif in_zeros:
                count = int.from_bytes(chunk[0:4], 'little')
                if count == numFiles:
                    fileTableOffset = i
                    break
                in_zeros = False
    
    if fileTableOffset == 0:
        logger.debug("  v2: Could not find file table offset")
        return None
    
    logger.debug(f"  v2: Found file table at {hex(fileTableOffset)}")
    
    # Parse file table entries starting after the 8-byte header (count + padding)
    tableStart = fileTableOffset + 8
    lastFileEnd = 0x200
    
    for idx in range(numFiles):
        entryOffset = tableStart + (idx * 8)
        if entryOffset + 8 > len(data):
            break
        entry = data[entryOffset:entryOffset+8]
        fileSize = int.from_bytes(entry[2:4], 'little')
        fileOffset = int.from_bytes(entry[6:8], 'little')
        
        if fileSize > 0:
            if fileOffset == 0 and tableOfFiles:
                fileOffset = lastFileEnd
            
            if fileOffset > 0:
                pac_file = PACFile(
                    name=tableOfFileNames[idx],
                    address=fileOffset,
                    size=fileSize,
                    after=-1
                )
                tableOfFiles.append(pac_file)
                lastFileEnd = ((fileOffset + fileSize + 0x1FF) // 0x200) * 0x200
    
    if len(tableOfFileNames) != len(tableOfFiles):
        minCount = min(len(tableOfFileNames), len(tableOfFiles))
        tableOfFileNames = tableOfFileNames[:minCount]
        tableOfFiles = tableOfFiles[:minCount]
    
    if not tableOfFiles:
        logger.debug("  v2: No valid files parsed")
        return None
    
    logger.info(f"  ✓ v2 format detected: {len(tableOfFiles)} files parsed")
    
    fileNames = data[fileTableOffset:tableStart + numFiles * 8]
    
    return PACArchive(
        data=data,
        files=tableOfFiles,
        file_names_beginning=4,
        file_names=fileNames,
        file_data_beginning_address=0x200,
        third=fileTableOffset,
        format_name="v2_simple"
    )


def parse_format_v4(data: bytes, input_pac_file: str) -> Optional[PACArchive]:
    """
    Parse v4 (Single-File Format) - Simplified format containing exactly one file.
    
    Used by: Flash.pac, RPG.pac
    
    File Structure:
        Header (bytes 0-4):
            - Unknown/magic bytes (not validated)
        
        Filename (byte 5+):
            - Null-terminated ASCII filename
            - Located at byte 5
            - Searched up to byte 64
            - Example: "FLogo.lz5bg" in Flash.pac
        
        Count Field:
            - Value: 0x00000001 (1 file)
            - Located after filename, before byte 64
            - Searched at each byte offset
        
        Size Field:
            - 4-byte little endian integer
            - Located 4-20 bytes after count field
            - Must be > 0 and < (file_size - 0x100)
        
        File Data:
            - Starts at fixed offset: 0x100
            - Contains single file of specified size
            - Usually compressed graphics data
    
    Detection:
        - File must be at least 0x30 bytes
        - Must find null-terminated filename at byte 5
        - Must find count=1 before byte 64
        - Must find valid size field within next 20 bytes
        - File data at 0x100 must not exceed archive bounds
    
    Returns:
        PACArchive with single file if format matches, None otherwise
    """
    logger.debug("Trying v4 (single-file) format parser...")
    
    if len(data) < 0x30:
        logger.debug("  v4: File too small")
        return None
    
    # Extract filename starting at byte 5
    null_idx = data.find(b'\x00', 5, 64)
    if null_idx < 5:
        return None
    
    filename = data[5:null_idx]
    if len(filename) == 0:
        return None
    
    # Look for count=1 after filename
    count_pos = -1
    for pos in range(null_idx, min(64, len(data)), 1):
        if pos + 4 <= len(data) and int.from_bytes(data[pos:pos+4], 'little') == 1:
            count_pos = pos
            break
    
    if count_pos < 0:
        return None
    
    # Size should be a few bytes after count
    file_size = 0
    for size_offset in range(count_pos + 4, min(count_pos + 20, len(data)), 1):
        if size_offset + 4 <= len(data):
            potential_size = int.from_bytes(data[size_offset:size_offset+4], 'little')
            if potential_size > 0 and potential_size <= len(data) - 0x100:
                file_size = potential_size
                break
    
    if file_size == 0:
        return None
    
    # File data starts at 0x100
    file_addr = 0x100
    if file_addr + file_size > len(data):
        logger.debug("  v4: File data exceeds archive size")
        return None
    
    logger.info(f"  ✓ v4 format detected: 1 file ({filename.decode('latin1', errors='replace')}, {file_size} bytes)")
    
    pac_file = PACFile(name=filename, address=file_addr, size=file_size, after=-1)
    
    fileNames = data[count_pos:count_pos+16]
    
    return PACArchive(
        data=data,
        files=[pac_file],
        file_names_beginning=5,
        file_names=fileNames,
        file_data_beginning_address=0,
        third=count_pos,
        format_name="v4_single_file"
    )


def parse_format_v6(data: bytes, input_pac_file: str) -> Optional[PACArchive]:
    """
    Parse v6 (Length-Prefix Format) - Format with length-prefixed filenames.
    
    Used by: cpuduel.pac
    
    File Structure:
        Header (bytes 0-2):
            - Unknown/magic bytes
        
        Filename Section (bytes 3-0x40):
            - Each filename is length-prefixed:
                * Byte 0: Length of filename (n)
                * Byte 1: Separator/unknown
                * Bytes 2-(n+1): Filename bytes
            - Multiple filenames packed sequentially
            - Section ends before byte 0x41
        
        File Count (byte 0x41):
            - Single byte containing number of files
            - Must be 1-50
            - Acts as key identifier for this format
        
        File Table (offset 0x48):
            - 8-byte entries for each file
            - Entry format:
                * Bytes 0-2: Unknown/flags
                * Bytes 3-6: File size (32-bit little endian)
                * Byte 7: Unknown/flags
            - No explicit address field
        
        File Data:
            - Starts at 0x200
            - Files aligned to 0x200-byte (512-byte) boundaries
            - Addresses calculated sequentially:
                * File 0: 0x200
                * File 1: align_up(0x200 + size_0, 0x200)
                * File n: align_up(prev_addr + prev_size, 0x200)
    
    Detection:
        - File must be at least 0x200 bytes
        - Byte 0x41 must be 1-50 (file count)
        - Must successfully parse that many length-prefixed names
        - All files must fit within archive bounds with alignment
    
    Returns:
        PACArchive if format matches, None otherwise
    """
    logger.debug("Trying v6 (length-prefix) format parser...")
    
    if len(data) < 0x200:
        logger.debug("  v6: File too small")
        return None
    
    # Check characteristic: file count at 0x41
    if data[0x41] == 0 or data[0x41] > 50:
        return None
    
    file_count = data[0x41]
    
    # Parse filenames starting at byte 3
    filenames = []
    pos = 3
    while pos < 0x40 and len(filenames) < file_count:
        length = data[pos]
        if length == 0 or pos + 2 + length > 0x48:
            break
        name = data[pos + 2:pos + 2 + length]
        filenames.append(name)
        pos += 2 + length
    
    if len(filenames) != file_count:
        return None
    
    # Parse file table at 0x48
    files = []
    addr = 0x200
    for i in range(file_count):
        entry_off = 0x48 + i * 8
        if entry_off + 8 > len(data):
            break
        
        size = int.from_bytes(data[entry_off+3:entry_off+7], 'little')
        if size > 0 and addr + size <= len(data):
            files.append(PACFile(name=filenames[i], address=addr, size=size))
            addr = ((addr + size + 0x1ff) // 0x200) * 0x200
    
    if len(files) == file_count:
        logger.info(f"  ✓ v6 format detected: {file_count} files parsed")
        fileNames = data[0x48:0x48 + file_count * 8]
        return PACArchive(
            data=data,
            files=files,
            file_names_beginning=0x48,
            file_names=fileNames,
            file_data_beginning_address=0x200,
            third=0x48,
            format_name="v6_length_prefix"
        )
    
    return None


def parse_pac(data: bytes, pac_path: str) -> Optional[PACArchive]:
    """
    Auto-detect and parse a PAC file.
    Tries different format parsers in priority order.
    """
    # ndspy may hand us a bytearray; coerce to bytes so that slices are
    # hashable and behave consistently across all format parsers.
    if isinstance(data, (bytearray, memoryview)):
        data = bytes(data)

    logger.info(f"Parsing {os.path.basename(pac_path)} ({len(data):,} bytes)...")
    
    # Try formats in priority order
    # v3 (graphics) must come before v1 because graphics files can have 0xFFFF markers in data
    parsers = [
        ("v4", parse_format_v4),
        ("v6", parse_format_v6),
        ("v3", parse_format_v3),  # Graphics files - check before v1
        ("v1", parse_format_v1),  # May have 0xFFFF markers
        ("v2", parse_format_v2),
    ]
    
    for name, parser in parsers:
        result = parser(data, pac_path)
        if result:
            return result
    
    logger.error(f"Failed to detect format for {os.path.basename(pac_path)}")
    return None


def unpack_pac(pac_path: str, output_dir: str) -> int:
    """Unpack a PAC archive."""
    logger.info(f"\n{'='*70}")
    logger.info(f"UNPACKING: {pac_path}")
    logger.info(f"{'='*70}")
    
    with open(pac_path, 'rb') as f:
        data = f.read()
    
    archive = parse_pac(data, pac_path)
    
    if not archive:
        print(f"Error: Could not detect format for {pac_path}")
        logger.error("Failed to parse PAC file")
        return 1
    
    print(f"Detected format: {archive.format_name}")
    print(f"Files found: {len(archive.files)}")
    logger.info(f"Format: {archive.format_name}")
    logger.info(f"Files to extract: {len(archive.files)}")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.debug(f"Created output directory: {output_dir}")
    
    for idx, pac_file in enumerate(archive.files, 1):
        clean_name = pac_file.get_clean_name()
        output_path = os.path.join(output_dir, clean_name)
        
        logger.debug(f"  [{idx}/{len(archive.files)}] Extracting {clean_name} (offset={hex(pac_file.address)}, size={pac_file.size} bytes)")
        
        with open(output_path, 'wb') as f:
            f.write(data[pac_file.address:pac_file.address + pac_file.size])
    
    print(f"Unpacked {len(archive.files)} files to {output_dir}")
    logger.info(f"\n✓ Successfully unpacked {len(archive.files)} files to {output_dir}")
    return 0


def build_modified_pac(
    pac_data: bytes,
    pac_path: str,
    replacements_by_index: dict,
) -> bytes:
    """Apply inner-file replacements to a PAC blob, preserving byte layout.

    This is the single canonical PAC writer. It mirrors the strategy validated
    by the Dash editor: prefer byte-faithful in-place edits, and only fall back
    to a full repack when an edit changes a file's size in a format that allows
    relocation.

    Args:
        pac_data: The original PAC archive bytes.
        pac_path: Path of the PAC (used for format detection and error messages).
        replacements_by_index: Mapping of file index (int) -> replacement bytes.

    Returns:
        Modified PAC archive as bytes. Returns *pac_data* unchanged when
        *replacements_by_index* is empty.

    Raises:
        ValueError: If the PAC cannot be parsed, an index is out of range, a
            v2 replacement is larger than its pre-allocated block, or two inner
            files share a clean name during a size-changing repack.
    """
    if not replacements_by_index:
        return pac_data

    archive = parse_pac(pac_data, pac_path)
    if not archive:
        raise ValueError(f"Could not parse PAC format: {pac_path}")

    for index in replacements_by_index:
        if index < 0 or index >= len(archive.files):
            raise ValueError(f"Invalid PAC index {index} for {pac_path}")

    # Fast path: all replacement sizes match original entry sizes -> in-place patch
    same_size_only = all(
        len(replacement) == archive.files[index].size
        for index, replacement in replacements_by_index.items()
    )

    if same_size_only:
        patched = bytearray(pac_data)
        for index, replacement in replacements_by_index.items():
            pac_file = archive.files[index]
            patched[pac_file.address:pac_file.address + pac_file.size] = replacement
        return bytes(patched)

    # v2 (puzzle.pac): repack_pac writes wrong file-table entries for this format.
    # Use in-place patching: update size field + overwrite within the pre-allocated block.
    if archive.format_name == "v2_simple":
        sorted_files = sorted(archive.files, key=lambda f: f.address)
        table_start = archive.third + 8
        patched = bytearray(pac_data)
        for index, replacement in replacements_by_index.items():
            pac_file = archive.files[index]
            target_in_sorted = next(
                i for i, f in enumerate(sorted_files)
                if f.get_clean_name() == pac_file.get_clean_name()
            )
            if target_in_sorted + 1 < len(sorted_files):
                block_size = sorted_files[target_in_sorted + 1].address - pac_file.address
            else:
                block_size = len(pac_data) - pac_file.address
            if len(replacement) > block_size:
                raise ValueError(
                    f"Replacement too large: {len(replacement):,} bytes exceeds "
                    f"{block_size}-byte block for {pac_file.get_clean_name()}"
                )
            entry_offset = table_start + index * 8
            patched[entry_offset + 2:entry_offset + 4] = len(replacement).to_bytes(2, "little")
            padded = replacement + bytes(block_size - len(replacement))
            patched[pac_file.address:pac_file.address + block_size] = padded
        return bytes(patched)

    # Repack path for size-changing edits (non-v2 formats)
    with tempfile.TemporaryDirectory(prefix="pac_stage_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        input_dir = tmp_root / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        pac_name = Path(pac_path).name or "archive.pac"
        original_pac_path = tmp_root / pac_name
        output_pac_path = tmp_root / f"repacked_{pac_name}"
        original_pac_path.write_bytes(pac_data)

        seen_names: set = set()
        for idx, pac_file in enumerate(archive.files):
            clean_name = pac_file.get_clean_name()
            if clean_name in seen_names:
                raise ValueError(f"Duplicate PAC internal filename: {clean_name}")
            seen_names.add(clean_name)

            entry_bytes = pac_data[pac_file.address:pac_file.address + pac_file.size]
            if idx in replacements_by_index:
                entry_bytes = replacements_by_index[idx]
            (input_dir / clean_name).write_bytes(entry_bytes)

        repack_result = repack_pac(str(input_dir), str(original_pac_path), str(output_pac_path))
        if repack_result != 0:
            raise ValueError(f"Failed to repack PAC {pac_path}")

        return output_pac_path.read_bytes()


def repack_pac(input_dir: str, original_pac: str, output_pac: str) -> int:
    """Repack a PAC archive maintaining original structure."""
    logger.info(f"\n{'='*70}")
    logger.info(f"REPACKING: {original_pac} -> {output_pac}")
    logger.info(f"{'='*70}")
    
    # Parse original PAC to get structure
    with open(original_pac, 'rb') as f:
        original_data = f.read()
    
    logger.info("Analyzing original PAC structure...")
    archive = parse_pac(original_data, original_pac)
    
    if not archive:
        print(f"Error: Could not parse original PAC {original_pac}")
        return 1
    
    # Use original file order from the PAC file table (CRITICAL for byte-perfect reproduction!)
    files_in_order = archive.files
    logger.info(f"Files to repack: {len(files_in_order)} (maintaining original order)")
    
    # Read replacement files
    logger.debug(f"Reading replacement files from {input_dir}...")
    new_file_data = {}
    for idx, pac_file in enumerate(files_in_order, 1):
        clean_name = pac_file.get_clean_name()
        file_path = os.path.join(input_dir, clean_name)
        
        if not os.path.exists(file_path):
            print(f"Error: Missing file {clean_name}")
            logger.error(f"Missing file: {clean_name}")
            return 1
        
        with open(file_path, 'rb') as f:
            new_file_data[clean_name] = f.read()
        
        logger.debug(f"  [{idx}/{len(files_in_order)}] Read {clean_name} ({len(new_file_data[clean_name])} bytes)")
    
    # Check if all files are identical (if so, we can just copy the original)
    logger.debug("Checking if files have changed...")
    all_same = True
    changed_files = []
    for pac_file in files_in_order:
        clean_name = pac_file.get_clean_name()
        new_data = new_file_data[clean_name]
        orig_data = original_data[pac_file.address:pac_file.address + pac_file.size]
        if new_data != orig_data:
            all_same = False
            changed_files.append(f"{clean_name} ({len(orig_data)} -> {len(new_data)} bytes)")
    
    if all_same:
        # Files unchanged, just copy original
        logger.info("No files changed - copying original PAC")
        with open(output_pac, 'wb') as f:
            f.write(original_data)
        print(f"Repacked {len(files_in_order)} files to {output_pac} (no changes)")
        logger.info(f"✓ Repacked {len(files_in_order)} files (no changes)")
        return 0
    
    logger.info(f"Files changed: {len(changed_files)}")
    print(f"\nChanged files ({len(changed_files)}):")
    for change in changed_files:
        print(f"  • {change}")
    print()
    
    # Build new PAC maintaining structure
    logger.info("Building new PAC file...")
    with open(output_pac, 'wb') as newPac:
        # Write header up to file names
        logger.debug(f"  Writing header (0x0 - {hex(archive.file_names_beginning)})")
        newPac.write(original_data[0:archive.file_names_beginning])
        
        # Write file names header (first 8 bytes)
        if len(archive.file_names) >= 8:
            logger.debug("  Writing file names header (8 bytes)")
            newPac.write(archive.file_names[0:8])
        
        # Calculate new addresses maintaining original file table order
        # The file table order stays the same, but we need to recalculate addresses
        # based on new file sizes
        logger.debug(f"  Writing file table ({len(files_in_order)} entries)...")
        
        # First pass: calculate where each file will be located
        # Files are laid out sequentially starting from first file's original address
        sorted_by_addr = sorted(files_in_order, key=lambda f: f.address)

        # Inner files sit on a fixed BOUNDARY (0x200 for v1 -- see the
        # fileDataBeginningAddress rounding in parse_format_v1), and the original
        # inter-file gaps are just zero padding sized to reach it. Preserving the GAP
        # LENGTH instead of the boundary leaves every later file misaligned as soon as
        # one file changes size: growing bin2.pac's card_desc_e.bin by 101 B put 90 of
        # its 99 inner files on ODD addresses, and card_indx_*.bin is a u32 table, so a
        # misaligned ARM load reads rotated garbage (this is the freeze
        # boggart_knight recorded when it appended a longer card name).
        # v1's boundary is 0x200 BY CONSTRUCTION -- parse_format_v1 computes
        # fileDataBeginningAddress as ((third + 0x1FF) // 0x200) * 0x200 -- so use it
        # flatly rather than deriving it from the input. Deriving would read a PAC that
        # a previous buggy repack had already knocked off its boundary as "this archive
        # is 1-byte aligned" and then tight-pack it, silently shrinking the archive.
        # Repacking such a PAC re-aligns it, which is a repair back toward stock.
        # Other formats keep whatever boundary their own layout shows.
        if archive.format_name == "v1_marker":
            align = 0x200
        else:
            align = 0x200
            while align > 1 and any(f.address % align for f in sorted_by_addr):
                align >>= 1
        logger.debug(f"  Inner-file boundary: {align:#x} ({archive.format_name})")

        file_to_new_addr = {}
        base = archive.file_data_beginning_address
        current_addr = sorted_by_addr[0].address - base

        for i, pac_file in enumerate(sorted_by_addr):
            clean_name = pac_file.get_clean_name()
            file_to_new_addr[clean_name] = current_addr
            current_addr += len(new_file_data[clean_name])
            if i + 1 < len(sorted_by_addr):
                # Pad up to the next boundary. Unchanged sizes reproduce the original
                # addresses exactly, because every original gap is < align.
                abs_addr = base + current_addr
                current_addr = ((abs_addr + align - 1) // align) * align - base
        
        # Second pass: write file table in ORIGINAL order
        for i, pac_file in enumerate(files_in_order):
            clean_name = pac_file.get_clean_name()
            new_addr = file_to_new_addr[clean_name]
            new_size = len(new_file_data[clean_name])
            
            # Write file table entry in original order
            newPac.write(new_addr.to_bytes(4, "little"))
            newPac.write(new_size.to_bytes(4, "little"))
            
            # Write 'after' field if present (v1 format)
            if pac_file.after != -1:
                newPac.write(pac_file.after.to_bytes(8, "little"))
        
        # Write remaining file names data
        if len(archive.file_names) > 0:
            endBit = len(archive.file_names) - (len(archive.file_names) % 8)
            if endBit < len(archive.file_names):
                logger.debug(f"  Writing remaining file names data ({len(archive.file_names) - endBit} bytes)")
                newPac.write(archive.file_names[endBit:len(archive.file_names)])
        
        # Write padding between file names and file data
        if archive.third < archive.file_data_beginning_address:
            padding_size = archive.file_data_beginning_address - archive.third
            logger.debug(f"  Writing padding ({padding_size} bytes)")
            newPac.write(original_data[archive.third:archive.file_data_beginning_address])
        
        # Write file data in address order (sorted)
        logger.debug(f"  Writing file data ({len(sorted_by_addr)} files)...")
        for i, pac_file in enumerate(sorted_by_addr):
            clean_name = pac_file.get_clean_name()
            currentFile = new_file_data[clean_name]
            
            # Write padding before file (if not first file), sized to land this file on
            # its NEW address. Reuses the original gap bytes when the length is
            # unchanged so an untouched PAC round-trips byte-for-byte; otherwise zeros,
            # which is what every v1 gap holds.
            if i > 0:
                prev_file = sorted_by_addr[i - 1]
                prev_name = prev_file.get_clean_name()
                pad_len = file_to_new_addr[clean_name] - (
                    file_to_new_addr[prev_name] + len(new_file_data[prev_name]))
                original_gap = original_data[prev_file.address + prev_file.size:pac_file.address]
                if pad_len > 0:
                    logger.debug(f"    [{i+1}/{len(sorted_by_addr)}] Writing inter-file padding ({pad_len} bytes)")
                    newPac.write(original_gap if len(original_gap) == pad_len else bytes(pad_len))
            
            # Write file data
            logger.debug(f"    [{i+1}/{len(sorted_by_addr)}] Writing {clean_name} ({len(currentFile)} bytes)")
            newPac.write(currentFile)
        
        # Write any trailing data after last file
        lastFile = sorted_by_addr[-1]
        trailing_start = lastFile.address + lastFile.size
        if trailing_start < len(original_data):
            trailing_bytes = len(original_data) - trailing_start
            logger.debug(f"  Writing trailing data ({trailing_bytes} bytes)")
            newPac.write(original_data[trailing_start:len(original_data)])
    
    final_size = os.path.getsize(output_pac)
    print(f"Repacked {len(files_in_order)} files to {output_pac}")
    if changed_files:
        print("\nSummary:")
        print(f"  Files modified: {len(changed_files)}/{len(files_in_order)}")
        print(f"  Original size:  {len(original_data):,} bytes")
        print(f"  New size:       {final_size:,} bytes")
        print(f"  Difference:     {final_size - len(original_data):+,} bytes")
    logger.info(f"\n✓ Successfully repacked {len(files_in_order)} files")
    logger.info(f"  Original size: {len(original_data):,} bytes")
    logger.info(f"  New size: {final_size:,} bytes")
    logger.info(f"  Difference: {final_size - len(original_data):+,} bytes")
    return 0


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python pac_new.py <unpack|repack> [args]")
        return 1
    
    command = sys.argv[1]
    sys.argv.pop(1)
    
    if command == "unpack":
        parser = argparse.ArgumentParser(description="Unpack a PAC file")
        parser.add_argument("input_pac_file", help="Path to the input PAC file")
        parser.add_argument("output_directory", help="Directory to unpack files into")
        parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
        args = parser.parse_args()
        
        # Set up logging based on verbosity
        if args.verbose:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            logger.addHandler(handler)
        
        return unpack_pac(args.input_pac_file, args.output_directory)
    
    elif command == "repack":
        parser = argparse.ArgumentParser(description="Repack a PAC file")
        parser.add_argument("input_directory", help="Directory containing files to repack")
        parser.add_argument("input_pac_file", help="Path to the original PAC file")
        parser.add_argument("output_pac_file", help="Path to the output PAC file")
        parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
        args = parser.parse_args()
        
        # Set up logging based on verbosity
        if args.verbose:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            logger.addHandler(handler)
        
        return repack_pac(args.input_directory, args.input_pac_file, args.output_pac_file)
    
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
