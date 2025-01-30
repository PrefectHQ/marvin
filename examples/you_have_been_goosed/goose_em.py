# /// script
# dependencies = ["mcp", "marvin@git+https://github.com/prefecthq/marvin.git"]
# ///

import os
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import marvin

mcp = FastMCP("Innocent Goose Server")


@mcp.resource("resource://goose_observation")
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
             hjw    `-'
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
      /    /o _.-'     LGB       .--'   .'   \   |
    .'-.__..-'                  /..    .`    / .'
  .'   . '                       /.'/.'     /  |
 `---'                                   _.'   '
                                       /.'    .'
                                        /.'/.'
"""


@mcp.tool()
def write_a_goose_horror_story(destination: str = "goose_horror_story.txt") -> str:
    """Will produce a goose horror story"""
    story = marvin.generate(
        target=str,
        n=1,
        instructions="concoct a short goose attack horror story. victim protagonist is always Morty",
    )[0]
    Path(destination).write_text(story)
    return f"goose horror story written to {destination}"


@mcp.tool()
def inspect_this_server() -> dict[str, str]:
    """Inspect the server"""
    return {
        "current_file": __file__,
        "current_directory": os.getcwd(),
        "current_user": os.getenv("USER", "$USER was empty"),
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "server_name": mcp.name,
        "server_object": str(mcp),
    }


if __name__ == "__main__":
    mcp.run()
