import json
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, cast

import pytest
import snick
from pydantic import (
    AfterValidator,
    AliasChoices,
    AliasPath,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)
from pytest_mock import MockerFixture
from rich.console import Console
from typerdrive import PlaintextSecretStr
from typerdrive.config import get_typerdrive_config, set_typerdrive_config
from typerdrive.env import tweak_env
from typerdrive.settings.exceptions import SettingsInitError, SettingsSaveError, SettingsUpdateError
from typerdrive.settings.manager import SettingsManager


def valid_alignment(value: str) -> str:
    if value not in ["good", "neutral", "evil"]:
        raise ValueError(f"{value} is an invalid alignment")
    return value


class DefaultSettingsModel(BaseModel):
    name: str = "jawa"
    planet: str = "tatooine"
    is_humanoid: bool = True
    alignment: Annotated[str, AfterValidator(valid_alignment)] = "neutral"


class RequiredFieldsModel(BaseModel):
    name: str
    planet: str
    is_humanoid: bool = True
    alignment: Annotated[str, AfterValidator(valid_alignment)] = "neutral"


class FixedTupleSettings(BaseModel):
    value: tuple[PlaintextSecretStr, int]


class VariadicTupleSettings(BaseModel):
    value: tuple[PlaintextSecretStr, ...]


@pytest.fixture(autouse=True)
def fake_settings_path(tmp_path: Path) -> Generator[Path, None, None]:
    state_home = tmp_path / ".local/state"
    cache_home = tmp_path / ".cache"
    settings_dir = state_home / "test"
    settings_dir.mkdir(parents=True)
    settings_path = settings_dir / "settings.json"
    original_config = get_typerdrive_config()

    with tweak_env(HOME=str(tmp_path), XDG_STATE_HOME=str(state_home), XDG_CACHE_HOME=str(cache_home)):
        set_typerdrive_config(state_home=state_home, cache_home=cache_home)
        try:
            yield settings_path
        finally:
            set_typerdrive_config(**original_config.model_dump())


