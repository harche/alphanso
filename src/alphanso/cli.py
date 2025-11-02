"""Command-line interface for Alphanso."""

import sys
from pathlib import Path

import click

from alphanso.api import run_convergence


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """Alphanso - AI-assisted iterative problem resolution framework."""
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Configuration YAML file",
)
@click.option(
    "--var",
    "-v",
    multiple=True,
    help="Environment variable (KEY=VALUE)",
)
def run(config: Path, var: tuple[str, ...]) -> None:
    """Run convergence loop with configuration.

    Examples:

        alphanso run --config config.yaml

        alphanso run --config rebase.yaml --var K8S_TAG=v1.35.0
    """
    # Parse variables from --var options
    env_vars: dict[str, str] = {}
    for v in var:
        if "=" not in v:
            click.echo(f"Error: Invalid variable format '{v}'. Expected KEY=VALUE")
            sys.exit(1)
        key, value = v.split("=", 1)
        env_vars[key] = value

    # Display header
    click.echo(f"Loading configuration from: {config}")
    click.echo()

    # Run convergence using API
    try:
        result = run_convergence(config_path=config, env_vars=env_vars)
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)

    # Display running header
    click.echo("=" * 60)
    click.echo(f"Running: {result['config_name']}")
    click.echo("=" * 60)
    click.echo()

    # Display execution message
    click.echo("Executing pre-actions...")
    click.echo()

    # Display results
    click.echo()
    click.echo("=" * 60)
    click.echo("Results:")
    click.echo("=" * 60)
    click.echo()

    for action_result in result["pre_action_results"]:
        if action_result["success"]:
            click.echo(f"✅ SUCCESS: {action_result['action']}")
        else:
            click.echo(f"❌ FAILED: {action_result['action']}")

        # Show output if present
        if action_result["output"]:
            for line in action_result["output"].strip().split("\n"):
                click.echo(f"  │ {line}")

        # Show errors if failed
        if not action_result["success"] and action_result["stderr"]:
            click.echo(f"  └─ Error: {action_result['stderr']}")

        click.echo()

    # Summary
    click.echo("=" * 60)
    if result["success"]:
        click.echo("✅ All pre-actions completed successfully!")
    else:
        click.echo("❌ Some pre-actions failed")
    click.echo("=" * 60)
    click.echo()

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    cli()
