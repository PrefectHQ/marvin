import pytest
from dirty_equals import IsStr

import marvin
from marvin import Thread
from marvin.agents.actor import get_current_actor
from marvin.agents.agent import Agent
from marvin.agents.team import RandomTeam, Swarm, Team


async def test_team_initialization():
    """Test basic team initialization."""
    agent1 = Agent(name="Agent 1")
    agent2 = Agent(name="Agent 2")
    team = Team(members=[agent1, agent2])

    assert len(team.members) == 2
    assert agent1 in team.members
    assert agent2 in team.members
    assert team.active_member is agent1  # First agent is active by default
    assert team.delegates == {}


async def test_team_empty_members():
    """Test that team requires at least one member."""
    with pytest.raises(ValueError, match="Team must have at least one member"):
        Team(members=[])


async def test_team_friendly_name():
    """Test team friendly name generation."""
    agent = Agent(name="Test Agent")
    team = Team(members=[agent])

    # Team should use active member's friendly name
    assert team.friendly_name() == agent.friendly_name()
    assert team.friendly_name(verbose=False) == agent.friendly_name(verbose=False)


async def test_team_context_management():
    """Test team context management."""
    agent1 = Agent(name="Agent 1")
    agent2 = Agent(name="Agent 2")
    team = Team(members=[agent1, agent2])

    # Outside context - no current actor
    assert get_current_actor() is None

    # Inside team context - get_current_actor() should return the active agent
    with team:
        # get_current_actor() should return the leaf agent (agent1)
        assert get_current_actor() is agent1

    # Outside context - no current actor
    assert get_current_actor() is None


async def test_nested_teams_context():
    """Test context management with nested teams."""
    # Create a structure of teams and agents:
    # team1
    #  └── team2
    #       └── agent

    agent = Agent(name="Agent")
    team2 = Team(members=[agent])
    team1 = Team(members=[team2])

    # Outside context - no current actor
    assert get_current_actor() is None

    # Inside nested team context
    with team1:
        # get_current_actor() should return the leaf agent
        assert get_current_actor() is agent

        # The active_member chain should go through all teams down to the agent
        assert team1.active_member is team2
        assert team2.active_member is agent

    # Outside context - no current actor
    assert get_current_actor() is None


async def test_team_of_teams():
    """Test a team composed entirely of other teams."""
    agent1 = Agent(name="Agent 1")
    agent2 = Agent(name="Agent 2")

    team1 = Team(members=[agent1])
    team2 = Team(members=[agent2])

    # Create a team composed of other teams
    team_of_teams = Team(members=[team1, team2])

    # The active_member should chain all the way down to an agent
    assert team_of_teams.active_member is team1
    assert team_of_teams.get_memories() == agent1.get_memories()

    with team_of_teams:
        # get_current_actor() should return the leaf agent (agent1)
        assert get_current_actor() is agent1

    # Change the active member and verify the chain
    team_of_teams.active_member = team2
    assert team_of_teams.get_memories() == agent2.get_memories()

    with team_of_teams:
        # get_current_actor() should now return agent2
        assert get_current_actor() is agent2


async def test_team_get_memories():
    """Test that team returns active member's memories."""
    agent1 = Agent(name="Agent 1", memories=[marvin.Memory(key="memory1")])
    agent2 = Agent(name="Agent 2", memories=[marvin.Memory(key="memory2")])
    team = Team(members=[agent1, agent2])

    # Should return active member's memories (agent1)
    assert team.get_memories() == agent1.get_memories()

    # Change active member
    team.active_member = agent2
    assert team.get_memories() == agent2.get_memories()


async def test_team_get_prompt():
    """Test team prompt generation."""
    agent = Agent(name="Test Agent")
    team = Team(members=[agent])

    prompt = team.get_prompt()
    assert isinstance(prompt, str)
    assert team.name in prompt


