import os
import json
import requests
import datetime
import webbrowser
from dotenv import load_dotenv

load_dotenv()

TOKENS_FILE = 'strava_tokens.json'


def load_tokens():
    """Load tokens from the JSON file if it exists."""
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    return None


def save_tokens(tokens):
    """Save tokens to the JSON file."""
    with open(TOKENS_FILE, 'w', encoding='utf-8') as file:
        json.dump(tokens, file, indent=4)


def refresh_strava_token():
    """
    Refresh the Strava API access token if expired.
    If no tokens exist, perform initial authentication using the authorization code.
    """
    tokens = load_tokens()
    now_timestamp = datetime.datetime.now().timestamp()

    if tokens:
        if tokens.get('expires_at', 0) < now_timestamp:
            print("Access token expired. Refreshing token...")
            response = requests.post(
                url='https://www.strava.com/api/v3/oauth/token',
                data={
                    'client_id': os.getenv('STRAVA_CLIENT_ID'),
                    'client_secret': os.getenv('STRAVA_CLIENT_SECRET'),
                    'grant_type': 'refresh_token',
                    'refresh_token': tokens['refresh_token']
                }
            )
            if response.status_code == 200:
                new_tokens = response.json()
                save_tokens(new_tokens)
                return new_tokens['access_token']
            else:
                print(
                    f"Failed to refresh token: {response.status_code} - {response.text}")
                return None
        else:
            return tokens['access_token']
    else:
        print("No token file found. Performing initial authentication...")
        response = requests.post(
            url='https://www.strava.com/api/v3/oauth/token',
            data={
                'client_id': os.getenv('STRAVA_CLIENT_ID'),
                'client_secret': os.getenv('STRAVA_CLIENT_SECRET'),
                'code': os.getenv('STRAVA_CODE'),
                'grant_type': 'authorization_code'
            }
        )
        if response.status_code == 200:
            tokens = response.json()
            save_tokens(tokens)
            return tokens['access_token']
        else:
            print(
                f"Failed initial authentication: {response.status_code} - {response.text}"
            )
            return None


def get_workouts_from_strava(start_date, end_date):
    """
    Retrieve workouts (activities) from Strava within a given date range.
    """
    access_token = refresh_strava_token()
    if not access_token:
        print("No valid access token available.")
        return []

    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "after": int(start_date.timestamp()),
        "before": int(end_date.timestamp()),
        "per_page": 200
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(
            f"Failed to retrieve workouts: {response.status_code} - {response.text}"
        )
        return []


def export_tcx_files(workouts):

    for workout in workouts:
        download_tcx_file(
            workout['id'],
            workout['type']
        )


def download_tcx_file(activity_id: str, sport: str) -> None:
    url = f"https://www.strava.com/activities/{activity_id}/export_{
        'original' if sport in ['Swim', 'Other'] else 'tcx'}"
    try:
        webbrowser.open(url)
    except Exception as err:
        print("Failed to download the TCX file from Strava.")
        raise ValueError("Error opening the browser") from err


if __name__ == "__main__":
    start_date = datetime.datetime(2024, 10, 1)
    end_date = datetime.datetime(2024, 12, 31)

    workouts = get_workouts_from_strava(start_date, end_date)
    workouts = list(
        filter(lambda x: str(x.get("type")).lower() in ["swim", "run", "ride"],
               map(lambda x: {"id": x.get('id', None), "type": x.get('type', None)},
                   workouts
                   )
               )
    )
    export_tcx_files(workouts)
