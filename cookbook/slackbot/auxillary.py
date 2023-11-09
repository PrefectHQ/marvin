from prefect.blocks.system import JSON
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


async def get_reduced_kw_relationship_map():
    try:
        json_map = (await JSON.load("keyword-relationship-map")).value
    except ObjectNotFound:
        json_map = {"keywords": keywords, "relationships": relationships}
        await JSON.save(json_map, "keyword-relationship-map")

    return {
        keyword: relationship
        for keyword_tuple, relationship in zip(
            json_map["keywords"], json_map["relationships"]
        )
        for keyword in keyword_tuple
    }
