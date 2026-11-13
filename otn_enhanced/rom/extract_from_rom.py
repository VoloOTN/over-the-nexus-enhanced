"""Extract files from NDS ROM."""

import argparse
import sys
import ndspy.rom


def extract_file(args):
    """Execute the extraction operation."""
    rom = ndspy.rom.NintendoDSRom.fromFile(args.rom_path)
    try:
        target_file = rom.files[rom.filenames[args.file_path_in_rom]]
    except KeyError:
        print(f"File {args.file_path_in_rom} not found in ROM.")
        print(rom.filenames)
        return 1
    if args.output_file:
        with open(args.output_file, 'wb') as f:
            f.write(target_file)
        print(f"Extracted {args.file_path_in_rom} to {args.output_file}")
    return 0


def main():
    """Main entry point for extract tool."""
    parser = argparse.ArgumentParser(description="Extract a file in an NDS ROM")
    parser.add_argument("--rom_path", help="Path to the NDS ROM file", required=True)
    parser.add_argument("--file_path_in_rom", help="Path of the file inside the ROM to extract/replace", required=True)
    parser.add_argument("--output_file", help="Extract the specified file from the ROM")
    args = parser.parse_args()
    return extract_file(args)



if __name__ == "__main__":
    sys.exit(main())