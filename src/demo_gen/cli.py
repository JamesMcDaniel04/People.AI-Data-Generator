"""CLI interface for demo-gen"""

import json
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from demo_gen.config import load_config
from demo_gen.runner import DemoGenRunner

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Demo data generator for People.ai - Create realistic demo environments on demand"""
    load_dotenv()


@main.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to configuration YAML file",
)
@click.option(
    "--env",
    type=click.Choice(["sandbox", "staging", "prod-demo"]),
    default="sandbox",
    help="Target environment",
)
@click.option(
    "--log-dir",
    type=click.Path(path_type=Path),
    default=Path("./runs"),
    help="Directory for run logs",
)
@click.option(
    "--concurrency",
    type=int,
    default=5,
    help="Concurrency limit for API calls",
)
@click.option(
    "--max-opps",
    type=int,
    default=200,
    help="Hard safety cap on number of opportunities",
)
def run(config, env, log_dir, concurrency, max_opps):
    """Run the full demo data generation pipeline"""
    try:
        console.print("[bold blue]Loading configuration...[/bold blue]")
        resolved_config = load_config(config, env, log_dir)

        console.print(f"[green]Run ID: {resolved_config.run_id}[/green]")
        console.print(f"[green]Run directory: {resolved_config.run_dir}[/green]")

        runner = DemoGenRunner(resolved_config, concurrency, max_opps)

        console.print("\n[bold blue]Starting demo data generation...[/bold blue]")
        stats = runner.run()

        console.print("\n[bold green]Run completed successfully![/bold green]")
        _display_stats(stats)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to configuration YAML file",
)
@click.option(
    "--env",
    type=click.Choice(["sandbox", "staging", "prod-demo"]),
    default="sandbox",
    help="Target environment",
)
@click.option(
    "--log-dir",
    type=click.Path(path_type=Path),
    default=Path("./runs"),
    help="Directory for run logs",
)
def dry_run(config, env, log_dir):
    """Preview what would be created without making changes"""
    try:
        console.print("[bold blue]Loading configuration (dry-run mode)...[/bold blue]")
        resolved_config = load_config(config, env, log_dir)
        resolved_config.config.run.dry_run = True

        runner = DemoGenRunner(resolved_config, concurrency=1, max_opps=200)

        console.print("\n[bold blue]Analyzing what would be created...[/bold blue]")
        stats = runner.run()

        console.print("\n[bold yellow]Dry-run results (no changes made):[/bold yellow]")
        _display_stats(stats)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option(
    "--run-id",
    required=True,
    help="Run ID to get status for",
)
@click.option(
    "--log-dir",
    type=click.Path(path_type=Path),
    default=Path("./runs"),
    help="Directory for run logs",
)
def status(run_id, log_dir):
    """Display status and summary of a completed run"""
    try:
        summary_file = _find_run_summary(log_dir, run_id)

        if not summary_file:
            console.print(f"[bold red]No run found with ID: {run_id}[/bold red]")
            sys.exit(1)

        with open(summary_file) as f:
            stats = json.load(f)

        console.print(f"\n[bold blue]Run {run_id} Summary[/bold blue]")
        _display_stats(stats)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option(
    "--run-id",
    required=True,
    help="Run ID to reset/cleanup",
)
@click.option(
    "--log-dir",
    type=click.Path(path_type=Path),
    default=Path("./runs"),
    help="Directory for run logs",
)
@click.confirmation_option(prompt="Are you sure you want to delete records created by this run?")
def reset(run_id, log_dir):
    """Delete records created by a specific run (tag or external_state)"""
    try:
        run_dir = _find_run_dir(log_dir, run_id)

        if not run_dir:
            console.print(f"[bold red]No run found with ID: {run_id}[/bold red]")
            sys.exit(1)

        console.print(f"[bold yellow]Resetting run {run_id}...[/bold yellow]")

        from demo_gen.runner import DemoGenRunner

        result = DemoGenRunner.cleanup_run(run_dir)

        if result:
            table = Table(title="Cleanup Results")
            table.add_column("Object", style="cyan")
            table.add_column("Deleted", style="magenta")
            for object_name, count in result.items():
                table.add_row(object_name, str(count))
            console.print(table)

        console.print(f"[bold green]Run {run_id} has been reset[/bold green]")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to configuration YAML file",
)
@click.option(
    "--opp-id",
    required=True,
    help="Specific opportunity ID to test with",
)
@click.option(
    "--env",
    type=click.Choice(["sandbox", "staging", "prod-demo"]),
    default="sandbox",
    help="Target environment",
)
def smoke(config, opp_id, env):
    """Smoke test: Create 1 meeting + 1 email + 1 scorecard for a single opp"""
    try:
        console.print("[bold blue]Running smoke test...[/bold blue]")
        console.print(f"[blue]Target opportunity: {opp_id}[/blue]")

        resolved_config = load_config(config, env, Path("./runs"))

        from demo_gen.runner import DemoGenRunner

        runner = DemoGenRunner(resolved_config, concurrency=1, max_opps=1)
        result = runner.smoke_test(opp_id)

        console.print("\n[bold green]Smoke test completed![/bold green]")

        table = Table(title="Created Records")
        table.add_column("Type", style="cyan")
        table.add_column("ID", style="magenta")
        table.add_column("Details", style="green")

        table.add_row("Meeting", result["meeting_id"], result.get("meeting_subject", ""))
        table.add_row("Email", result["email_id"], result.get("email_subject", ""))
        table.add_row(
            "Scorecard",
            result["scorecard_id"],
            f"Score: {result.get('scorecard_score', 0)}",
        )

        console.print(table)

        console.print(
            "\n[yellow]Check People.ai ingestion to verify these activities appear[/yellow]"
        )

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


def _display_stats(stats):
    """Display run statistics in a formatted table"""
    table = Table(title="Run Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Run ID", stats.get("run_id", "N/A"))
    table.add_row("Started At", stats.get("started_at", "N/A"))
    table.add_row("Finished At", stats.get("finished_at", "N/A"))
    table.add_row("Opportunities Selected", str(stats.get("opps_selected", 0)))
    table.add_row("Meetings Created", str(stats.get("meetings_created", 0)))
    table.add_row("Emails Created", str(stats.get("emails_created", 0)))
    table.add_row("Scorecards Created", str(stats.get("scorecards_created", 0)))
    table.add_row("Scorecard Answers Written", str(stats.get("scorecard_answers_written", 0)))
    table.add_row("Failures", str(stats.get("failures", 0)))
    table.add_row("Coverage", f"{stats.get('coverage', 0):.1%}")

    console.print(table)


def _find_run_summary(log_dir: Path, run_id: str) -> Path:
    """Find the summary.json file for a given run ID"""
    for run_dir in log_dir.iterdir():
        if run_dir.is_dir() and run_id in run_dir.name:
            summary_file = run_dir / "summary.json"
            if summary_file.exists():
                return summary_file
    return None


def _find_run_dir(log_dir: Path, run_id: str) -> Path:
    """Find the run directory for a given run ID"""
    for run_dir in log_dir.iterdir():
        if run_dir.is_dir() and run_id in run_dir.name:
            return run_dir
    return None


if __name__ == "__main__":
    main()
