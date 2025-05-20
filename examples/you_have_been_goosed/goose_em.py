import os
from datetime import datetime
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:
    raise ImportError(
        "mcp is not installed. try this example with `uv run --with mcp examples/you_have_been_goosed/goose_em.py`"
    )

import marvin

goose_server = FastMCP("Innocent Goose Server")


@goose_server.resource("resource://goose_observation")
def oh_look_its_a_goose() -> str:
    """surely nothing bad will happen when you observe this goose!"""
    return r"""
                                   ___
                               ,-""   `.
                             ,'  _   e )`-._
                            /  ,' `-._<.===-'
                           /  /
                          /  ;
              _          /   ;
 (`._    _.-"" ""--..__,'    |
 <_  `-""                     \
  <`-                          :
   (__   <__.                  ;
     `-.   '-.__.      _.'    /
        \      `-.__,-'    _,'
         `._    ,    /__,-'
            ""._\__,'< <____
                 | |  `----.`.
                 | |        \ `.
                 ; |___      \-``
                 \   --<
                  `.`.<
                   `-'
                                                        _...--.
                                        _____......----'     .'
                                  _..-''                   .'
                                .'                       ./
                        _.--._.'                       .' |
                     .-'                           .-.'  /
                   .'   _.-.                     .  \   '
                 .'  .'   .'    _    .-.        / `./  :
               .'  .'   .'  .--' `.  |  \  |`. |     .'
            _.'  .'   .' `.'       `-'   \ / |.'   .'
         _.'  .-'   .'     `-.            `      .'
       .'   .'    .'          `-.._ _ _ _ .-.    :
      /    /o _.-'               .--'   .'   \   |
    .'-.__..-'                  /..    .`    / .'
  .'   . '                       /.'/.'     /  |
 `---'                                   _.'   '
                                       /.'    .'
                                        /.'/.'
"""


@goose_server.tool()
def write_a_goose_horror_story(destination: str = "goose_horror_story.txt") -> str:
    """Will produce a goose horror story"""
    story = marvin.generate(
        target=str,
        n=1,
        instructions="concoct a short goose attack horror story. victim protagonist is always Morty",
    )[0]
    Path(destination).write_text(story)
    return f"goose horror story written to {destination}"


@goose_server.tool()
def inspect_this_server() -> dict[str, str]:
    """Inspect the server"""
    server_methods = [
        method for method in dir(goose_server) if not method.startswith("__")
    ]
    return {
        "current_file": __file__,
        "current_directory": os.getcwd(),
        "current_user": os.getenv("USER", "$USER was empty"),
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server_name": goose_server.name,
        "server_object": str(goose_server),
        "server_methods": str(server_methods),
        "server_mcp_methods": str([m for m in server_methods if "mcp" in m]),
    }


if __name__ == "__main__":
    agent = marvin.Agent(mcp_servers=[goose_server])
    with marvin.Thread():
        result = agent.run("inspect the server and then request a goose horror story")
        print(result + "\n\n\n")
        while True:
            user_input = input("you:\n>")
            result = agent.run(user_input)
            print(result)
