import asyncio
from enum import Enum

import marvin


class CustomerDissatisfaction(Enum):
    IMPERCEPTIBLE = 0
    MINIMAL = 1
    MODERATE = 2
    SUBSTANTIAL = 3
    EXTREME = 4


async def bucket_criticism(feedbacks: list[str]) -> list[CustomerDissatisfaction]:
    return await asyncio.gather(
        *[
            marvin.classify_async(
                feedback,
                labels=CustomerDissatisfaction,
                instructions="Decide how bad the customer's experience was",
            )
            for feedback in feedbacks
        ]
    )


if __name__ == "__main__":
    customer_feedbacks: list[str] = [
        "I really appreciated your service 🙂",
        "Your hold music made my ears bleed, but eventually got what I needed",
        "Your support team is the Enron of customer service",
    ]

    print(asyncio.run(bucket_criticism(customer_feedbacks)))
