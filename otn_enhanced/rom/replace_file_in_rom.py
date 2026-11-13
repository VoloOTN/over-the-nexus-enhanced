"""Replace files in NDS ROM."""

import argparse
import sys
import ndspy.rom


def replace_file(args):
    """Execute the replace operation."""
    rom = ndspy.rom.NintendoDSRom.fromFile(args.rom_path)
    try:
        _ = rom.files[rom.filenames[args.file_path_in_rom]]
    except KeyError:
        print(f"File {args.file_path_in_rom} not found in ROM.")
        print(rom.filenames)
        return 1
    if args.input_file:
        with open(args.input_file, 'rb') as f:
            new_file_data = f.read()
        rom.setFileByName(args.file_path_in_rom, new_file_data)
        rom.saveToFile(args.rom_path)
        print(f"Replaced {args.file_path_in_rom} in {args.rom_path} with {args.input_file}")
        return 0


def main():
    """Main entry point for replace tool."""
    parser = argparse.ArgumentParser(description="Replace a file in an NDS ROM")
    parser.add_argument("--rom_path", help="Path to the NDS ROM file", required=True)
    parser.add_argument("--file_path_in_rom", help="Path of the file inside the ROM to extract/replace", required=True)
    parser.add_argument("--input_file", help="Path to the input file to replace with", required=True)
    args = parser.parse_args()
    return replace_file(args)


if __name__ == "__main__":
    sys.exit(main())