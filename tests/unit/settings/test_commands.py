import json
from pathlib import Path

import typer
from auto_name_enum import AutoNameEnum, LowerCaseMixin, auto
from pydantic import BaseModel
from typerdrive.constants import ExitCode
from typerdrive.settings.commands import add_bind, add_reset, add_settings_subcommand, add_show, add_unset, add_update

from tests.unit.helpers import match_help, match_output
from tests.unit.settings.models import DefaultSettingsModel, RequiredFieldsModel, SecretFieldsModel, SecretFieldsModel


class Faction(AutoNameEnum, LowerCaseMixin):
    REBEL = auto()
    EMPIRE = auto()
    NEUTRAL = auto()


class TestBind:
    def test_bind__updates_settings_with_cli_args(self, fake_settings_path: Path):
        cli = typer.Typer()

        add_bind(cli, RequiredFieldsModel)

        expected_pattern = [
            "name.*hutt",
            "planet.*nal hutta",
            "is-humanoid.*False",
            "alignment.*neutral",
            f"saved to {str(fake_settings_path)[:40]}",
        ]
        match_output(
            cli,
            "--name=hutt",
            "--planet=nal hutta",
            "--no-is-humanoid",
            expected_pattern=expected_pattern,
            prog_name="test",
        )

        assert fake_settings_path.exists()
        data = json.loads(fake_settings_path.read_text())
        assert data == dict(
            name="hutt",
            planet="nal hutta",
            is_humanoid=False,
            alignment="neutral",
        )

    def test_bind__raises_exception_if_final_config_is_not_valid(self):
        cli = typer.Typer()

        add_bind(cli, RequiredFieldsModel)

        match_output(
            cli,
            "--name=hutt",
            "--planet=nal hutta",
            "--alignment=invalid-alignment",
            exit_code=ExitCode.GENERAL_ERROR,
            expected_pattern=[
                "Failed to bind settings",
                "Final settings are invalid",
                "RequiredFieldsModel",
                "invalid-alignment is an invalid alignment",
            ],
            prog_name="test",
        )

    def test_bind__help_text(self):
        cli = typer.Typer()

        add_bind(cli, RequiredFieldsModel)

        expected_pattern = [
            "Options",
            r"--name TEXT \[default: None\] \[required\]",
            r"--planet TEXT \[default: None\] \[required\]",
            r"--is-humanoid --no-is-humanoid  \[default: is-humanoid\]",
            r"--alignment TEXT \[default: neutral\]",
        ]
        match_help(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )

    def test_bind__with_single_nested_pydantic_models(self, fake_settings_path: Path):
        cli = typer.Typer()

        class Planet(BaseModel):
            name: str
            climate: str

        class Settings(BaseModel):
            name: str
            planet: Planet

        add_bind(cli, Settings)

        expected_pattern = [
            "name.*jawa",
            "planet.*name='tatooine' climate='desert'",
            f"saved to {str(fake_settings_path)[:40]}",
        ]
        match_output(
            cli,
            "--name=jawa",
            """--planet={"name": "tatooine", "climate": "desert"}""",
            expected_pattern=expected_pattern,
            prog_name="test",
        )

        assert fake_settings_path.exists()
        data = json.loads(fake_settings_path.read_text())
        assert data == dict(
            name="jawa",
            planet=dict(
                name="tatooine",
                climate="desert",
            ),
        )

    def test_bind__with_multiple_nested_pydantic_models(self, fake_settings_path: Path):
        cli = typer.Typer()

        class Planet(BaseModel):
            name: str
            climate: str

        class Coloration(BaseModel):
            eyes: str
            hair: str

        class Settings(BaseModel):
            name: str
            planet: Planet
            coloration: Coloration

        add_bind(cli, Settings)

        expected_pattern = [
            "name.*jawa",
            "planet.*name='tatooine' climate='desert'",
            "coloration.*eyes='yellow' hair='black'",
            f"saved to {str(fake_settings_path)[:40]}",
        ]
        match_output(
            cli,
            "--name=jawa",
            """--planet={"name": "tatooine", "climate": "desert"}""",
            """--coloration={"eyes": "yellow", "hair": "black"}""",
            expected_pattern=expected_pattern,
            prog_name="test",
        )

        assert fake_settings_path.exists()
        data = json.loads(fake_settings_path.read_text())
        assert data == dict(
            name="jawa",
            planet=dict(
                name="tatooine",
                climate="desert",
            ),
            coloration=dict(
                eyes="yellow",
                hair="black",
            ),
        )

    def test_bind__with_auto_name_enum_default(self, fake_settings_path: Path):
        class Settings(BaseModel):
            name: str = "jawa"
            faction: Faction = Faction.NEUTRAL

        cli = typer.Typer()
        add_bind(cli, Settings)

        match_output(
            cli,
            "--name=jawa",
            "--faction=rebel",
            expected_pattern=[
                "name.*jawa",
                "faction.*rebel",
                f"saved to {str(fake_settings_path)[:40]}",
            ],
            prog_name="test",
        )

        assert fake_settings_path.exists()
        data = json.loads(fake_settings_path.read_text())
        assert data == dict(name="jawa", faction="rebel")


