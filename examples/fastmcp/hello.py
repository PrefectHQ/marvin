from fastmcp.server import FastMCP

import marvin

server = FastMCP("hello server")


@server.tool()
def get_the_value_of_schleeb() -> int:
    return 42


if __name__ == "__main__":
    agent = marvin.Agent(mcp_servers=[server])
    result = agent.run("What is the value of schleeb?")
    print(result)
