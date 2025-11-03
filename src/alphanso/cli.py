"""Command-line interface for Alphanso."""

import sys
from pathlib import Path

import click

from alphanso.api import run_convergence
from alphanso.config.schema import ConvergenceConfig


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

    # Load configuration from YAML
    # Note: from_yaml() automatically loads system_prompt_file content into system_prompt field
    try:
        config_obj = ConvergenceConfig.from_yaml(config)
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)

    # Extract system prompt content (already loaded by from_yaml())
    system_prompt_content = config_obj.agent.claude.system_prompt or None

    # Run convergence using API
    # Note: All output is now printed in real-time by the graph nodes
    # Don't pass working_directory - let it use config.working_directory
    # which is resolved relative to the config file location
    try:
        # Resolve config's working_directory relative to config file location
        if not Path(config_obj.working_directory).is_absolute():
            working_dir = config.parent / config_obj.working_directory
        else:
            working_dir = Path(config_obj.working_directory)

        result = run_convergence(
            config=config_obj,
            system_prompt_content=system_prompt_content,
            env_vars=env_vars,
            working_directory=working_dir.absolute(),
        )
    except Exception as e:
        click.echo(f"Error running convergence: {e}", err=True)
        sys.exit(1)

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
