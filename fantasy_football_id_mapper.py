import csv
from collections import defaultdict


def load_player_ids_from_file(file_path='player_ids.csv'):
    # Create a defaultdict to store player data
    player_map = defaultdict(dict)

    # Open and read the CSV file
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        csv_reader = csv.DictReader(file)

        # Iterate through each row in the CSV
        for row in csv_reader:
            sleeper_id = row['sleeper_id']
            if sleeper_id:  # Only process rows with a valid Sleeper ID
                # Store all other IDs for this player
                for key, value in row.items():
                    if key != 'sleeper_id' and value:
                        player_map[sleeper_id][key] = value

    return player_map


def get_player_ids(player_map, sleeper_id):
    return player_map.get(sleeper_id, {})


# Example usage
if __name__ == "__main__":
    # Load the player IDs from the CSV file
    player_map = load_player_ids_from_file()

    # Example lookup
    sleeper_id = '4034'  # Example Sleeper ID
    player_ids = get_player_ids(player_map, sleeper_id)
    print(f"Player IDs for Sleeper ID {sleeper_id}:")
    for platform, id_value in player_ids.items():
        print(f"{platform}: {id_value}")