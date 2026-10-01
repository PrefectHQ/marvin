from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from slackbot.search import check_cli_command


def test_deployment_help_keeps_scheduling_options(capsys):
    with patch(
        "slackbot.search.subprocess.run", side_effect=AssertionError("spawned process")
    ):
        help_text = check_cli_command("prefect deployment run", ["--help"])
    assert "--start-at" in help_text
    assert "--watch-timeout" in help_text
    assert capsys.readouterr().out == ""


def test_concurrent_help_checks_do_not_invoke_callbacks():
    commands = ["deploy", "worker start", "work-pool create", "server start"]
    with (
        patch("click.Command.invoke", side_effect=AssertionError("invoked command")),
        patch(
            "slackbot.search.subprocess.run",
            side_effect=AssertionError("spawned process"),
        ),
        ThreadPoolExecutor(max_workers=4) as pool,
    ):
        results = list(
            pool.map(
                lambda cmd: check_cli_command(f"prefect {cmd}", ["--help"]), commands
            )
        )
    for command, result in zip(commands, results):
        assert f"Usage: prefect {command}" in result


@pytest.mark.parametrize(
    "command",
    ["prefect made-up", "prefect deployment made-up", "prefect deployment run extra"],
)
def test_unknown_command_is_not_reported_as_verified(command):
    assert check_cli_command(command, ["--help"]).startswith("Unknown Prefect command:")


def test_prefect_action_arguments_cannot_execute_a_mutation():
    with patch(
        "slackbot.search.subprocess.run", side_effect=AssertionError("spawned process")
    ):
        assert "--help only" in check_cli_command(
            "prefect deployment run", ["--id", "anything"]
        )


def test_other_program_preserves_quoted_arguments():
    with patch("slackbot.search.subprocess.run") as run:
        run.return_value.stdout = "help"
        run.return_value.stderr = ""
        assert check_cli_command('python -c "print(1 + 2)"') == "help"
    assert run.call_args.args[0] == ["python", "-c", "print(1 + 2)"]
