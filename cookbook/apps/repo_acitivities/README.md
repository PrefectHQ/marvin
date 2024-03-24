# process and react to webhook events from github repositories

## Installation
TODO

## Overview

### Webhook Events
For each repo set up, Github will `POST` to `/webhook` with a JSON payload containing information about the event that triggered the webhook.


### Webhook Event Handlers
The JSON payload will be parsed and the event type will be determined. The event type will be used to determine which handler to call.

#### Event Types
- merge to `main` branch
- release
- new issue
- new issue comment
- new pull request
- new pull request comment