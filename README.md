# ESPN Fantasy Football Draft Importer

This project allows you to import a Sleeper NFL fantasy football draft into an ESPN fantasy football league. It supports both snake and linear draft types from Sleeper and automatically adjusts linear drafts to fit ESPN's snake draft format.

## Features

- Import Sleeper NFL fantasy football drafts into ESPN leagues
- Support for both snake and linear draft types
- Automatic conversion of linear drafts to snake format for ESPN compatibility
- Efficient batch processing of player information
- Automatic download of the latest player ID mappings
- Detailed console output for tracking the import process

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.7 or higher installed on your system
- Access to both the Sleeper draft you want to import and the ESPN league you're importing into
- League manager permissions for the ESPN league

## Installation

1. Clone this repository or download the script files.

2. Install the required Python packages:

   ```
   pip install espn_api sleeper requests
   ```

3. Create a file named `espn_config.json` in the same directory as the script with the following structure:

   ```json
   {
       "ESPN_S2": "your_espn_s2_cookie",
       "SWID": "your_swid_cookie",
       "LEAGUE_ID": your_espn_league_id,
       "YEAR": current_year
   }
   ```

   Replace the values with your actual ESPN credentials and league information.

   For help on how to acquire these values checkout [this discussion from the espn-api repository](https://github.com/cwendt94/espn-api/discussions/150#discussioncomment-133615).



## Usage

### Draft Setup

1. Ensure that your Sleeper draft settings match the settings of your ESPN league.

      `i.e.: Team #, Roster Size, Roster Position Composition`

2. Ensure that the draft slots for each player in the Sleeper draft line up with their corresponding draft slot in your ESPN fantasy league.

3. For your ESPN league, set your Draft Settings `Draft Type` to `Offline`.

4. Verify that you have your draft order set correctly in ESPN, and that your Sleeper draft order mirrors the order set for your ESPN league.

5. Before running the script, you must make sure that the Draft Date/Time you set for the ESPN league's Offline Draft has already passed and the draft has begun.
   - In ESPN: Go to `LM Tools`
   - Under `Draft Tools`, select `Input Offline Draft Results`
   - Press the `Begin Offline Draft` button.

### Running the script

1. Run the script:

   ```
   python espn_fantasy_import.py
   ```

2. The script will automatically download the latest player ID mappings from the [ffb_ids repository](https://github.com/mayscopeland/ffb_ids).

3. When prompted, enter the full URL of the Sleeper draft you want to import. It should look something like this:

   ```
   https://sleeper.com/draft/nfl/12345678901234567890
   ```

4. The script will process the draft data and attempt to import it into your ESPN league. You'll see progress updates and any warnings or errors in the console.

5. Once the import is complete, check your ESPN league to verify the draft results. 
   - Go to your ESPN League's LM Tools and under `Draft Tools` click the `Input Offline Draft Results` button. This should take you to the page where you can modify the imported rosters and verify that you're finished submitting the draft results.

## Example Video
https://github.com/user-attachments/assets/60e21a82-44c2-4c18-9738-a3986fd65742


## Important Notes

- This script will overwrite any existing draft data in your ESPN league. Use it with caution and only on leagues where you intend to replace the current draft.
- The script automatically downloads the latest player ID mappings at the start of each run. Ensure you have a stable internet connection.
- If you encounter any "No ESPN ID found for Sleeper ID" messages, it means the script couldn't find a matching ESPN player for a Sleeper player. This may occur if the player mappings are not up to date.
- The script includes a short delay between importing each team's picks to avoid rate limiting. If you encounter rate limit errors, you may need to increase this delay.

## Troubleshooting

- If you encounter authentication errors, double-check your ESPN_S2 and SWID values in the `espn_config.json` file.
- For any player mapping issues, ensure you have a stable internet connection for downloading the latest mappings.
- If you get errors related to missing modules, ensure you've installed all required packages listed in the Installation section.

## Contributing

Contributions to improve the script or extend its functionality are welcome. Please feel free to submit pull requests or open issues for any bugs or feature requests.

## Acknowledgments

- Player ID mappings are sourced from the [ffb_ids repository](https://github.com/mayscopeland/ffb_ids) maintained by [May Scopeland](https://github.com/mayscopeland). 

## Disclaimer

This script is for educational purposes and personal use. Use it at your own risk. Always ensure you have the necessary permissions to modify league data on ESPN.
