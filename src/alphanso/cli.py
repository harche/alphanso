"""Command-line interface for Alphanso."""

import logging
import sys
from pathlib import Path

import click

from alphanso.api import run_convergence
from alphanso.config.schema import ConvergenceConfig
from alphanso.utils.logging import TRACE, setup_logging


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
    multiple=True,
    help="Environment variable (KEY=VALUE)",
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v=INFO, -vv=DEBUG)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress all output except errors",
)
@click.option(
    "--log-file",
    type=click.Path(path_type=Path),
    help="Write logs to file",
)
@click.option(
    "--log-format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Log file format (text or json)",
)
def run(
    config: Path,
    var: tuple[str, ...],
    verbose: int,
    quiet: bool,
    log_file: Path | None,
    log_format: str,
) -> None:
    """Run convergence loop with configuration.

    Examples:

        alphanso run --config config.yaml

        alphanso run --config rebase.yaml --var K8S_TAG=v1.35.0

        alphanso run --config config.yaml -vv --log-file debug.log

        alphanso run --config config.yaml --log-file logs.json --log-format json
    """
    # Setup logging based on verbosity flags
    # Map verbosity count to log level
    if quiet:
        log_level = logging.ERROR  # -q: errors only
    elif verbose == 0:
        log_level = (
            logging.INFO
        )  # Default: show all important info (validator results, AI actions, progress)
    elif verbose == 1:
        log_level = logging.DEBUG  # -v: add workflow tracking, state transitions, detailed tool I/O
    else:  # verbose >= 2
        log_level = TRACE  # -vv: add state dumps, development diagnostics, ultra-verbose output

    # Initialize logging for entire application
    setup_logging(
        level=log_level,
        log_file=log_file,
        log_format=log_format,
        enable_colors=sys.stdout.isatty(),
    )

    # Get logger for CLI module
    logger = logging.getLogger(__name__)

    # Parse variables from --var options
    env_vars: dict[str, str] = {}
    for v in var:
        if "=" not in v:
            logger.error(f"Invalid variable format '{v}'. Expected KEY=VALUE")
            sys.exit(1)
        key, value = v.split("=", 1)
        env_vars[key] = value

    # Log configuration loading
    logger.info(f"Loading configuration from: {config}")

    # Load configuration from YAML
    # Note: from_yaml() automatically loads system_prompt_file content into system_prompt field
    try:
        config_obj = ConvergenceConfig.from_yaml(config)
        logger.info(f"Configuration loaded successfully: {config_obj.name}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}", exc_info=True)
        sys.exit(1)

    # Extract system prompt content (already loaded by from_yaml())
    system_prompt_content = config_obj.agent.claude.system_prompt or None
    if system_prompt_content:
        logger.info("Custom system prompt loaded from configuration")

    # Run convergence using API
    try:
        # Resolve config's working_directory relative to config file location
        if not Path(config_obj.working_directory).is_absolute():
            working_dir = config.parent / config_obj.working_directory
        else:
            working_dir = Path(config_obj.working_directory)

        logger.info(f"Starting convergence loop: {config_obj.name}")
        logger.info(f"Working directory: {working_dir.absolute()}")
        logger.info(f"Max attempts: {config_obj.max_attempts}")

        result = run_convergence(
            config=config_obj,
            system_prompt_content=system_prompt_content,
            env_vars=env_vars,
            working_directory=working_dir.absolute(),
            config_directory=config.parent.absolute(),
        )
    except Exception as e:
        logger.error(f"Error running convergence: {e}", exc_info=True)
        sys.exit(1)

    # Summary
    logger.info("=" * 60)
    if result["success"]:
        logger.info("✅ All pre-actions completed successfully!")
    else:
        logger.warning("❌ Some pre-actions failed")
    logger.info("=" * 60)

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    cli()
