import typer
from typer.testing import CliRunner

from typerdrive.config import TyperdriveConfig
from typerdrive.info import add_info_subcommand


def make_cli() -> typer.Typer:
    cli = typer.Typer()
    add_info_subcommand(cli)
    return cli


def test_version_command_shows_app_name_and_version(monkeypatch):
    config = TyperdriveConfig(app_name="test-app", version="1.2.3", description="A test app")
    monkeypatch.setattr("typerdrive.info.get_typerdrive_config", lambda: config)

    result = CliRunner().invoke(make_cli(), ["version"])

    assert result.exit_code == 0
    assert result.stdout == "test-app v1.2.3\n"


def test_version_command_shows_unknown_when_version_is_unset(monkeypatch):
    config = TyperdriveConfig(app_name="test-app")
    monkeypatch.setattr("typerdrive.info.get_typerdrive_config", lambda: config)

    result = CliRunner().invoke(make_cli(), ["version"])

    assert result.exit_code == 0
    assert result.stdout == "test-app (version unknown)\n"


def test_info_command_shows_all_app_metadata(monkeypatch):
    config = TyperdriveConfig(app_name="test-app", version="1.2.3", description="A test app")
    monkeypatch.setattr("typerdrive.info.get_typerdrive_config", lambda: config)

    result = CliRunner().invoke(make_cli(), ["info"])

    assert result.exit_code == 0
    assert "App Information" in result.stdout
    assert "Name" in result.stdout
    assert "test-app" in result.stdout
    assert "Version" in result.stdout
    assert "1.2.3" in result.stdout
    assert "Description" in result.stdout
    assert "A test app" in result.stdout
    assert "Typerdrive Config" not in result.stdout


def test_info_full_shows_effective_typerdrive_config(monkeypatch):
    config = TyperdriveConfig(
        app_name="test-app",
        version="1.2.3",
        description="A test app",
        log_file_name="custom.log",
        console_width=90,
        console_ascii_only=True,
    )
    monkeypatch.setattr("typerdrive.info.get_typerdrive_config", lambda: config)

    result = CliRunner().invoke(make_cli(), ["info", "--full"])

    assert result.exit_code == 0
    assert "Typerdrive Config" in result.stdout
    assert "App Information" not in result.stdout
    assert result.stdout.count("app_name") == 1
    assert result.stdout.count("version") == 1
    assert result.stdout.count("description") == 1
    assert result.stdout.count("1.2.3") == 1
    assert result.stdout.count("A test app") == 1
    assert "custom.log" in result.stdout
    assert "console_width" in result.stdout
    assert "90" in result.stdout
    assert "log_dir" in result.stdout
    assert "cache_dir" in result.stdout
    assert "database_path" in result.stdout


def test_terse_version_prints_only_unformatted_version(monkeypatch):
    config = TyperdriveConfig(app_name="test-app", version="1.2.3", description="A test app")
    monkeypatch.setattr("typerdrive.info.get_typerdrive_config", lambda: config)

    result = CliRunner().invoke(make_cli(), ["version", "--terse"])

    assert result.exit_code == 0
    assert result.stdout == "1.2.3\n"


def test_terse_version_uses_unknown_when_version_is_unset(monkeypatch):
    config = TyperdriveConfig(app_name="test-app")
    monkeypatch.setattr("typerdrive.info.get_typerdrive_config", lambda: config)

    result = CliRunner().invoke(make_cli(), ["version", "--terse"])

    assert result.exit_code == 0
    assert result.stdout == "unknown\n"


def test_info_does_not_accept_short_option():
    result = CliRunner().invoke(make_cli(), ["info", "--short"])

    assert result.exit_code == 2
