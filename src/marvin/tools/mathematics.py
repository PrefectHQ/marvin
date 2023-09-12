# This module provides a tool for evaluating math expressions using Wolfram Alpha
# It uses the Wolfram Alpha API to send a query and retrieve the result.
# The main class is WolframCalculator which inherits from the Tool class.
# The run method of WolframCalculator takes an expression and a result type as input,
# sends a request to the Wolfram Alpha API, and returns the result.

from typing import Literal

import httpx

import marvin
from marvin.tools import Tool

# Define the type of result that can be returned by the Wolfram Alpha API
ResultType = Literal["DecimalApproximation"]


class WolframCalculator(Tool):
    """
    A tool to evaluate mathematical expressions using Wolfram Alpha.

    Attributes:
        description (str): A brief description of the tool.
    """

    description: str = """
        Evaluate mathematical expressions using Wolfram Alpha.
        
        Always append "to decimal" to your expression unless asked for something else.
    """

    async def run(  # type: ignore
        self, expression: str, result_type: ResultType = "DecimalApproximation"
    ) -> str:
        """
        Evaluate a mathematical expression using Wolfram Alpha.

        Args:
            expression (str): The mathematical expression to evaluate.
            result_type (ResultType, optional): The type of result to return.
                Defaults to "DecimalApproximation".

        Returns:
            str: The result of the evaluation.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.wolframalpha.com/v2/query",
                params={
                    "appid": marvin.settings.wolfram_app_id.get_secret_value(),  # type: ignore # noqa: E501
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
