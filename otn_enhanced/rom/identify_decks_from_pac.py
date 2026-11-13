# Deck.pac File positions
import argparse
from otn_enhanced.rom.pac import parse_format_v1
from otn_enhanced.rom.konami_id_to_card_name import KONAMI_ID_TO_CARD_NAME
import json
import logging

# Set up logger
logger = logging.getLogger('identify_decks_from_pac')
logger.setLevel(logging.INFO)

def doTheThing(pac_path):
    with open(pac_path, 'rb') as f:
        data = f.read()
    pac_archive = parse_format_v1(data, pac_path)
    logger.debug(f"Parsed PAC archive with {len(pac_archive.files)} files.")
    deck_files = {}
    for file in pac_archive.files:
        # Fetch data according to address and size
        deck_name = file.name.decode('utf-8', errors='ignore').rstrip('\x00').strip().rstrip('\x19').strip()
        deck_data = data[file.address:file.address + file.size]
        # Get the 9th, 10th byte for main deck size
        main_deck_size = int.from_bytes(deck_data[8:10], byteorder='little')
        # From the 11th byte, read main_deck_size * 2 bytes for main deck card IDs
        main_deck_ids = []
        for i in range(main_deck_size):
            card_id = int.from_bytes(deck_data[10 + i*2:12 + i*2], byteorder='little')
            main_deck_ids.append(KONAMI_ID_TO_CARD_NAME.get(card_id))
        # After main deck, read 2 bytes for extra deck size
        extra_deck_size_offset = 10 + main_deck_size * 2
        extra_deck_size = int.from_bytes(deck_data[extra_deck_size_offset:extra_deck_size_offset + 2], byteorder='little')
        # From there, read extra_deck_size * 2 bytes for extra deck card IDs
        extra_deck_ids = []
        for i in range(extra_deck_size):
            card_id = int.from_bytes(deck_data[extra_deck_size_offset + 2 + i*2:extra_deck_size_offset + 4 + i*2], byteorder='little')
            # Map card konami ID to card name
            extra_deck_ids.append(KONAMI_ID_TO_CARD_NAME.get(card_id))
        # Convert header bytes to uint16 array
        header_uint16 = [int.from_bytes(deck_data[i:i+2], byteorder='little') for i in range(0, 8, 2)]
        deck_files[deck_name] = {
            "header": header_uint16,
            "main_deck_size": main_deck_size,
            "main_deck_names": main_deck_ids,
            "extra_deck_size": extra_deck_size,
            "extra_deck_names": extra_deck_ids,
        }
    return deck_files


def main():
    parser = argparse.ArgumentParser(
        description="Identify decks from Deck.pac in NDS ROM"
    )
    parser.add_argument("--deck_pac", help="Path to pac", required=True)
    parser.add_argument("--output_json_path", help="Path to output JSON file", required=False)
    args = parser.parse_args()
    deck_files = doTheThing(args.deck_pac)
    output_path = args.output_json_path if args.output_json_path else "deck_data.json"
    with open(output_path, "w") as json_file:
        json.dump(deck_files, json_file, indent=4)

if __name__ == "__main__":
    main()