async def test_swarm_initialization():
    """Test swarm initialization and delegation setup."""
    agent1 = Agent(name="Agent 1")
    agent2 = Agent(name="Agent 2")
    agent3 = Agent(name="Agent 3")

    swarm = Swarm(members=[agent1, agent2, agent3])

    # Swarm should set up delegation between all members
    assert len(swarm.delegates) == 3
    assert agent2 in swarm.delegates[agent1]
    assert agent3 in swarm.delegates[agent1]
    assert agent1 in swarm.delegates[agent2]
    assert agent3 in swarm.delegates[agent2]
    assert agent1 in swarm.delegates[agent3]
    assert agent2 in swarm.delegates[agent3]

    # Each agent should not delegate to itself
    assert agent1 not in swarm.delegates[agent1]
    assert agent2 not in swarm.delegates[agent2]
    assert agent3 not in swarm.delegates[agent3]


async def test_random_team_initialization():
    """Test random team initialization."""
    agent1 = Agent(name="Agent 1")
    agent2 = Agent(name="Agent 2")

    random_team = RandomTeam(members=[agent1, agent2])
    assert (
        random_team.description
        == "A team of agents that randomly selects an agent to act."
    )


class TestTeamVerbose:
    @pytest.fixture
    def thread(self) -> marvin.Thread:
        return marvin.Thread()

    async def test_team_verbose_setting(self):
        """Test that teams can be created with verbose=True."""
        agent = Agent(name="Test Agent")
        team = Team(members=[agent], verbose=True)
        assert team.verbose
        # The team's verbosity doesn't automatically make the member verbose
        assert not agent.verbose

    async def test_team_start_turn_delegates_to_member(self, thread: Thread):
        """Test that team.start_turn delegates to the active member."""
        agent = Agent(name="Test Agent")
        team = Team(members=[agent])

        # Even with verbose=True on the team, no messages are added by the team itself
        team.verbose = True
        await team.start_turn(thread=thread)
        messages = await thread.get_messages_async()

        # No messages because the member isn't verbose
        assert len(messages) == 0

        # When the member is verbose, it adds messages
        agent.verbose = True
        await team.start_turn(thread=thread)
        messages = await thread.get_messages_async()

        # Should have one message from the verbose member
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^ACTOR UPDATE: .* has started its turn\.$"
        )

    async def test_team_end_turn_delegates_to_member(self, thread: Thread):
        """Test that team.end_turn delegates to the active member."""
        agent = Agent(name="Test Agent")
        team = Team(members=[agent])
        result = type("AgentRunResult", (), {})()

        # Even with verbose=True on the team, no messages are added by the team itself
        team.verbose = True
        await team.end_turn(thread=thread, result=result)
        messages = await thread.get_messages_async()

        # No messages because the member isn't verbose
        assert len(messages) == 0

        # When the member is verbose, it adds messages
        agent.verbose = True
        await team.end_turn(thread=thread, result=result)
        messages = await thread.get_messages_async()

        # Should have one message from the verbose member
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^ACTOR UPDATE: .* has finished its turn\.$"
        )


async def test_random_team_start_turn():
    """Test that random team selects a random member on start_turn."""
    agent1 = Agent(name="Agent 1")
    agent2 = Agent(name="Agent 2")

    random_team = RandomTeam(members=[agent1, agent2])

    # Set initial active member
    random_team.active_member = agent1

    # Mock random.choice to always return agent2
    original_choice = marvin.agents.team.random.choice

    try:
        marvin.agents.team.random.choice = lambda x: agent2

        # Start turn should change active member to agent2
        thread = Thread()
        await random_team.start_turn(thread=thread)

        assert random_team.active_member is agent2
    finally:
        # Restore original random.choice
        marvin.agents.team.random.choice = original_choice


async def test_team_delegation():
    """Test team delegation setup."""
    agent1 = Agent(name="Agent 1")
    agent2 = Agent(name="Agent 2")

    # Create a team with explicit delegation
    team = Team(members=[agent1, agent2], delegates={agent1: [agent2]})

    # agent1 should be able to delegate to agent2
    assert agent2 in team.delegates[agent1]

    # But agent2 should not be able to delegate to agent1 by default
    assert agent1 not in team.delegates.get(agent2, [])

    # Get end turn tools should include delegation tools
    assert len(team.get_end_turn_tools()) == 1

    # No delegation tools when agent2 is active (no delegates configured)
    team.active_member = agent2
    assert len(team.get_end_turn_tools()) == 0

    # Delegation tools when agent1 is active (can delegate to agent2)
    team.active_member = agent1
    assert len(team.get_end_turn_tools()) == 1
