import json
import time
from urllib.parse import urlparse, urlunparse
import requests
from espn_api.football import League
from espn_api.requests.espn_requests import checkRequestStatus
from sleeper.api import DraftAPIClient
from sleeper.enum import Sport, DraftType
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


def modify_endpoint_to_writes(endpoint: str) -> str:
    parsed_url = urlparse(endpoint)
    netloc = parsed_url.netloc.replace('lm-api-reads', 'lm-api-writes')
    modified_url = parsed_url._replace(netloc=netloc)
    return urlunparse(modified_url)


def league_post(league: League, payload: dict = None, headers: dict = None, extend: str = ''):
    test = league.espn_request.get_league_draft()

    endpoint = league.espn_request.LEAGUE_ENDPOINT + extend
    write_endpoint = modify_endpoint_to_writes(endpoint)
    r = requests.post(write_endpoint, json=payload, headers=headers, cookies=league.espn_request.cookies)
    checkRequestStatus(r.status_code)
    if league.espn_request.logger:
        league.espn_request.logger.log_request(endpoint=endpoint, params=payload, headers=headers, response=r.json())
    return r.json() if league.espn_request.year > 2017 else r.json()[0]


def extract_draft_id_from_url(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    if len(path_parts) >= 4 and path_parts[1] == 'draft' and path_parts[2] == 'nfl':
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


def rearrange_linear_to_snake(draft_picks: list[PlayerDraftPick], num_teams: int):
    team_picks = defaultdict(list)
    for pick in draft_picks:
        team_picks[pick.draft_slot].append(pick)

    snake_picks = []
    for round_num in range(1, len(draft_picks) // num_teams + 1):
        round_picks = []
        for team in range(1, num_teams + 1):
            if round_num % 2 == 1:  # Odd rounds
                pick = team_picks[team].pop(0)
            else:  # Even rounds
                pick = team_picks[num_teams - team + 1].pop(0)
            round_picks.append(pick)
        snake_picks.extend(round_picks)

    for i, pick in enumerate(snake_picks):
        pick.pick_no = i + 1

    return snake_picks


def map_sleeper_to_espn_players(draft: Draft, draft_picks: list[PlayerDraftPick], league, player_map):
    if draft.type == DraftType.LINEAR:
        draft_picks = rearrange_linear_to_snake(draft_picks, draft.settings.teams)

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


def get_draft_slot_to_team_id_mapping(league: League, num_teams: int):
    draft_detail = league.espn_request.get_league_draft()['draftDetail']
    mapping = {}
    for pick in draft_detail['picks']:
        if pick['roundId'] == 1:
            mapping[pick['roundPickNumber']] = pick['teamId']

    for slot in range(1, num_teams + 1):
        if slot not in mapping:
            print(f"Warning: No team ID found for draft slot {slot}")

    return mapping


def import_draft_slot_to_espn(league: League, draft_slot: int, picks: list, slot_to_team_mapping: dict):
    items = []
    for pick in picks:
        items.append({
            "overallPickNumber": pick['pick_no'],
            "type": "DRAFT",
            "playerId": pick['player'].playerId
        })

    team_id = slot_to_team_mapping.get(draft_slot)
    if team_id is None:
        print(f"Error: No team ID found for draft slot {draft_slot}")
        return None

    payload = {
        "isLeagueManager": True,
        "teamId": team_id,
        "type": "DRAFT",
        "scoringPeriodId": 1,
        "executionType": "EXECUTE",
        "items": items
    }

    try:
        response = league_post(league=league, payload=payload, extend="/transactions/")
        print(f"Successfully imported draft for team {team_id} (draft slot {draft_slot})")
        print(f"Response: {json.dumps(response, indent=2)}")
        return response
    except Exception as e:
        print(f"Error importing draft for team {team_id} (draft slot {draft_slot}): {str(e)}")
        return None


def import_all_draft_slots(league: League, draft: Draft, draft_slot_picks: dict):
    slot_to_team_mapping = get_draft_slot_to_team_id_mapping(league, draft.settings.teams)
    for draft_slot, picks in draft_slot_picks.items():
        import_draft_slot_to_espn(league, draft_slot, picks, slot_to_team_mapping)
        time.sleep(0.1)  # Delay to avoid rate limiting


def download_latest_player_ids(file_path='player_ids.csv'):
    url = "https://raw.githubusercontent.com/mayscopeland/ffb_ids/main/player_ids.csv"
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(response.text)
        print(f"Successfully downloaded and saved player IDs to {file_path}")
    except requests.RequestException as e:
        print(f"Error downloading player IDs: {e}")
        return False
    except IOError as e:
        print(f"Error saving player IDs file: {e}")
        return False
    return True


def main():
    # Download the latest player IDs
    if not download_latest_player_ids():
        print("Failed to download latest player IDs. Exiting.")
        return

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
    draft_slot_picks = map_sleeper_to_espn_players(draft, draft_picks, league, player_map)

    # Import draft results into ESPN
    import_all_draft_slots(league, draft, draft_slot_picks)

    print("Import complete")


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.2f} seconds")
