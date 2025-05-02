import typer
from pydantic import BaseModel
from pytest_mock import MockerFixture

from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError, handle_errors
from typerdrive.cache.manager import CacheManager
from typerdrive.cache.attach import attach_cache
from typerdrive.settings.attach import attach_settings, get_settings

from tests.helpers import check_output


class TestHandleErrors:
    def test_handle_errors__no_errors(self):
        cli: typer.Typer = typer.Typer()

        @cli.command()
        @handle_errors("What happened?")
        def _():
            print("We're all fine here now, thank you. How are you?")

        check_output(cli, expected_substring="thank you", unwanted_substring="What happened?", prog_name="test")

    def test_handle_errors__no_conflict_with_attach_cache(self):
        cli: typer.Typer = typer.Typer()

        @cli.command()
        @handle_errors("What happened?")
        @attach_cache()
        def _(ctx: typer.Context):
            manager = ctx.obj.cache_manager
            assert isinstance(manager, CacheManager)
            assert manager.app_name == "test"
            print("We're all fine here now, thank you. How are you?")

        check_output(cli, expected_substring="thank you", unwanted_substring="What happened?", prog_name="test")

    def test_handle_errors__no_conflict_with_attach_settings(self):
        class SettingsModel(BaseModel):
            name: str = "jawa"

        cli: typer.Typer = typer.Typer()

        @cli.command()
        @attach_settings(SettingsModel)
        def _(ctx: typer.Context):
            settings = get_settings(ctx, SettingsModel)
            assert settings.name == "jawa"
            print("We're all fine here now, thank you. How are you?")

        check_output(cli, expected_substring="thank you", unwanted_substring="What happened?", prog_name="test")

    def test_handle_errors__handles_typerdrive_error_by_default(self):
        cli: typer.Typer = typer.Typer()

        @cli.command()
        @handle_errors("What happened?")
        def _():
            raise TyperdriveError("Boring conversation anyway")

        check_output(
            cli,
            expected_substring=[
                "What happened?",
                "Boring conversation anyway",
            ],
            unwanted_substring="Traceback",
            exit_code=TyperdriveError.exit_code,
            prog_name="test",
        )

    def test_handle_errors__handles_errors_matching_handle_exc_class(self):
        cli: typer.Typer = typer.Typer()

        @cli.command()
        @handle_errors("What happened?", handle_exc_class=RuntimeError)
        def han():  # pyright: ignore[reportUnusedFunction]
            raise RuntimeError("Boring conversation anyway")

        @cli.command()
        @handle_errors("Let me see your identification.", handle_exc_class=RuntimeError)
        def ben():  # pyright: ignore[reportUnusedFunction]
            raise ValueError("These aren't the droids you're looking for")

        check_output(
            cli,
            "han",
            expected_substring=[
                "What happened?",
                "Boring conversation anyway",
            ],
            unwanted_substring="Traceback",
            exit_code=ExitCode.GENERAL_ERROR,
            prog_name="test",
        )

        check_output(
            cli,
            "ben",
            unwanted_substring=[
                "Let me see your identification",
                "These aren't the droids you're looking for",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            exception_type=ValueError,
            exception_pattern="These aren't the droids you're looking for",
            prog_name="test",
        )

    def test_handle_errors__handles_all_errors_in_handle_exc_class_group(self):
        cli: typer.Typer = typer.Typer()

        @cli.command()
        @handle_errors("What happened?", handle_exc_class=(RuntimeError, ValueError))
        def han():  # pyright: ignore[reportUnusedFunction]
            raise RuntimeError("Boring conversation anyway")

        @cli.command()
        @handle_errors("Let me see your identification.", handle_exc_class=(RuntimeError, ValueError))
        def ben():  # pyright: ignore[reportUnusedFunction]
            raise ValueError("These aren't the droids you're looking for")

        check_output(
            cli,
            "han",
            expected_substring=[
                "What happened?",
                "Boring conversation anyway",
            ],
            unwanted_substring="Traceback",
            exit_code=ExitCode.GENERAL_ERROR,
            prog_name="test",
        )

        check_output(
            cli,
            "ben",
            expected_substring=[
                "Let me see your identification",
                "These aren't the droids you're looking for",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            prog_name="test",
        )

    def test_handle_errors__ignores_errors_matching_ignore_exc_class(self):
        cli: typer.Typer = typer.Typer()

        class BlasterRuntimeError(RuntimeError):
            pass

        class LightSaberRuntimeError(RuntimeError):
            pass

        @cli.command()
        @handle_errors(
            "What happened?",
            handle_exc_class=RuntimeError,
            ignore_exc_class=BlasterRuntimeError,
        )
        def han():  # pyright: ignore[reportUnusedFunction]
            raise BlasterRuntimeError("Boring conversation anyway")

        @cli.command()
        @handle_errors(
            "Let me see your identification.",
            handle_exc_class=RuntimeError,
            ignore_exc_class=BlasterRuntimeError,
        )
        def ben():  # pyright: ignore[reportUnusedFunction]
            raise LightSaberRuntimeError("These aren't the droids you're looking for")

        check_output(
            cli,
            "han",
            unwanted_substring=[
                "What happened?",
                "Boring conversation anyway",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            exception_type=BlasterRuntimeError,
            exception_pattern="Boring conversation anyway",
            prog_name="test",
        )

        check_output(
            cli,
            "ben",
            expected_substring=[
                "Let me see your identification",
                "These aren't the droids you're looking for",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            prog_name="test",
        )

    def test_handle_errors__ignores_all_errors_in_ignore_exc_class_group(self):
        cli: typer.Typer = typer.Typer()

        class BlasterRuntimeError(RuntimeError):
            pass

        class LightSaberRuntimeError(RuntimeError):
            pass

        @cli.command()
        @handle_errors(
            "What happened?",
            handle_exc_class=RuntimeError,
            ignore_exc_class=(BlasterRuntimeError, LightSaberRuntimeError),
        )
        def han():  # pyright: ignore[reportUnusedFunction]
            raise BlasterRuntimeError("Boring conversation anyway")

        @cli.command()
        @handle_errors(
            "Let me see your identification.",
            handle_exc_class=RuntimeError,
            ignore_exc_class=(BlasterRuntimeError, LightSaberRuntimeError),
        )
        def ben():  # pyright: ignore[reportUnusedFunction]
            raise LightSaberRuntimeError("These aren't the droids you're looking for")

        check_output(
            cli,
            "han",
            unwanted_substring=[
                "What happened?",
                "Boring conversation anyway",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            exception_type=BlasterRuntimeError,
            exception_pattern="Boring conversation anyway",
            prog_name="test",
        )

        check_output(
            cli,
            "ben",
            unwanted_substring=[
                "Let me see your identification",
                "These aren't the droids you're looking for",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            exception_type=LightSaberRuntimeError,
            exception_pattern="These aren't the droids you're looking for",
            prog_name="test",
        )

    def test_handle_errors__do_except(self):
        cli: typer.Typer = typer.Typer()

        garbage_chute: list[str] = []

        @cli.command()
        @handle_errors("What happened?", do_except=lambda params: garbage_chute.append(params.base_message))
        def _():
            raise TyperdriveError("Boring conversation anyway")

        check_output(
            cli,
            expected_substring=[
                "What happened?",
                "Boring conversation anyway",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            prog_name="test",
        )
        assert "What happened?" in garbage_chute

    def test_handle_errors__do_else(self):
        cli: typer.Typer = typer.Typer()

        garbage_chute: list[str] = []

        @cli.command()
        @handle_errors("What happened?", do_else=lambda: garbage_chute.append("some rescue"))
        def _():
            print("We're all fine here now, thank you. How are you?")

        check_output(
            cli,
            expected_substring="We're all fine here now, thank you. How are you?",
            unwanted_substring=[
                "What happened?",
                "Boring conversation anyway",
            ],
            prog_name="test",
        )
        assert "some rescue" in garbage_chute

    def test_handle_errors__do_finally(self):
        cli: typer.Typer = typer.Typer()

        garbage_chute: list[str] = []

        @cli.command()
        @handle_errors("What happened?", do_finally=lambda: garbage_chute.append("I don't care what you smell"))
        def _():
            raise TyperdriveError("Boring conversation anyway")

        check_output(
            cli,
            expected_substring=[
                "What happened?",
                "Boring conversation anyway",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            prog_name="test",
        )
        assert "I don't care what you smell" in garbage_chute

    def test_handle_errors__raises_runtime_error_if_format_fails(self, mocker: MockerFixture):
        mocker.patch("typerdrive.exceptions.reformat_exception", side_effect=ValueError("BOOM!"))

        cli: typer.Typer = typer.Typer()

        @cli.command()
        @handle_errors("What happened?")
        def _():
            raise TyperdriveError("Boring conversation anyway")

        check_output(
            cli,
            unwanted_substring=[
                "What happened?",
                "Boring conversation anyway",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            exception_type=RuntimeError,
            exception_pattern="Failed while formatting message.*BOOM!",
            prog_name="test",
        )

    def test_handle_errors__uses_subject_and_footer_from_typerdrive_error_if_provided(self):
        cli: typer.Typer = typer.Typer()

        @cli.command()
        @handle_errors("What happened?")
        def _():
            raise TyperdriveError(
                "Boring conversation anyway",
                subject="slight weapons malfunction",
                footer="WE'RE GONNA HAVE COMPANY!",
            )

        check_output(
            cli,
            expected_substring=[
                "slight weapons malfunction",
                "Boring conversation anyway",
                "WE'RE GONNA HAVE COMPANY!",
            ],
            exit_code=ExitCode.GENERAL_ERROR,
            prog_name="test",
        )
