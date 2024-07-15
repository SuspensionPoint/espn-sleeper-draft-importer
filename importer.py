import json
import time
import concurrent.futures
from urllib.parse import urlparse, parse_qs

import requests
from espn_api.football import League
from espn_api.requests.espn_requests import checkRequestStatus
from sleeper.api import DraftAPIClient
from sleeper.enum import Sport
from sleeper.model import Draft, PlayerDraftPick
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


def league_post(league: League, payload: dict = None, headers: dict = None, extend: str = ''):
    endpoint = league.espn_request.LEAGUE_ENDPOINT + extend
    r = requests.post(endpoint, json=payload, headers=headers, cookies=league.espn_request.cookies)
    checkRequestStatus(r.status_code)
    if league.espn_request.logger:
        league.espn_request.logger.log_request(endpoint=endpoint, params=payload, headers=headers, response=r.json())
    return r.json() if league.espn_request.year > 2017 else r.json()[0]


def extract_draft_id_from_url(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    if path_parts[1] == 'draft' and path_parts[2] == 'nfl':
        return path_parts[3]
    return None


def get_sleeper_draft(draft_id):
    draft: Draft = DraftAPIClient.get_draft(draft_id=draft_id)
    draft_picks: list[PlayerDraftPick] = DraftAPIClient.get_player_draft_picks(
        draft_id=draft_id, sport=Sport.NFL
    )
    return draft, draft_picks


def batch_get_espn_players(league, player_ids):
    batch_size = 50
    all_players = []
    for i in range(0, len(player_ids), batch_size):
        batch = player_ids[i:i + batch_size]
        players = league.player_info(playerId=batch)
        all_players.extend(players)
    return {player.playerId: player for player in all_players if player}


def map_sleeper_to_espn_players(draft_picks: list[PlayerDraftPick], league, player_map):
    draft_slot_picks = defaultdict(list)
    espn_ids = []
    sleeper_to_espn_id = {}

    for pick in draft_picks:
        sleeper_player_id = str(pick.player_id)
        player_ids = get_player_ids(player_map, sleeper_player_id)
        espn_id = player_ids.get('espn_id')
        if espn_id:
            espn_ids.append(int(espn_id))
            sleeper_to_espn_id[sleeper_player_id] = int(espn_id)
        else:
            print(f"No ESPN ID found for Sleeper ID: {sleeper_player_id}")

    espn_players = batch_get_espn_players(league, espn_ids)

    for pick in draft_picks:
        sleeper_player_id = str(pick.player_id)
        espn_id = sleeper_to_espn_id.get(sleeper_player_id)
        if espn_id:
            espn_player = espn_players.get(espn_id)
            if espn_player:
                draft_slot_picks[pick.draft_slot].append({
                    'player': espn_player,
                    'pick_no': pick.pick_no
                })
            else:
                print(f"ESPN player not found for Sleeper ID: {sleeper_player_id}")

    return dict(draft_slot_picks)


def import_draft_to_espn(draft: Draft, draft_slot_picks: dict, league):
    for draft_slot, picks in draft_slot_picks.items():
        print(f"Draft Slot {draft_slot} selections:")
        for pick in picks:
            print(f"  Pick {pick['pick_no']}: {pick['player'].name}")
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

    # Get Sleeper draft URL from user
    sleeper_draft_url = input("Enter the Sleeper draft URL: ")
    sleeper_draft_id = extract_draft_id_from_url(sleeper_draft_url)
    if not sleeper_draft_id:
        print("Invalid Sleeper draft URL. Exiting.")
        return

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
