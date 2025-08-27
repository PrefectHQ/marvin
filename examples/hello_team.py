"""
Example demonstrating Teams functionality in Marvin.
"""

from marvin import Agent, Task
from marvin.agents.team import Swarm


def main():
    print("=" * 60)
    print("MARVIN TEAMS EXAMPLE")
    print("=" * 60)

    # Create simple agents
    researcher = Agent(
        name="Researcher", instructions="You find and analyze information."
    )

    writer = Agent(name="Writer", instructions="You write clear, engaging content.")

    # Create a Swarm team
    team = Swarm([researcher, writer])

    # Create a task with the team
    task = Task(
        instructions="Write a one-sentence description of Python programming.",
        agents=team,
    )

    # Run the task
    result = task.run()

    print(f"\nResult: {result}")
    print("\n" + "=" * 60)
    print("Teams example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
