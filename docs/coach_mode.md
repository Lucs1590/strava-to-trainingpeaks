# Coach Mode - Multi-Athlete Sync Guide

This guide explains how to use the Coach Mode feature to manage and sync Strava activities for multiple athletes.

## Overview

Coach Mode enables coaches, trainers, and team managers to:

- 🔐 **Secure OAuth Authorization**: Athletes authorize once through Strava's official OAuth flow
- 👥 **Multi-Athlete Management**: Manage dozens of athletes from a single interface
- 🔄 **Automatic Token Refresh**: Tokens are automatically refreshed when expired
- 📥 **Batch Operations**: Download and process activities for multiple athletes
- 🎯 **No Code Required**: Athletes don't need to install anything or run code
- 🔒 **Token Security**: All tokens are stored securely and can be revoked anytime

## Use Cases

- **Professional Coaches**: Manage training data for your entire roster
- **Team Managers**: Coordinate athlete data across your organization
- **Training Groups**: Help athletes who aren't tech-savvy
- **Triathlon Clubs**: Centralize data management for club members

## Prerequisites

Before starting, ensure you have:

1. **Python 3.12+** installed
2. **Strava account** (coach/manager account)
3. **Athletes willing to authorize** your application
4. **Basic command line knowledge**

---

## Step 1: Register a Strava API Application

1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Click **Create an App** (or manage existing app)
3. Fill in the application details:
   - **Application Name**: Your app name (e.g., "My Coach Sync")
   - **Category**: Choose "Training Analysis"
   - **Club**: Optional
   - **Website**: Your website or `http://localhost`
   - **Authorization Callback Domain**: `localhost`
   - **Description**: Brief description of your app

4. After creation, note down:
   - **Client ID**: A numeric ID
   - **Client Secret**: A secret string (keep this secure!)