class TestUpdate:
    def test_update__updates_settings_with_cli_args(self, fake_settings_path: Path):
        cli = typer.Typer()

        add_update(cli, DefaultSettingsModel)

        expected_pattern = [
            "name.*hutt",
            "planet.*tatooine",
            "is-humanoid.*True",
            "alignment.*neutral",
            f"saved to {str(fake_settings_path)[:40]}",
        ]
        match_output(
            cli,
            "--name=hutt",
            expected_pattern=expected_pattern,
            prog_name="test",
        )

        assert fake_settings_path.exists()
        data = json.loads(fake_settings_path.read_text())
        assert data == dict(
            name="hutt",
            planet="tatooine",
            is_humanoid=True,
            alignment="neutral",
        )

    def test_update__does_not_fail_with_invalid_settings(self, fake_settings_path: Path):
        cli = typer.Typer()

        add_update(cli, RequiredFieldsModel)

        expected_pattern = [
            "name str -> hutt",
            "planet str -> <UNSET>",
            "is-humanoid bool -> True",
            "alignment str -> neutral",
            "Invalid Values",
            "planet -> Field required",
            f"saved to {str(fake_settings_path)[:40]}",
        ]
        match_output(
            cli,
            "--name=hutt",
            expected_pattern=expected_pattern,
            prog_name="test",
        )

    def test_update__help_text(self):
        cli = typer.Typer()

        add_update(cli, RequiredFieldsModel)

        expected_pattern = [
            "Options",
            r"--name TEXT \[default: None\]",
            r"--planet TEXT \[default: None\]",
            r"--is-humanoid",  # NOTE: This doesn't match typer docs. It should show a default
            r"--alignment TEXT \[default: None\]",
        ]
        match_help(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )

    def test_update__with_nested_pydantic_models(self, fake_settings_path: Path):
        cli = typer.Typer()

        class Nested(BaseModel):
            name: str
            planet: str

        class Settings(BaseModel):
            nested: Nested

        add_update(cli, Settings)

        expected_pattern = [
            "nested.*name='jawa' planet='tatooine'",
            f"saved to {str(fake_settings_path)[:40]}",
        ]
        match_output(
            cli,
            """--nested={"name": "jawa", "planet": "tatooine"}""",
            expected_pattern=expected_pattern,
            prog_name="test",
        )

        assert fake_settings_path.exists()
        data = json.loads(fake_settings_path.read_text())
        assert data == dict(
            nested=dict(
                name="jawa",
                planet="tatooine",
            ),
        )


