import inspect
from datetime import date, datetime, timedelta

import marvin
from marvin.utilities.jinja import BaseTemplate, JinjaEnvironment
from marvin.utilities.slack import post_slack_message
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from prefect.blocks.system import Secret
from prefect.filesystems import GCS
from prefect.tasks import task_input_hash
from utils import fetch_contributor_data

CHANNEL_MAP = {
    "ask-marvin-tests": "C046WGGKF4P",
    "testing-slackbots": "C03S3HZ2X3M",
}


def get_repo_digest_template(**jinja_settings) -> BaseTemplate:
    return JinjaEnvironment(**jinja_settings).from_string(
        inspect.cleandoc(
            """
            # [{{ owner }}/{{ repo }}](https://github.com/{{ owner }}/{{ repo }})

            ## GitHub Events Digest from {{ since.strftime("%Y-%m-%d") }} to {{ today.strftime("%Y-%m-%d") }}
                
            {% for contributor, activities in contributors_activity.items() %}
            {% if activities.created_issues|length > 0 or activities.created_pull_requests|length > 0 or activities.merged_commits|length > 0 %}
            ## {{ contributor }}:
            {% if activities.created_issues|length > 0 %}
            - Created {{ activities.created_issues|length }} issue(s)
            {% for issue in activities.created_issues %}
                - [{{ issue.title }}]({{ issue.html_url }})
            {% endfor %}
            {% endif %}
            
            {% if activities.created_pull_requests|length > 0 %}
            - Opened {{ activities.created_pull_requests|length }} PR(s)
            {% for pr in activities.created_pull_requests %}
                - [{{ pr.title }}]({{ pr.html_url }})
            {% endfor %}
            {% endif %}
            
            {% if activities.merged_commits|length > 0 %}
            - Merged {{ activities.merged_commits|length }} commit(s)
            {% for commit in activities.merged_commits %}
                - [{{ commit.commit.message }}]({{ commit.html_url }})
            {% endfor %}
            {% endif %}
            {% endif %}
            {% endfor %}
            """
        )
    )


@task(
    task_run_name="Fetch GitHub Activity for {owner}/{repo} @ {since}",
    cache_key_fn=lambda c, a: task_input_hash(
        c, {k: v for k, v in a.items() if k != "since"}
    ),
    cache_expiration=timedelta(days=1),
)
async def get_repo_activity_data(
    owner: str,
    repo: str,
    gh_token_secret_name: str,
    since: datetime,
    excluded_users=None,
):
    """Get the activity data for a given repository."""

    if not excluded_users:
        excluded_users = {"dependabot[bot]", "dependabot-preview[bot]", "dependabot"}

    return await fetch_contributor_data(
        token=(await Secret.load(gh_token_secret_name)).get(),
        owner=owner,
        repo=repo,
        since=since,
        excluded_users=excluded_users,
    )


@task(
    task_run_name="Summarize digest as an epic story",
    retries=1,
    retry_delay_seconds=3,
)
@marvin.fn
async def write_a_tasteful_epic(markdown_digest: str) -> str:
    """Given a markdown digest of GitHub activity, create a short story.

    Each contributor should be mentioned by name and the character representation
    proportional to their contribution. Speak as if Marvin from the Hitchhiker's
    Guide to the galaxy -- genius, but sarcastic and mildly depressed. Marvin should genuinely
    but begrudgingly cheer on the contributors in their efforts, interspersing satirical digs.
    Always link to every centrally relevant Github resources (PRs, user profiles, etc.) at
    least once and recall that readers will only see the hyperlink text, so be sure to
    make clear the context of each link -- while remaining consistent and proportional in
    clarity to the gravity of contribution. Cleverly reference specific commit messages.

    Do NOT be overly verbose - think step by step like an expert Pythonista to determine gravity.

    The story should begin with a short pithy welcome to the reader and have
    an incredibly short #h1 title that directly and specifically summarizes the activity.
    """


@task
@marvin.image
def draw_a_movie_poster(
    epic_story: str,
    actor_representation: str = "distinctive stick figures",
    setting_description: str = "realistic, space-themed (70s George Lucas style)",
    requirements: str = "5 words DIRECTLY relevant to the story, no other words",
) -> str:
    return f"""
        Given a short story, create a movie poster for the story.

        The poster should include the main actors in proportion to their representation
        in the story. Individual actors should be shown as {actor_representation} in a
        {setting_description} setting with grand and highly detailed scenery. The repo
        should be represented abstractly as a large, ornate, central figure in the background.
        
        The poster NEEDS to include the following: {requirements}

        here's the story to draw a movie poster for: {epic_story}
    """


@flow(
    name="Daily GitHub Digest",
    flow_run_name="Digest {owner}/{repo}",
    result_storage=GCS.load("marvin-result-storage"),
)
async def daily_github_digest(
    owner: str = "PrefectHQ",
    repo: str = "prefect",
    slack_channel: str = "ask-marvin-tests",
    gh_token_secret_name: str = "github-token",
    post_story_to_slack: bool = False,
    lookback_days: int | None = None,
):
    """Creates a daily digest of GitHub activity for a given repository.

    Args:
        owner: The owner of the repository.
        repo: The name of the repository.
        slack_channel: The name of the Slack channel to post the digest to.
        gh_token_secret_name: Secret Block containing the GitHub token.
    """
    if lookback_days is None:
        lookback_days = 1 if date.today().weekday() != 0 else 3

    since = datetime.utcnow() - timedelta(days=lookback_days)

    data_future = await get_repo_activity_data.submit(
        owner=owner,
        repo=repo,
        gh_token_secret_name=gh_token_secret_name,
        since=since,
    )

    markdown_digest = await task(
        get_repo_digest_template(enable_async=True).render_async
    )(
        today=date.today(),
        since=since,
        owner=owner,
        repo=repo,
        contributors_activity=await data_future.result(),
    )

    marvin.settings.openai.chat.completions.model = "gpt-4"

    epic_story = write_a_tasteful_epic(markdown_digest)

    image_url = draw_a_movie_poster(epic_story).data[0].url

    await create_markdown_artifact(
        key=f"{repo}-github-digest",
        markdown=markdown_digest,
        description=epic_story + f"\n![cover art]({image_url})",
    )

    if post_story_to_slack:
        await task(post_slack_message)(
            message=epic_story + f"\n<{image_url}|cover art>",
            channel_id=CHANNEL_MAP[slack_channel],
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        daily_github_digest(
            owner="PrefectHQ",
            repo="prefect",
            post_story_to_slack=False,
            lookback_days=1,
        )
    )
