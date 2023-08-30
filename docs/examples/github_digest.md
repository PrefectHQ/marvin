# GitHub Digest

A fun example covering a few practical patterns is to create an AI digest of GitHub activity for a given repo.

If you've spent some time messing with AI tools in the Python ecosystem lately, you're probably familiar with [Jinja2](https://jinja.palletsprojects.com/en/3.1.x/). Jinja pairs really nicely with LLMs, because you can structure the template in a way that either makes it easy for the LLM to fill in the blanks, or makes it easy for you to fill in the blanks with traditional software and then pass the rendered template to the LLM as a prompt.

Here's an example of the latter:

## Writing an epic about the day's events in `PrefectHQ/prefect`

The AI part is pretty much English:

```python
@ai_fn(
    instructions="You are a witty and subtle orator. Speak to us of the day's events."
)
def summarize_digest(markdown_digest: str) -> str:
    """Given a markdown digest of GitHub activity, create a Story that is
    informative, entertaining, and epic in proportion to the day's events -
    an empty day should be handled with a short sarcastic quip about humans
    and their laziness.

    The story should capture collective efforts of the project.
    Each contributor plays a role in this story, their actions
    (issues raised, PRs opened, commits merged) shaping the events of the day.

    The narrative should highlight key contributors and their deeds, drawing upon the
    details in the digest to create a compelling and engaging tale of the day's events.
    A dry pun or 2 are encouraged.

    Usernames should be markdown links to the contributor's GitHub profile.

    The story should begin with a short pithy welcome to the reader and have
    a very short, summarizing title.
    """ # noqa: E501 (to make Ruff happy)
```

... and the rest is just... Python?

```python
import os
import inspect
from datetime import date, datetime, timedelta

from marvin import ai_fn

from my_helpers import (
    fetch_contributor_data,
    post_slack_message,
    YOUR_JINJA_TEMPLATE,
)

async def daily_github_digest(
    owner: str = "PrefectHQ",
    repo: str = "marvin",
    slack_channel: str = "ai-tools",
    gh_token_env_var: str = "GITHUB_PAT",
):
    since = datetime.utcnow() - timedelta(days=1)

    data = await fetch_contributor_data(
        token=os.getenv(gh_token_env_var), # load from your secrets manager
        owner=owner,
        repo=repo,
        since=since,
    )

    markdown_digest = YOUR_JINJA_TEMPLATE.render(
        today=date.today(),
        owner=owner,
        repo=repo,
        contributors_activity=data,
    )

    epic_story = summarize_digest(markdown_digest)

    await post_slack_message(
        message=epic_story,
        channel=slack_channel,
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(daily_github_digest(owner="PrefectHQ", repo="prefect"))
```

!!! tip "Tip"
    I brought some helpers with me to make this easier:

    - `fetch_contributor_data` uses the GitHub API to get a list of contributors and their activity
    - `post_slack_message` uses the Slack API to post a message to a channel
    - `YOUR_JINJA_TEMPLATE` is a Jinja template that you can use to render the digest

    Find my helpers [here](https://github.com/PrefectHQ/marvin-recipes/blob/main/examples/flows/github_digest.py)

Here's a sample output from August 16th 2023 on the `PrefectHQ/prefect` repo:
```markdown
Greetings, wanderer! Sit, rest your feet, and allow me to regale you with the
heroic deeds of the PrefectHQ/prefect repository on this fateful day, the 16th
of August, 2023.

Our tale begins with the indefatigable jakekaplan, who single-handedly opened 
two perceptive Pull Requests: flow run viz v2 and don't run tasks draft-. Not
satisfied, he also valiantly merged five commits, clearing the path for others
to tread. Meanwhile, cicdw, desertaxle, and serinamarie, each merged a single,
but significant commit, contributing their mite to the collective effort.

In the realm of PRs, prefectcboyd, WillRaphaelson, and bunchesofdonald all 
unfurled their banners, each opening a PR of their own, like pioneers staking
their claim on the wild frontiers of code.

In the grand theatre of software development, where victory is measured in merged
commits and opened PRs, these individuals stood tall, their actions resonating 
through the corridors of GitHub. Their names are etched onto the scroll of this 
day, their deeds a testament to their commitment.

So ends the telling of this day's events. Until our paths cross again, wanderer, 
may your code compile and your tests always pass!
```

### Full example:

The full example, with improvements like caching and observability, can be found [here](https://github.com/PrefectHQ/marvin-recipes/blob/main/examples/flows/github_digest.py).
