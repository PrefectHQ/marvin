# Process and React to Webhook Events from GitHub Repositories

This project enables processing and reacting to webhook events from GitHub repositories. It provides a flexible and extensible framework for handling different types of events and executing custom actions based on the event type.

## Installation

0. Learn a bit about [GitHub Webhooks](https://docs.github.com/en/developers/webhooks-and-events/webhooks) and how to [create a webhook](https://docs.github.com/en/developers/webhooks-and-events/webhooks/creating-webhooks) for your repository.

1. Clone this repository:
   ```
   gh repo clone https://github.com/prefecthq/marvin.git
   # or `git clone https://github.com/prefecthq/marvin.git` if you don't have `gh` installed
   ```

2. Navigate to the app directory:
   ```
   cd cookbook/apps/repo_activities
   ```

3. Create a `.env` file in the project root and set the required environment variables:
   ```
   OPENAI_API_KEY=your-openai-api-key
   PREFECT_API_KEY=your-prefect-api-key
   PREFECT_API_URL=your-prefect-api-url
   ```

4. Build and start the services using Docker Compose:
   ```
   docker-compose up --build -d
   ```

   This command will build the Docker images and start the services defined in the `docker-compose.yml` file.

5. Monitor the logs of the `handlers` and `api` services to observe the processing of webhook events:
   ```
    docker-compose logs -f handlers api
   ```

6. Tear down the services when you're done:
   ```
   docker-compose down -v
   ```

## Overview

### Webhook Events

GitHub will send a `POST` request to the `/webhook` endpoint with a JSON payload containing information about the event that triggered the webhook. The payload includes details such as the event type, repository information, and additional data specific to the event.

### Webhook Event Handlers

The received JSON payload is parsed, and the event type is determined based on the payload data. The event type is used to select the appropriate handler function to process the event.

### Configuration

The project uses a `docker-compose.yml` file to define and configure the services. The file includes the following services:

- `api`: Serves the endpoint that receives webhook events and submits them to the handler
- `tasks`: Processes the received events and executes the appropriate handler function
- `redis`: Provides a Redis instance for storing handler results (or any other data)

The `tasks` and `api` services depend on the `redis` service and share a task storage volume for persistence.

### Prefect Integration

The project leverages Prefect to handle the execution of webhook event handlers (i.e background tasks). The `handle_repo_request` function in `tasks.py` is decorated with `@task` to make it a Prefect task.

The Prefect task is configured with the following settings:
- `log_prints=True`: Send stdout and stderr output to the Prefect logger
- `task_run_name`: Sets the name of the task run based on the tasks input arguments

The task retrieves the appropriate handler function based on the repository name and executes it with the received request data. If the handler returns a serializable result (i.e., a Pydantic model), it is serialized and stored in Redis using a key composed of:
- the webhook event type
- a short LLM-digest string
- the webhook delivery ID as the key.

for example, the key might look like:
```console
issue_comment:about_broken_imports:123456789
```

## How to Use

1. Set up a webhook in your GitHub repository settings, pointing to the `/webhook` endpoint of your deployed service.

2. Deploy the services using the provided `docker-compose.yml` file.

3. GitHub will send webhook events to the `/webhook` endpoint whenever the configured events occur in the repository.

4. Customize the `handlers.py` file to define specific handler functions for different event types or repositories.