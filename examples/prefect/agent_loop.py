from secrets import token_hex

from prefect import flow

from marvin.beta import PrefectAgent

_KEY = token_hex(4)


def get_key() -> str:
    """Get the key to the door."""
    return _KEY


def open_door(key: str) -> str:
    """Open the door with the given key.

    If the key is right, the secret will be returned. Otherwise, an error will be raised.
    """
    if key != _KEY:
        raise ValueError("wrong key")
    return "tiny acorns become mighty oaks"


@flow()
def run_agent_loop():
    agent = PrefectAgent(
        tools=[get_key, open_door],
        instructions="use provided tools to help the user",
        model="gpt-4o",
    )

    result = agent.run("open the door")
    print(result)


if __name__ == "__main__":
    run_agent_loop()
