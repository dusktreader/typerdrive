import tempfile
from pathlib import Path

import typer
from typerdrive import FilesManager, attach_files
from typerdrive.config import get_typerdrive_config, set_typerdrive_config

cli = typer.Typer()


@cli.command()
@attach_files()
def list_reports(ctx: typer.Context, manager: FilesManager):
    manager.store_text("Q1 report", "reports/2025/q1.txt")
    manager.store_text("Planning notes", "reports/2025/planning/notes.txt")
    manager.store_text("Reports index", "reports/index.txt")
    manager.store_text("Reports overview", "reports/index.md")
    manager.store_text("Release notes", "reports/2025/release.md")

    immediate_names = manager.list_items("reports")
    recursive_keys = sorted(manager.list_items("reports", recursive=True))
    immediate_markdown = sorted(manager.list_items("reports", recursive=True, pattern="*.md"))
    all_markdown = sorted(manager.list_items("reports", recursive=True, pattern="**/*.md"))

    print(f"Immediate names: {immediate_names}")
    print(f"Recursive keys: {recursive_keys}")
    print(f"Immediate Markdown matches: {immediate_markdown}")
    print(f"Markdown matches at all depths: {all_markdown}")
    for key in recursive_keys:
        print(f"{key}: {manager.load_text(key)}")

    missing_keys = manager.list_items("reports/archive", recursive=True, missing_ok=True)
    print(f"Missing directory: {missing_keys}")


def main():
    original_config = get_typerdrive_config()
    with tempfile.TemporaryDirectory() as state_home:
        set_typerdrive_config(app_name="files-listing-example", state_home=Path(state_home))
        try:
            cli()
        finally:
            set_typerdrive_config(**original_config.model_dump())


if __name__ == "__main__":
    main()
