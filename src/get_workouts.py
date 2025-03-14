import os
import requests
import datetime

def refresh_strava_token():
    """Refresh the Strava API access token if expired."""
    expires_at = int(os.getenv('STRAVA_TOKEN_EXPIRES_AT', '0'))
    if expires_at < datetime.datetime.now().timestamp():
        response = requests.post(
            url='https://www.strava.com/api/v3/oauth/token',
            data={
                'client_id': os.getenv('STRAVA_CLIENT_ID'),
                'client_secret': os.getenv('STRAVA_CLIENT_SECRET'),
                'refresh_token': os.getenv('STRAVA_REFRESH_TOKEN'),
                'grant_type': 'refresh_token'
            }
        )
        if response.status_code == 200:
            new_tokens = response.json()
            os.environ['STRAVA_ACCESS_TOKEN'] = new_tokens['access_token']
            os.environ['STRAVA_TOKEN_EXPIRES_AT'] = str(new_tokens['expires_at'])
            return new_tokens['access_token']
        else:
            print(f"Failed to refresh token: {response.status_code}")
            return None
    return os.getenv('STRAVA_ACCESS_TOKEN')

def get_workouts_from_strava(start_date, end_date):
    """Retrieve workouts from Strava within a date range."""
    access_token = refresh_strava_token()
    if not access_token:
        return []

    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "before": int(end_date.timestamp()),
        "after": int(start_date.timestamp()),
        "per_page": 200
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve workouts from Strava: {response.status_code}")
        return []

# Example usage
if __name__ == "__main__":
    start_date = datetime.datetime(2024, 12, 1)
    end_date = datetime.datetime(2024, 12, 31)
    workouts = get_workouts_from_strava(start_date, end_date)
    print(workouts)
