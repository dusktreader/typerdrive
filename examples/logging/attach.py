import typer
from loguru import logger
from typerdrive import LoggingManager, attach_logging, set_typerdrive_config
from typerdrive.logging.commands import add_logs_subcommand

cli = typer.Typer()
add_logs_subcommand(cli)
set_typerdrive_config(app_name="logging-attach-example")


@cli.command()
@attach_logging(verbose=True)
def report(ctx: typer.Context, manager: LoggingManager, clear: bool = False, count: int = 10):  # pyright: ignore[reportUnusedParameter]
    logger.info("Starting report")
    for i in range(count):
        logger.info(f"Logging message {i + 1}")
    logger.info("Completing report")

    logger.info("Showing log")
    manager.show()

    logger.info("Auditing log directory")
    manager.audit()

    if clear:
        logger.info("Clearing the log directory")
        manager.clear()


if __name__ == "__main__":
    cli()
