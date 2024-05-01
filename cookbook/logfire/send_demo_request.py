import asyncio
import json

import httpx


async def main():
    candidates = [
        {
            "name": "Alice",
            "self_identified_seniority": "3",
            "bio": "10 years with postgres, 5 years with python, 3 years with django.",
        },
        {
            "name": "Bob",
            "self_identified_seniority": "1",
            "bio": "I just graduated from a coding bootcamp and I'm ready to take on the world!",
        },
        {
            "name": "Charlie",
            "self_identified_seniority": "2",
            "bio": "graduated 2 years ago and i can make you a react app in no time",
        },
        {
            "name": "David",
            "self_identified_seniority": "3",
            "bio": "i just been riding that SCRUM wave for 10 years fam",
        },
    ]

    role = {
        "title": "Senior Software Engineer",
        "desired_seniority": "3",
        "description": "Build and maintain a large-scale web application with a team of 10+ engineers.",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/interview",
            json={"candidates": candidates, "role": role},
        )
        result = response.json()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
