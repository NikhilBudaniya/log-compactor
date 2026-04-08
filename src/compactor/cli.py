import sys
import yaml
import click
from rich.console import Console
from compactor.core import SmartCompactor

err_console = Console(stderr=True)

@click.group()
def cli():
    """Log Compactor: Automate your log management."""
    pass

@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to config file')
def stream(config):
    """
    Pipe mode. Read from stdin and output compacted logs to stdout.
    Example: cat raw_logs.txt | logcompact stream
    """
    try:
        with open(config, 'r') as f:
            settings = yaml.safe_load(f)
    except FileNotFoundError:
        err_console.print(f"[bold red]Error:[/bold red] Config file '{config}' not found.")
        err_console.print(f"[yellow]Create a config.yaml in your project directory or use:[/yellow]")
        err_console.print(f"  logcompact stream -c /path/to/your/config.yaml")
        sys.exit(1)

    compactor = SmartCompactor(settings)

    try:
        for compacted_line in compactor.compact_stream(sys.stdin):
            print(compacted_line, flush=True)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    cli()