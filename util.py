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
