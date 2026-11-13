import ndspy.code
import ndspy.codeCompression
import ndspy.rom
import argparse
import os

# Usage: uv run python -m otn_enhanced.rom.extract_all_overlays <path_to_rom> <output_directory>

def extract_all_overlays(rom: "ndspy.rom.NintendoDSRom", output_dir: str) -> None:
    """Extract all overlays from the ROM into *output_dir*."""
    ovs = rom.loadArm9Overlays()
    for k, overlay_data in ovs.items():
        overlay_filename = f"overlay_{k}.bin"
        output_path = os.path.join(output_dir, overlay_filename)
        with open(output_path, "wb") as f:
            f.write(overlay_data.data)
        print(f"Extracted overlay {k} to {output_path}")

def main(rom_path: str, output_dir: str) -> None:
    """Extract all overlays from the ROM at *rom_path* into *output_dir*."""
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    extract_all_overlays(rom, output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract all overlays from a Nintendo DS ROM into a directory."
    )
    parser.add_argument("rom_path", help="Path to the input ROM file.")
    parser.add_argument("output_dir", help="Directory to write extracted overlays.")
    args = parser.parse_args()
    main(args.rom_path, args.output_dir)