class TestSettingsManager:
    def test_init__loads_default_model(self):
        manager = SettingsManager(DefaultSettingsModel)
        assert manager.settings_model == DefaultSettingsModel
        assert manager.settings_path == get_typerdrive_config().settings_path
        assert manager.invalid_warnings == {}

        assert isinstance(manager.settings_instance, DefaultSettingsModel)
        assert manager.settings_instance.name == "jawa"
        assert manager.settings_instance.planet == "tatooine"
        assert manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "neutral"

    def test_init__loads_default_model_from_disk(self, fake_settings_path: Path):
        settings_path = fake_settings_path
        settings_path.write_text(
            json.dumps(
                {"name": "hutt", "planet": "nal hutta", "is_humanoid": False, "alignment": "evil"},
            )
        )

        manager = SettingsManager(DefaultSettingsModel)

        assert manager.settings_model == DefaultSettingsModel
        assert manager.settings_path == settings_path
        assert manager.invalid_warnings == {}

        assert isinstance(manager.settings_instance, DefaultSettingsModel)
        assert manager.settings_instance.name == "hutt"
        assert manager.settings_instance.planet == "nal hutta"
        assert not manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "evil"

    def test_init__loads_invalid_model_with_warnings(self):
        manager = SettingsManager(RequiredFieldsModel)
        assert manager.settings_model == RequiredFieldsModel
        assert manager.settings_path == get_typerdrive_config().settings_path
        assert manager.invalid_warnings == {
            "name": "Field required",
            "planet": "Field required",
        }

        assert isinstance(manager.settings_instance, RequiredFieldsModel)
        assert not hasattr(manager.settings_instance, "name")
        assert not hasattr(manager.settings_instance, "planet")
        assert manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "neutral"

    def test_init__loads_invalid_model_from_disk(self, fake_settings_path: Path):
        settings_path = fake_settings_path
        settings_path.write_text(json.dumps({"name": "hutt"}))

        manager = SettingsManager(RequiredFieldsModel)

        assert manager.settings_model == RequiredFieldsModel
        assert manager.settings_path == settings_path
        assert manager.invalid_warnings == {
            "planet": "Field required",
        }

        assert isinstance(manager.settings_instance, RequiredFieldsModel)
        assert manager.settings_instance.name == "hutt"
        assert not hasattr(manager.settings_instance, "planet")
        assert manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "neutral"

    def test_init__raises_error_on_failure(self, mocker: MockerFixture):
        mocker.patch.object(DefaultSettingsModel, "model_validate", side_effect=RuntimeError("BOOM"))
        with pytest.raises(SettingsInitError, match="Failed to initialize settings"):
            SettingsManager(DefaultSettingsModel)

    def test_set_warnings__unpacks_validation_error(self):
        manager = SettingsManager(DefaultSettingsModel)
        err = ValidationError.from_exception_data(
            "BOOM",
            [
                {
                    "type": "missing",
                    "loc": ("name",),
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ("planet",),
                    "input": {},
                },
            ],
        )
        manager.set_warnings(err)

        assert manager.invalid_warnings == {
            "name": "Field required",
            "planet": "Field required",
        }

    def test_update__updates_valid_to_valid_settings(self):
        manager = SettingsManager(DefaultSettingsModel)
        manager.update(planet="nevarro", alignment="good")
        assert isinstance(manager.settings_instance, DefaultSettingsModel)
        assert manager.settings_instance.name == "jawa"
        assert manager.settings_instance.planet == "nevarro"
        assert manager.settings_instance.alignment == "good"
        assert manager.settings_instance.is_humanoid
        assert manager.invalid_warnings == {}

    def test_update__updates_invalid_to_valid_settings(self):
        manager = SettingsManager(RequiredFieldsModel)
        assert len(manager.invalid_warnings) > 0
        manager.update(name="pyke", planet="oba diah")
        assert isinstance(manager.settings_instance, RequiredFieldsModel)
        assert manager.settings_instance.name == "pyke"
        assert manager.settings_instance.planet == "oba diah"
        assert manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "neutral"
        assert manager.invalid_warnings == {}

    def test_update__updates_valid_to_invalid_settings(self):
        manager = SettingsManager(DefaultSettingsModel)
        manager.update(planet="nevarro", alignment="negative")
        assert isinstance(manager.settings_instance, DefaultSettingsModel)
        assert manager.settings_instance.name == "jawa"
        assert manager.settings_instance.planet == "nevarro"
        assert manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "negative"
        assert manager.invalid_warnings == {
            "alignment": "Value error, negative is an invalid alignment",
        }

    def test_update__raises_error_on_failure(self, mocker: MockerFixture):
        manager = SettingsManager(DefaultSettingsModel)
        mocker.patch.object(manager.settings_model, "model_validate", side_effect=RuntimeError("BOOM"))
        with pytest.raises(SettingsUpdateError, match="Failed to update settings"):
            manager.update()

    def test_unset__resets_field_to_default(self):
        manager = SettingsManager(DefaultSettingsModel)
        manager.update(name="pyke", planet="oba diah", alignment="evil")
        assert isinstance(manager.settings_instance, DefaultSettingsModel)
        assert manager.settings_instance.name == "pyke"
        assert manager.settings_instance.planet == "oba diah"
        assert manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "evil"
        assert manager.invalid_warnings == {}
        manager.unset("name", "alignment")
        assert manager.settings_instance.name == "jawa"
        assert manager.settings_instance.planet == "oba diah"
        assert manager.settings_instance.alignment == "neutral"

    def test_unset__adds_warnings_if_field_has_no_default(self):
        manager = SettingsManager(RequiredFieldsModel)
        assert isinstance(manager.settings_instance, RequiredFieldsModel)
        manager.update(name="jawa", planet="tatooine", alignment="neutral")
        assert manager.invalid_warnings == {}
        manager.unset("planet")
        assert manager.settings_instance.name == "jawa"
        assert not hasattr(manager.settings_instance, "planet")
        assert manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "neutral"
        assert manager.invalid_warnings == {
            "planet": "Field required",
        }

    def test_reset__returns_all_fields_to_default(self):
        manager = SettingsManager(DefaultSettingsModel)
        manager.update(name="hutt", planet="nal hutta", is_humanoid=False, alignment="evil")
        assert isinstance(manager.settings_instance, DefaultSettingsModel)
        assert manager.settings_instance.name == "hutt"
        assert manager.settings_instance.planet == "nal hutta"
        assert not manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "evil"
        assert manager.invalid_warnings == {}
        manager.reset()
        assert manager.settings_instance.name == "jawa"
        assert manager.settings_instance.planet == "tatooine"
        assert manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "neutral"

    def test_reset__adds_warnings_for_fields_with_no_defaults(self):
        manager = SettingsManager(RequiredFieldsModel)
        manager.update(name="hutt", planet="nal hutta", is_humanoid=False, alignment="evil")
        assert isinstance(manager.settings_instance, RequiredFieldsModel)
        assert manager.settings_instance.name == "hutt"
        assert manager.settings_instance.planet == "nal hutta"
        assert not manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "evil"
        assert manager.invalid_warnings == {}
        manager.reset()
        assert not hasattr(manager.settings_instance, "name")
        assert not hasattr(manager.settings_instance, "planet")
        assert manager.settings_instance.is_humanoid
        assert manager.settings_instance.alignment == "neutral"
        assert manager.invalid_warnings == {
            "name": "Field required",
            "planet": "Field required",
        }

    def test_pretty__provides_string_reflecting_settings_instance(self):
        manager = SettingsManager(RequiredFieldsModel)
        manager.update(name="pyke", alignment="negative")
        console = Console()
        with console.capture() as snag:
            console.print(manager.pretty())
        computed = snick.strip_trailing_whitespace(snag.get())
        expected = snick.dedent(
            """
            Settings Values

                    name  str   ->  pyke
                  planet  str   ->  <UNSET>
             is-humanoid  bool  ->  True
               alignment  str   ->  negative


            Invalid Values

                planet  ->  Field required
             alignment  ->  Value error, negative is an invalid alignment
            """
        ).strip()
        assert expected == computed

    def test_pretty__does_not_error_with_no_default_fields(self):
        class NoDefaultsModel(BaseModel):
            name: str
            planet: str
            is_humanoid: bool
            alignment: Annotated[str, AfterValidator(valid_alignment)]

        manager = SettingsManager(NoDefaultsModel)
        console = Console()
        with console.capture() as snag:
            console.print(manager.pretty())
        computed = snick.strip_trailing_whitespace(snag.get())
        expected = snick.dedent(
            """
            Settings Values

                    name  str   ->  <UNSET>
                  planet  str   ->  <UNSET>
             is-humanoid  bool  ->  <UNSET>
               alignment  str   ->  <UNSET>


            Invalid Values

                    name  ->  Field required
                  planet  ->  Field required
             is-humanoid  ->  Field required
               alignment  ->  Field required
            """
        ).strip()
        assert expected == computed, f"Values didn't match\n\ncomputed:\n{computed}\n\nexpected:\n{expected}"

    def test_save__writes_settings_to_disk(self, fake_settings_path: Path):
        manager = SettingsManager(DefaultSettingsModel)
        manager.save()

        assert json.loads(fake_settings_path.read_text()) == {
            "name": "jawa",
            "planet": "tatooine",
            "is_humanoid": True,
            "alignment": "neutral",
        }

    def test_save__raises_error_on_failure(self, mocker: MockerFixture):
        manager = SettingsManager(DefaultSettingsModel)
        mocker.patch.object(manager, "settings_path").write_text.side_effect = RuntimeError("BOOM")
        with pytest.raises(SettingsSaveError, match="Failed to save settings"):
            manager.save()

    def test_secret_str__is_masked_in_display(self):
        class SecretSettingsModel(BaseModel):
            username: str = "leia"
            api_token: PlaintextSecretStr = PlaintextSecretStr("s3cr3t")

        manager = SettingsManager(SecretSettingsModel)
        console = Console()
        with console.capture() as snag:
            console.print(manager.pretty())
        output = snag.get()
        assert "s3cr3t" not in output
        assert "**********" in output

    def test_secret_str__is_persisted_as_plaintext_and_reloaded(self, fake_settings_path: Path):
        class SecretSettingsModel(BaseModel):
            username: str = "leia"
            api_token: PlaintextSecretStr = PlaintextSecretStr("s3cr3t")

        manager = SettingsManager(SecretSettingsModel)
        manager.save()

        data = json.loads(fake_settings_path.read_text())
        assert data == {"username": "leia", "api_token": "s3cr3t"}

        manager2 = SettingsManager(SecretSettingsModel)
        assert cast(SecretSettingsModel, manager2.settings_instance).api_token.get_secret_value() == "s3cr3t"

    def test_secret_str__survives_update_round_trip(self):
        class SecretSettingsModel(BaseModel):
            username: str = "leia"
            api_token: PlaintextSecretStr = PlaintextSecretStr("s3cr3t")

        manager = SettingsManager(SecretSettingsModel)
        manager.update(username="han")
        assert cast(SecretSettingsModel, manager.settings_instance).username == "han"
        assert cast(SecretSettingsModel, manager.settings_instance).api_token.get_secret_value() == "s3cr3t"

    def test_secret_str__survives_unset_round_trip(self):
        class SecretSettingsModel(BaseModel):
            username: str = "leia"
            api_token: PlaintextSecretStr = PlaintextSecretStr("s3cr3t")

        manager = SettingsManager(SecretSettingsModel)
        manager.unset("username")
        assert cast(SecretSettingsModel, manager.settings_instance).username == "leia"
        assert cast(SecretSettingsModel, manager.settings_instance).api_token.get_secret_value() == "s3cr3t"

    def test_nested_secret_str__is_masked_in_display_and_persisted_as_plaintext(self, fake_settings_path: Path):
        class NestedSettingsModel(BaseModel):
            api_token: PlaintextSecretStr = PlaintextSecretStr("nested-secret")

        class ParentSettingsModel(BaseModel):
            child: NestedSettingsModel = NestedSettingsModel()

        manager = SettingsManager(ParentSettingsModel)
        console = Console()
        with console.capture() as snag:
            console.print(manager.pretty())
        output = snag.get()
        assert "nested-secret" not in output
        assert "**********" in output

        manager.update()
        assert cast(ParentSettingsModel, manager.settings_instance).child.api_token.get_secret_value() == (
            "nested-secret"
        )
        manager.save()
        data = json.loads(fake_settings_path.read_text())
        assert data == {"child": {"api_token": "nested-secret"}}

        reloaded_manager = SettingsManager(ParentSettingsModel)
        assert cast(ParentSettingsModel, reloaded_manager.settings_instance).child.api_token.get_secret_value() == (
            "nested-secret"
        )

    def test_regular_settings__preserves_malformed_nested_secret_values(self, fake_settings_path: Path):

        class Child(BaseModel):
            token: PlaintextSecretStr

        class Parent(BaseModel):
            child: Child

        malformed = {"child": {"token": {"unexpected": "shape"}}}
        fake_settings_path.write_text(json.dumps(malformed))

        manager = SettingsManager(Parent)
        manager.save()

        assert json.loads(fake_settings_path.read_text()) == malformed

    def test_regular_settings__loads_alias_choices_and_paths(self, fake_settings_path: Path):

        class AliasSettings(BaseModel):
            first: str = Field(validation_alias=AliasChoices("preferred", "legacy"))
            second: str = Field(validation_alias=AliasPath("credentials", "display"))

        fake_settings_path.write_text(json.dumps({"preferred": "primary", "credentials": {"display": "nested"}}))

        manager = SettingsManager(AliasSettings)

        settings = cast(AliasSettings, manager.settings_instance)
        assert settings.first == "primary"
        assert settings.second == "nested"

    def test_save__restricts_settings_file_to_current_user(self, fake_settings_path: Path):
        class Settings(BaseModel):
            name: str = "leia"

        SettingsManager(Settings).save()

        assert fake_settings_path.stat().st_mode & 0o777 == 0o600

    def test_regular_settings__ignores_model_extras_when_saving(self, fake_settings_path: Path):

        class ExtraSettings(BaseModel):
            model_config = ConfigDict(extra="allow")
            name: str

        fake_settings_path.write_text(json.dumps({"name": "leia", "unmodeled": "preserved-in-memory"}))

        manager = SettingsManager(ExtraSettings)
        assert manager.settings_instance.model_extra == {"unmodeled": "preserved-in-memory"}
        manager.save()

        assert json.loads(fake_settings_path.read_text()) == {"name": "leia"}

    def test_regular_settings__does_not_validate_on_save(self, fake_settings_path: Path):
        validator_calls = []

        class ValidatedSettings(BaseModel):
            value: int

            @field_validator("value")
            @classmethod
            def track_validation(cls, value: int) -> int:
                validator_calls.append(value)
                return value

        fake_settings_path.write_text(json.dumps({"value": 1}))
        manager = SettingsManager(ValidatedSettings)
        assert validator_calls == [1]
        validator_calls.clear()
        cast(Any, manager.settings_instance).value = "invalid"

        manager.save()

        assert validator_calls == []
        assert json.loads(fake_settings_path.read_text()) == {"value": "invalid"}

    @pytest.mark.parametrize(
        ("settings_model", "value"),
        [
            (FixedTupleSettings, "malformed"),
            (FixedTupleSettings, ["ordinary", 1, 2]),
            (FixedTupleSettings, ["ordinary"]),
            (VariadicTupleSettings, "malformed"),
            (VariadicTupleSettings, ["ordinary", "extra"]),
            (VariadicTupleSettings, []),
        ],
    )
    def test_regular_settings__preserves_malformed_tuple_shapes(
        self, fake_settings_path: Path, settings_model: type[BaseModel], value: Any
    ):
        data = {"value": value}
        fake_settings_path.write_text(json.dumps(data))

        manager = SettingsManager(settings_model)
        manager.save()

        assert json.loads(fake_settings_path.read_text()) == data

    def test_save__serializes_non_json_types(self):
        class Settings(BaseModel):
            url: AnyHttpUrl = AnyHttpUrl("https://example.com/")
            path: Path = Path("/tmp/example")
            when: datetime = datetime(2026, 1, 2, 3, 4, 5)
            token: PlaintextSecretStr = PlaintextSecretStr("plain-token")
            nested: dict[str, AnyHttpUrl] = {"a": AnyHttpUrl("https://a.example.com/")}

        manager = SettingsManager(Settings)
        manager.save()

        assert json.loads(manager.settings_path.read_text()) == {
            "url": "https://example.com/",
            "path": "/tmp/example",
            "when": "2026-01-02T03:04:05",
            "token": "plain-token",
            "nested": {"a": "https://a.example.com/"},
        }
        reloaded = SettingsManager(Settings).settings_instance
        assert isinstance(reloaded, Settings)
        assert str(reloaded.url) == "https://example.com/"
