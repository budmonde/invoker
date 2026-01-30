import click


def raise_error(message):
    click.secho("Invoker Error: ", err=True, nl=False, fg="red")
    click.echo(message, err=True)
    raise SystemExit(1)


def warn(message):
    click.secho("Invoker Warning: ", err=True, nl=False, fg="yellow")
    click.echo(message, err=True)


def to_camel_case(string):
    return "".join([token.capitalize() for token in string.split("_")])


def is_editable_install() -> bool:
    """
    Heuristic check: returns False if installed under site-packages/dist-packages,
    True otherwise (e.g., editable/develop install from a local checkout).
    """
    from pathlib import Path

    resources_root = (Path(__file__).parent / "resources").resolve()
    for parent in [resources_root] + list(resources_root.parents):
        name = parent.name.lower()
        if name in ("site-packages", "dist-packages"):
            return False
    return True