class TestUnset:
    def test_unset__unsets_fields_with_cli_args(self, fake_settings_path: Path):
        fake_settings_path.write_text(
            json.dumps(
                dict(
                    name="pyke",
                    planet="oba diah",
                    is_humanoid=True,
                    alignment="evil",
                ),
            ),
        )

        cli = typer.Typer()

        add_unset(cli, RequiredFieldsModel)

        expected_pattern = [
            "name.*pyke",
            "planet.*oba diah",
            "is-humanoid.*True",
            "alignment.*neutral",
            f"saved to {str(fake_settings_path)[:40]}",
        ]
        match_output(
            cli,
            "--alignment",
            expected_pattern=expected_pattern,
            prog_name="test",
        )

        assert fake_settings_path.exists()
        data = json.loads(fake_settings_path.read_text())
        assert data == dict(
            name="pyke",
            planet="oba diah",
            is_humanoid=True,
            alignment="neutral",
        )

    def test_unset__does_not_fail_with_invalid_settings(self, fake_settings_path: Path):
        fake_settings_path.write_text(
            json.dumps(
                dict(
                    name="pyke",
                    planet="oba diah",
                    is_humanoid=True,
                    alignment="evil",
                ),
            ),
        )

        cli = typer.Typer()

        add_unset(cli, RequiredFieldsModel)

        expected_pattern = [
            "name str -> <UNSET>",
            "planet str -> <UNSET>",
            "is-humanoid bool -> True",
            "alignment str -> evil",
            "Invalid Values",
            "name -> Field required",
            "planet -> Field required",
            f"saved to {str(fake_settings_path)[:40]}",
        ]
        match_output(
            cli,
            "--name",
            "--planet",
            expected_pattern=expected_pattern,
            prog_name="test",
        )

    def test_unset__help_text(self):
        cli = typer.Typer()

        add_unset(cli, RequiredFieldsModel)

        expected_pattern = [
            "Options",
            r"--name (?! \[default)",
            r"--planet (?! \[default)",
            r"--is-humanoid (?! \[default)",
            r"--alignment (?! \[default)",
        ]
        match_help(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )


class TestShow:
    def test_show__shows_settings(self):
        cli = typer.Typer()

        add_show(cli, DefaultSettingsModel)

        expected_pattern = [
            "name.*jawa",
            "planet.*tatooine",
            "is-humanoid.*True",
            "alignment.*neutral",
        ]
        match_output(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )

    def test_show__help_text(self):
        cli = typer.Typer()

        add_show(cli, RequiredFieldsModel)

        expected_pattern = [
            r"name",
            r"planet",
            r"is-humanoid",
            r"alignment",
        ]
        match_help(
            cli,
            unwanted_pattern=expected_pattern,
            prog_name="test",
        )


class TestReset:
    def test_reset__resets_all_fields_to_defaults(self, fake_settings_path: Path):
        fake_settings_path.write_text(
            json.dumps(
                dict(
                    name="pyke",
                    planet="oba diah",
                    is_humanoid=True,
                    alignment="evil",
                ),
            ),
        )

        cli = typer.Typer()

        add_reset(cli, RequiredFieldsModel)

        expected_pattern = [
            "name str -> <UNSET>",
            "planet str -> <UNSET>",
            "is-humanoid bool -> True",
            "alignment str -> neutral",
            "Invalid Values",
            "name -> Field required",
            "planet -> Field required",
            f"saved to {str(fake_settings_path)[:40]}",
        ]
        match_output(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
            input="y",
        )

        assert fake_settings_path.exists()
        data = json.loads(fake_settings_path.read_text())
        assert data == dict(
            is_humanoid=True,
            alignment="neutral",
        )

    def test_reset__help_text(self):
        cli = typer.Typer()

        add_reset(cli, RequiredFieldsModel)

        expected_pattern = [
            r"name",
            r"planet",
            r"is-humanoid",
            r"alignment",
        ]
        match_help(
            cli,
            unwanted_pattern=expected_pattern,
            prog_name="test",
        )


