from marvin import ai_fn
from marvin.utilities.slack import post_slack_message
from prefect import task
from prefect.blocks.system import JSON, Secret, String
from prefect.exceptions import ObjectNotFound

"""
Define a map between keywords and the relationships we want to check for
in a given message related to that keyword.
"""

keywords = (
    ("429", "rate limit"),
    ("SSO", "Single Sign On", "RBAC", "Roles", "Role Based Access Controls"),
)

relationships = (
    "The user is getting rate limited",
    "The user is asking about a paid feature",
)


async def get_reduced_kw_relationship_map() -> dict:
    try:
        json_map = (await JSON.load("keyword-relationship-map")).value
    except (ObjectNotFound, ValueError):
        json_map = {"keywords": keywords, "relationships": relationships}
        await JSON(value=json_map).save("keyword-relationship-map")

    return {
        keyword: relationship
        for keyword_tuple, relationship in zip(
            json_map["keywords"], json_map["relationships"]
        )
        for keyword in keyword_tuple
    }


@ai_fn
def activation_score(message: str, keyword: str, target_relationship: str) -> float:
    """Return a score between 0 and 1 indicating whether the target relationship exists
    between the message and the keyword"""


@task
async def handle_keywords(message: str, channel_name: str, asking_user: str, link: str):
    keyword_relationships = await get_reduced_kw_relationship_map()
    keywords = [
        keyword for keyword in keyword_relationships.keys() if keyword in message
    ]
    for keyword in keywords:
        target_relationship = keyword_relationships.get(keyword)
        if not target_relationship:
            continue
        score = activation_score(message, keyword, target_relationship)
        if score > 0.5:
            await post_slack_message(
                message=(
                    f"A user ({asking_user}) just asked a question in"
                    f" {channel_name} that contains the keyword `{keyword}`, and I'm"
                    f" {score*100:.0f}% sure that their message indicates the"
                    f" following:\n\n**{target_relationship!r}**.\n\n[Go to"
                    f" message]({link})"
                ),
                channel_id=(await String.load("ask-marvin-tests-channel-id")).value,
                auth_token=(await Secret.load("slack-api-token")).get(),
            )
            return