> **Note**: For visual reference, see the [Strava API Documentation](https://developers.strava.com/docs/getting-started/) which includes screenshots of the API settings page.

---

## Step 2: Configure Environment Variables

Create a `.env` file in the project root or set environment variables:

```bash
# Required
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here

# Optional (defaults shown)
STRAVA_REDIRECT_URI=http://localhost:8089/callback
STRAVA_SCOPES=activity:read_all
STRAVA_TOKEN_FILE=.strava_tokens.json
```

### Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRAVA_CLIENT_ID` | Yes | - | Your Strava API Client ID |
| `STRAVA_CLIENT_SECRET` | Yes | - | Your Strava API Client Secret |
| `STRAVA_REDIRECT_URI` | No | `http://localhost:8089/callback` | OAuth callback URL |
| `STRAVA_SCOPES` | No | `activity:read_all` | OAuth scopes to request |
| `STRAVA_TOKEN_FILE` | No | `.strava_tokens.json` | File to store athlete tokens |

---

## Step 3: Authorize Athletes (One-Time Setup)

Each athlete needs to authorize the app once. This can be done in person or remotely.

### In-Person Authorization

1. Run the coach mode:

   ```bash
   strava-coach-mode
   ```

2. Select **"Add new athlete (OAuth authorization)"**

3. Have the athlete:
   - Log into their Strava account in the browser that opens
   - Click **Authorize** to grant permission

4. The athlete's token is now stored locally

### Remote Authorization

For athletes who can't be present:

1. Share the authorization URL with them:

   ```python
   from src.strava_oauth import StravaOAuthClient
   
   client = StravaOAuthClient()
   print(client.get_authorization_url())
   ```

2. The athlete visits the URL, logs in, and authorizes

3. The callback will fail (since it's localhost), but they can copy the authorization code from the URL:

   ```bash
   http://localhost:8089/callback?code=XXXXXXXX&scope=...
   ```

4. Manually exchange the code (advanced):

   ```python
   token = client._exchange_code_for_token("XXXXXXXX")
   ```

---

## Step 4: Using Coach Mode

### Start Coach Mode

```bash
strava-coach-mode
```

### Available Commands

| Command | Description |
|---------|-------------|
| Add new athlete | Start OAuth flow for a new athlete |
| List registered athletes | Show all authorized athletes |
| Sync activity for athlete | Download a specific activity |
| List athlete's recent activities | Show recent activities with IDs |
| Remove athlete | Revoke an athlete's authorization |
| Exit coach mode | Exit the application |

### Syncing an Activity

1. Select **"Sync activity for athlete"**
2. Choose the athlete from the list
3. Enter the Strava activity ID (found in the activity URL)
4. The TCX file is downloaded to your Downloads folder
5. Optionally process it with the main application

### Finding Activity IDs

Activity IDs can be found in Strava URLs:

```
https://www.strava.com/activities/1234567890
                                 ^^^^^^^^^^
                                 Activity ID
```

Or use **"List athlete's recent activities"** to see recent activity IDs.

---

## Security Considerations

### Token Storage

- Tokens are stored in `.strava_tokens.json` by default
- This file should **NOT** be committed to version control
- Add to `.gitignore`:

  ```
  .strava_tokens.json
  ```

### Token Security Best Practices

1. **Keep `STRAVA_CLIENT_SECRET` secure**
   - Never commit it to version control
   - Use environment variables or a secrets manager

2. **Limit scope requests**
   - Only request scopes you need
   - `activity:read_all` is sufficient for downloading activities

3. **Refresh tokens**
   - Access tokens expire after 6 hours
   - The app automatically refreshes tokens when needed
   - Refresh tokens are long-lived but can be revoked

4. **Athlete consent**
   - Athletes can revoke access anytime at [Strava Settings > Apps](https://www.strava.com/settings/apps)
   - Inform athletes about what data you'll access

### File Permissions

On Unix systems, restrict token file permissions:

```bash
chmod 600 .strava_tokens.json
```

---

## API Rate Limits

Strava API has rate limits:

| Limit | Value |
|-------|-------|
| Per 15 minutes | 100 requests |
| Per day | 1000 requests |

The application handles rate limiting gracefully, but avoid rapid bulk operations.

---

## Troubleshooting

### "STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables are required"

**Cause**: Environment variables not set.

**Solution**:

1. Create a `.env` file with your credentials
2. Or export variables: `export STRAVA_CLIENT_ID=xxx`

### "Authorization timed out"

**Cause**: Athlete didn't complete authorization within 3 minutes.

**Solution**: Try again and complete authorization faster.

### "Failed to download activity data"

**Cause**: Activity may be private or token may be expired.

**Solutions**:

1. Ensure the activity is accessible with the granted scope
2. Try refreshing the token (automatic on next request)
3. Re-authorize the athlete

### "No valid token for athlete"

**Cause**: Token may have been revoked or deleted.

**Solution**: Re-authorize the athlete using "Add new athlete".

---

## Programmatic Usage

You can also use the OAuth client programmatically:

```python
from src.strava_oauth import StravaOAuthClient, StravaAPIClient

# Initialize clients
oauth = StravaOAuthClient()
api = StravaAPIClient(oauth)

# List athletes
athletes = oauth.list_athletes()
print(athletes)

# Get athlete's activities
activities = api.list_activities(athlete_id=12345, per_page=10)

# Download TCX
api.download_tcx(
    athlete_id=12345,
    activity_id=9876543210,
    output_path="activity.tcx"
)
```

---

## Privacy Notice

When using Coach Mode:

1. **Data Collection**: The app collects activity data (routes, times, heart rate, etc.)
2. **Storage**: Tokens are stored locally on your machine
3. **Usage**: Data is used solely to generate TCX files for TrainingPeaks
4. **Sharing**: No data is shared with third parties
5. **Deletion**: Athletes can request data deletion by revoking access

Coaches should inform athletes about data handling practices.

---

## Best Practices for Coaches

### Communication with Athletes

1. **Clear Explanation**: Explain why you need OAuth access and what you'll use it for
2. **Privacy Assurance**: Reassure athletes that their data is secure and won't be shared
3. **Revocation Rights**: Inform them they can revoke access at any time
4. **Regular Updates**: Keep athletes informed about their training data usage

### Workflow Optimization

1. **Batch Processing**: Schedule regular sync windows to process multiple athletes
2. **Activity Filtering**: Focus on recent activities or specific date ranges
3. **Token Management**: Regularly check token status to ensure smooth operations
4. **Backup Strategy**: Keep backups of token files (securely) to prevent data loss

### Scaling to Many Athletes

- Use descriptive athlete names in the token file for easy identification
- Implement a naming convention for downloaded TCX files (e.g., `athletename_date_activityid.tcx`)
- Consider automating syncs with scheduled tasks or cron jobs
- Monitor API rate limits when managing 10+ athletes

---

## Related Articles & Tutorials

Learn more about this project and its capabilities:

### Setup & Configuration
- 📖 [Complete Setup Guide - Strava to Training Peaks](https://medium.com/p/fa3a0fa05f79)
  - Step-by-step installation instructions
  - OAuth configuration walkthrough
  - Tips for managing multiple athletes

### AI-Powered Features
- 🤖 [LLM to Strava: Intelligent Training Analysis with AI Co-coaching](https://levelup.gitconnected.com/llm-to-strava-intelligent-training-analysis-with-ai-co-coaching-03f1cf866597)
  - How the AI analysis feature works
  - Understanding performance metrics
  - Using audio summaries for training feedback

### Video Tutorials
- 🎥 [Manual Export from Strava to TrainingPeaks](https://www.youtube.com/watch?v=Y0nWzOAM8_M)
  - Visual walkthrough of the export process

---

## Further Resources

### Official Documentation
- [Strava API Documentation](https://developers.strava.com/docs/reference/)
- [OAuth 2.0 Authentication Guide](https://developers.strava.com/docs/authentication/)
- [TrainingPeaks Import Guide](https://help.trainingpeaks.com/hc/en-us/articles/360014889633-Uploading-Activities)

### Project Links
- **Author**: [Lucas Brito](https://lucasbrito.com.br/)
- **Repository**: [github.com/Lucs1590/strava-to-trainingpeaks](https://github.com/Lucs1590/strava-to-trainingpeaks)
- **Issues**: [Report bugs or request features](https://github.com/Lucs1590/strava-to-trainingpeaks/issues)

---

## Support & Community

Need help? Have questions?

- 🐛 **Bug Reports**: [Open an issue on GitHub](https://github.com/Lucs1590/strava-to-trainingpeaks/issues)
- 💡 **Feature Requests**: Share your ideas in the issue tracker
- 📧 **Contact**: Reach out through [Lucas's website](https://lucasbrito.com.br/)
- ⭐ **Show Support**: Star the repository if you find it useful!

---

*Last Updated: December 2024*
