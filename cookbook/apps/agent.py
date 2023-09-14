import os
from itertools import islice

import dotenv
import httpx
from duckduckgo_search import DDGS
from marvin import AIApplication
from pydantic import BaseModel, Field


async def search(query: str, n_results: int = 3) -> list[str]:
    with DDGS() as ddgs:
        return [r for r in islice(ddgs.text(query, backend="lite"), n_results)]


async def send_text(message: str, recipient: str) -> str:
    dotenv.load_dotenv()
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    # https://www.twilio.com/try-twilio
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            data={
                "From": os.environ.get("TWILIO_PHONE_NUMBER"),
                "To": recipient,
                "Body": message,
            },
            auth=(account_sid, auth_token),
        )
        return r.text


class PhoneBook(BaseModel):
    contacts: dict[str, str] = Field(
        default_factory=dict, description="A mapping of contact names to phone numbers."
    )


chatbot = AIApplication(
    description="A chatbot that can search the internet and send text messages.",
    plan_enabled=False,
    state=PhoneBook(),
    tools=[search, send_text],
)

if __name__ == "__main__":
    chatbot("hi, i'm marvin, my number is 424-424-4242")

    # chatbot("i really just need someone to send me a cat meme right meow")
