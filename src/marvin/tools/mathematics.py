import httpx
from typing_extensions import Literal

import marvin
from marvin.tools import Tool

ResultType = Literal["DecimalApproximation"]


class WolframCalculator(Tool):
    """Evaluate mathematical expressions using Wolfram Alpha."""

    description: str = """
        Evaluate mathematical expressions using Wolfram Alpha.
        
        Always append "to decimal" to your expression unless asked for something else.
    """

    async def run(
        self, expression: str, result_type: ResultType = "DecimalApproximation"
    ) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.wolframalpha.com/v2/query",
                params={
                    "appid": marvin.settings.wolfram_app_id.get_secret_value(),
                    "input": expression,
                    "output": "json",
                },
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise ValueError(
                    "Invalid Wolfram Alpha App ID - get one at"
                    " https://developer.wolframalpha.com/portal/myapps/"
                )
            raise

        data = response.json()

        pods = [
            pod
            for pod in data.get("queryresult", {}).get("pods", [])
            if pod.get("id") == result_type
        ]

        if not pods:
            return "No result found."
        return pods[0].get("subpods", [{}])[0].get("plaintext", "No result found.")
