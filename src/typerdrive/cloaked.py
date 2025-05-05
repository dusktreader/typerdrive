import typer

CloakingDevice = typer.Option(parser=lambda _: _, hidden=True, expose_value=False, default_factory=lambda: None)
