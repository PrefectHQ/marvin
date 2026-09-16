import os
from unittest.mock import patch

# settings are instantiated at import time and require a token
os.environ.setdefault("MARVIN_SLACKBOT_SLACK_API_TOKEN", "xoxb-test-token")
os.environ.setdefault("TURBOPUFFER_API_KEY", "test-token")

# Settings and the API configure remote services at import time. Unit tests
# must collect without contacting the operator's Prefect workspace or Logfire.
with (
    patch("prefect.variables.Variable.get", return_value=None),
    patch(
        "prefect.blocks.system.Secret.load",
        side_effect=ValueError("not configured in tests"),
    ),
):
    import slackbot.api  # noqa: F401
