import json
import requests
import time
from espn_api.football import League
from sleeper.api import DraftAPIClient
from sleeper.enum import Sport
from sleeper.model import Draft, DraftPick, PlayerDraftPick
from fantasy_football_id_mapper import load_player_ids_from_file, get_player_ids
from collections import defaultdict


def load_espn_config(file_path='espn_config.json'):
    try:
        with open(file_path, 'r') as file:
            config = json.load(file)
            return (
                config.get('ESPN_S2'),
                config.get('SWID'),
                config.get('LEAGUE_ID'),
                config.get('YEAR')
            )
    except FileNotFoundError:
        print(f"Configuration file not found: {file_path}")
        return None, None, None, None
    except json.JSONDecodeError:
        print(f"Invalid JSON in configuration file: {file_path}")
        return None, None, None, None


def get_sleeper_draft(draft_id):
    draft: Draft = DraftAPIClient.get_draft(draft_id=draft_id)
    draft_picks: list[PlayerDraftPick] = DraftAPIClient.get_player_draft_picks(
        draft_id=draft_id, sport=Sport.NFL
    )
    return draft, draft_picks


def map_sleeper_to_espn_players(draft_picks: list[PlayerDraftPick], league, player_map):
    draft_slot_picks = defaultdict(list)
    for pick in draft_picks:
        sleeper_player_id = str(pick.player_id)
        player_ids = get_player_ids(player_map, sleeper_player_id)
        espn_id = player_ids.get('espn_id')
        if espn_id:
            espn_player = league.player_info(playerId=int(espn_id))
            if espn_player:
                draft_slot_picks[pick.draft_slot].append(espn_player)
            else:
                print(f"ESPN player not found for Sleeper ID: {sleeper_player_id}")
        else:
            print(f"No ESPN ID found for Sleeper ID: {sleeper_player_id}")
    return dict(draft_slot_picks)


def import_draft_to_espn(draft: Draft, draft_slot_picks: dict, league):
    for draft_slot, players in draft_slot_picks.items():
        print(f"Draft Slot {draft_slot} selections:")
        for player in players:
            print(f"  - {player.name}")
        print()


def main():
    # Load ESPN configuration
    ESPN_S2, SWID, LEAGUE_ID, YEAR = load_espn_config()
    if not all([ESPN_S2, SWID, LEAGUE_ID, YEAR]):
        print("Failed to load ESPN configuration. Exiting.")
        return

    # Load player ID mappings from file
    player_map = load_player_ids_from_file()

    # Initialize the ESPN league
    league = League(league_id=LEAGUE_ID, year=YEAR, espn_s2=ESPN_S2, swid=SWID)

    # Get Sleeper draft ID from user
    sleeper_draft_id = input("Enter the Sleeper draft ID: ")

    # Fetch draft data from Sleeper
    draft, draft_picks = get_sleeper_draft(sleeper_draft_id)

    # Map Sleeper players to ESPN players
    draft_slot_picks = map_sleeper_to_espn_players(draft_picks, league, player_map)

    # Import draft results into ESPN
    # import_draft_to_espn(draft, draft_slot_picks, league)

    print("Import complete")


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.2f} seconds")
