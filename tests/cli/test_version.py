from typer.testing import CliRunner


def test_marvin_version_command():
    """Test the marvin version command."""
    from marvin.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "Version:" in result.output
    assert "Python version:" in result.output
    assert "OS/Arch:" in result.output
