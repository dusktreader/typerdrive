import tempfile

import typer
from typer.testing import CliRunner

from attach import cli, registry
from typerdrive import add_database_subcommand
from typerdrive.env import tweak_env


add_database_subcommand(cli, registry)


@cli.command(name="migration-workflow")
def migration_workflow():
    with tempfile.TemporaryDirectory() as state_home, tweak_env(XDG_STATE_HOME=state_home):
        runner = CliRunner()
        setup = runner.invoke(cli, ["db", "setup"], prog_name="database-example")
        pending = runner.invoke(cli, ["db", "status"], prog_name="database-example")
        migrate = runner.invoke(cli, ["db", "migrate"], prog_name="database-example")
        applied = runner.invoke(cli, ["db", "status"], prog_name="database-example")

        for result in (setup, pending, migrate, applied):
            assert result.exit_code == 0, result.output
        assert "pending 00000001create_items" in pending.output
        assert "applied 00000001create_items" in applied.output
        for result in (setup, pending, migrate, applied):
            typer.echo(result.output.strip())


def main():
    cli()


if __name__ == "__main__":
    main()