class TestSubcommand:
    def test_add_settings_subcommand(self):
        cli = typer.Typer()

        add_settings_subcommand(cli, RequiredFieldsModel)

        expected_pattern = [
            r"settings.*Manage settings for the app",
        ]
        match_help(
            cli,
            expected_pattern=expected_pattern,
            prog_name="test",
        )

        expected_pattern = [
            "bind",
            "update",
            "unset",
            "reset",
            "show",
        ]
        match_output(
            cli,
            "settings",
            "--help",
            exit_code=0,
            expected_pattern=expected_pattern,
            prog_name="test",
        )

    def test_add_settings_subcommand__no_args_shows_help(self):
        cli = typer.Typer()

        add_settings_subcommand(cli, RequiredFieldsModel)

        expected_pattern = [
            "bind",
            "update",
            "unset",
            "reset",
            "show",
        ]
        match_output(
            cli,
            "settings",
            exit_code=0,
            expected_pattern=expected_pattern,
            prog_name="test",
        )


class TestSecretFields:
    """
    Typer does not support `pydantic.SecretStr` as a CLI parameter type — passing it directly
    raises `RuntimeError: Type not yet supported`.  The fix in `commands.py` substitutes `str`
    so Typer can build the command tree, while `SettingsManager` continues to round-trip the
    values through `SecretStr` when persisting to / loading from disk.
    """

    def test_bind__does_not_raise_on_registration(self):
        """add_bind must not crash when the model contains SecretStr fields."""
        cli = typer.Typer()
        # Previously raised: RuntimeError: Type not yet supported: <class 'pydantic.types.SecretStr'>
        add_bind(cli, SecretFieldsModel)

    def test_bind__help_shows_secret_fields_as_text(self):
        """SecretStr fields must appear as TEXT options in --help output."""
        cli = typer.Typer()
        add_bind(cli, SecretFieldsModel)

        match_help(
            cli,
            expected_pattern=[
                r"--name TEXT",
                r"--api-key TEXT",
                r"--token TEXT",
            ],
            prog_name="test",
        )

    def test_bind__saves_secret_value_as_plain_text_on_disk(self, fake_settings_path: Path):
        """Secret values passed via CLI must be persisted as plain strings, not masked."""
        cli = typer.Typer()
        add_bind(cli, SecretFieldsModel)

        match_output(
            cli,
            "--name=han",
            "--api-key=s3cr3t",
            "--token=tok123",
            expected_pattern=[f"saved to {str(fake_settings_path)[:40]}"],
            prog_name="test",
        )

        data = json.loads(fake_settings_path.read_text())
        assert data == dict(name="han", api_key="s3cr3t", token="tok123")

    def test_bind__secretstr_default_does_not_crash_registration(self):
        """A SecretStr field with a default value must not crash CLI registration."""
        cli = typer.Typer()
        # SecretFieldsModel.token has default=SecretStr("default-token")
        add_bind(cli, SecretFieldsModel)
        match_help(cli, expected_pattern=[r"--token TEXT"], prog_name="test")

    def test_update__does_not_raise_on_registration(self):
        """add_update must not crash when the model contains SecretStr fields."""
        cli = typer.Typer()
        add_update(cli, SecretFieldsModel)

    def test_update__saves_updated_secret_as_plain_text_on_disk(self, fake_settings_path: Path):
        """Updating a single secret field must persist the new plain-text value while leaving others intact."""
        fake_settings_path.write_text(json.dumps(dict(name="han", api_key="old-key", token="old-tok")))

        cli = typer.Typer()
        add_update(cli, SecretFieldsModel)

        match_output(
            cli,
            "--api-key=new-key",
            expected_pattern=[f"saved to {str(fake_settings_path)[:40]}"],
            prog_name="test",
        )

        data = json.loads(fake_settings_path.read_text())
        assert data["api_key"] == "new-key"
        assert data["token"] == "old-tok"  # unchanged

    def test_add_settings_subcommand__does_not_raise_on_registration(self):
        """add_settings_subcommand must build the full command tree without crashing."""
        cli = typer.Typer()
        add_settings_subcommand(cli, SecretFieldsModel)

    def test_add_settings_subcommand__top_level_help_does_not_raise(self):
        """`--help` at the top level must exit cleanly when settings contain SecretStr fields."""
        cli = typer.Typer()
        add_settings_subcommand(cli, SecretFieldsModel)

        match_help(
            cli,
            expected_pattern=[r"settings.*Manage settings for the app"],
            prog_name="test",
        )
