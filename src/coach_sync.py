"""
Coach mode sync module for managing multiple athletes.

This module provides CLI commands for coaches to manage athletes,
trigger syncs, and download activities on behalf of their runners.
"""

import logging
from pathlib import Path
from typing import Optional

import questionary

from .strava_oauth import (
    StravaOAuthClient,
    StravaAPIClient
)
from .main import TCXProcessor


def setup_logging() -> logging.Logger:
    """Setup logging for the coach sync module."""
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)
        handler = logging.FileHandler('coach_sync.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class CoachSyncManager:
    """Manager for coach mode operations."""

    def __init__(self, oauth_client: Optional[StravaOAuthClient] = None):
        self.logger = setup_logging()
        try:
            self.oauth_client = oauth_client or StravaOAuthClient()
            self.api_client = StravaAPIClient(self.oauth_client)
        except ValueError as err:
            self.logger.error(str(err))
            self.oauth_client = None
            self.api_client = None

    def run(self) -> None:
        """Main coach mode menu."""
        if not self.oauth_client:
            print("\n⚠️  Strava OAuth is not configured.")
            print(
                "Please set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables.")
            print("See docs/coach_mode.md for setup instructions.\n")
            return

        while True:
            action = questionary.select(
                "Coach Mode - What would you like to do?",
                choices=[
                    "Add new athlete (OAuth authorization)",
                    "List registered athletes",
                    "Sync activity for athlete",
                    "List athlete's recent activities",
                    "Remove athlete",
                    "Exit coach mode"
                ]
            ).ask()

            if action is None or "Exit" in action:
                break
            if "Add new" in action:
                self._add_athlete()
            elif "List registered" in action:
                self._list_athletes()
            elif "Sync activity" in action:
                self._sync_activity()
            elif "List athlete" in action:
                self._list_activities()
            elif "Remove" in action:
                self._remove_athlete()

    def _add_athlete(self) -> None:
        """Add a new athlete via OAuth flow."""
        print("\n🏃 Adding new athlete...")
        print("A browser window will open for the athlete to authorize the app.")
        print("The athlete should log into their Strava account and grant permission.\n")

        proceed = questionary.confirm(
            "Ready to proceed with authorization?",
            default=True
        ).ask()

        if not proceed:
            return

        token = self.oauth_client.authorize_athlete(timeout=180)
        if token:
            print(
                f"\n✅ Successfully added athlete: {token.athlete_name} (ID: {token.athlete_id})")
        else:
            print("\n❌ Failed to add athlete. Please try again.")

    def _list_athletes(self) -> None:
        """List all registered athletes."""
        athletes = self.oauth_client.list_athletes()

        if not athletes:
            print("\n📋 No athletes registered yet.")
            print("Use 'Add new athlete' to register an athlete.\n")
            return

        print("\n📋 Registered Athletes:")
        print("-" * 40)
        for athlete_id, name in athletes.items():
            token = self.oauth_client.storage.get_token(athlete_id)
            status = "🟢 Valid" if token and not token.is_expired() else "🟡 Needs refresh"
            print(f"  {name} (ID: {athlete_id}) - {status}")
        print("-" * 40)
        print(f"Total: {len(athletes)} athlete(s)\n")

    def _select_athlete(self) -> Optional[int]:
        """Helper to select an athlete from the list."""
        athletes = self.oauth_client.list_athletes()

        if not athletes:
            print("\n❌ No athletes registered. Add an athlete first.\n")
            return None

        choices = [
            f"{name} (ID: {athlete_id})"
            for athlete_id, name in athletes.items()
        ]
        choices.append("Cancel")

        selection = questionary.select(
            "Select an athlete:",
            choices=choices
        ).ask()

        if selection == "Cancel" or selection is None:
            return None

        # Extract athlete ID from selection
        athlete_id = int(selection.split("ID: ")[1].rstrip(")"))
        return athlete_id

    def _sync_activity(self) -> None:
        """Sync a specific activity for an athlete."""
        athlete_id = self._select_athlete()
        if not athlete_id:
            return

        # Get activity ID
        activity_id_str = questionary.text(
            "Enter the Strava activity ID to sync:"
        ).ask()

        if not activity_id_str:
            return

        try:
            activity_id = int(activity_id_str.strip())
        except ValueError:
            print("❌ Invalid activity ID. Please enter a numeric ID.")
            return

        # Get output path
        download_folder = Path.home() / "Downloads"
        download_folder.mkdir(parents=True, exist_ok=True)
        output_path = str(download_folder / f"activity_{activity_id}.tcx")

        print(f"\n⏳ Downloading activity {activity_id}...")

        result = self.api_client.download_tcx(
            athlete_id, activity_id, output_path)

        if result:
            print(f"✅ Activity downloaded successfully to: {result}")
            print("\n📤 You can now upload this file to TrainingPeaks.")

            # Option to process with main TCXProcessor
            process = questionary.confirm(
                "Do you want to process this file with the main application?",
                default=True
            ).ask()

            if process:
                self._process_tcx_file(result)
        else:
            print("❌ Failed to download activity. Check the activity ID and try again.")

    def _process_tcx_file(self, file_path: str) -> None:
        """Process a TCX file with the main application."""
        try:
            processor = TCXProcessor()
            if hasattr(processor, 'run_with_file'):
                processor.run_with_file(file_path)
            else:
                print(f"\n📁 TCX file saved at: {file_path}")
                print(
                    "Run 'strava-to-trainingpeaks' and select 'Provide path' to process this file.")
        except Exception as err:
            self.logger.error("Failed to process TCX file: %s", str(err))
            print(f"\n📁 TCX file saved at: {file_path}")
            print(
                "Run 'strava-to-trainingpeaks' and select 'Provide path' to process this file.")

    def _list_activities(self) -> None:
        """List recent activities for an athlete."""
        athlete_id = self._select_athlete()
        if not athlete_id:
            return

        print("\n⏳ Fetching recent activities...")

        activities = self.api_client.list_activities(athlete_id, per_page=10)

        if not activities:
            print("❌ No activities found or failed to fetch activities.")
            return

        print("\n📋 Recent Activities:")
        print("-" * 60)
        for activity in activities:
            activity_id = activity.get("id")
            name = activity.get("name", "Unnamed")
            sport = activity.get("type", "Unknown")
            distance = activity.get("distance", 0) / 1000  # Convert to km
            date = activity.get("start_date_local", "Unknown date")[:10]
            print(
                f"  [{activity_id}] {date} - {sport}: {name} ({distance:.2f} km)")
        print("-" * 60)
        print(f"Showing {len(activities)} most recent activities.\n")

    def _remove_athlete(self) -> None:
        """Remove an athlete's authorization."""
        athlete_id = self._select_athlete()
        if not athlete_id:
            return

        athletes = self.oauth_client.list_athletes()
        athlete_name = athletes.get(athlete_id, "Unknown")

        confirm = questionary.confirm(
            f"Are you sure you want to remove {athlete_name} (ID: {athlete_id})?",
            default=False
        ).ask()

        if confirm:
            success = self.oauth_client.remove_athlete(athlete_id)
            if success:
                print(f"✅ Removed athlete: {athlete_name}")
            else:
                print("❌ Failed to remove athlete.")


def coach_mode_main() -> None:
    """Entry point for coach mode CLI."""
    print("\n" + "=" * 50)
    print("🏋️  STRAVA TO TRAININGPEAKS - COACH MODE")
    print("=" * 50 + "\n")

    manager = CoachSyncManager()
    manager.run()

    print("\nGoodbye! 👋\n")


if __name__ == "__main__":
    coach_mode_main()
