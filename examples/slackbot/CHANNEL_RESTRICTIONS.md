# Slack Bot Channel Restrictions

This feature restricts the Slack bot to only respond in designated channels per workspace. When users message the bot in other channels, they'll receive a friendly redirect message.

## Configuration

The workspace-to-channel mapping is configured in `_internal/constants.py`:

```python
WORKSPACE_TO_CHANNEL_ID = {
    "TL09B008Y": "C04DZJC94DC",  # Prefect Community -> #ask-marvin
    "TAN3D79AL": "C046WGGKF4P",  # Prefect -> #ask-marvin-tests
    "T03S63K44P6": "C03S3HZ2X3M",  # Stoat LLC -> #testing-slackbots
}
```

To add a new workspace, simply add an entry to this dictionary with the workspace team ID as the key and the designated channel ID as the value.

### Finding your workspace and channel IDs

#### Method 1: From Slack Web/Desktop App
1. **Workspace Team ID**: 
   - Open Slack in a web browser
   - The URL will be something like `https://app.slack.com/client/T024BE7LD/C0123456789`
   - The part after `/client/` starting with "T" is your Team ID (e.g., `T024BE7LD`)

#### Method 2: Using the bot itself
The bot already retrieves the team ID from incoming events. You can see it in the logs when a message is processed, or add a temporary debug endpoint:

```python
# In api.py, you could add:
@app.get("/workspace-info")
async def get_workspace_info_endpoint():
    info = await get_workspace_info()
    return {"team_id": info.get("id"), "name": info.get("name")}
```

#### Method 3: Via Slack API
```bash
curl -X GET "https://slack.com/api/team.info" \
  -H "Authorization: Bearer YOUR_SLACK_BOT_TOKEN"
```

2. **Channel ID**: 
   - Right-click on a channel in Slack
   - Select "View channel details" 
   - Scroll to the bottom - you'll see the Channel ID (starts with "C" for public channels)

## How it works

1. When a user mentions the bot in any channel, the bot checks if that channel is the designated channel for the workspace
2. If it's not the designated channel, the bot responds with: "Please use #channel-name for bot interactions."
3. The channel name is rendered as a clickable link that takes users directly to the correct channel
4. If no mapping is configured for a workspace, the bot will respond in all channels (default behavior)

## Multiple environments

This feature is designed to support multiple deployment environments. Simply configure different channel IDs in the Prefect Variable for each environment:

- **Production**: Map to your production support channel
- **Staging**: Map to your staging/test channel
- **Development**: Map to your dev/sandbox channel

The bot will automatically use the correct channel based on which workspace it's deployed to.

## Example redirect message

When a user messages the bot in a non-designated channel, they'll see:

> Please use #bot-support for bot interactions.

The channel name appears as a clickable link that opens the correct channel when clicked.