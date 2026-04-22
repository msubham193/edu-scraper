"""
main.py
-------
CLI entry point for the Education Institute Scraper.

Usage:
    python main.py -q "JEE coaching in Delhi" -n 20 -o results.xlsx
    python main.py -q "engineering colleges in Mumbai" -n 30
    python main.py --help
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from google_search import google_search
from scraper import scrape_all
from exporter import export_to_excel

console = Console()

import os
import sys
# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

BANNER = """
+-----------------------------------------------------------+
|       EDUCATION INSTITUTE SCRAPER  v1.0                   |
|  Schools  Colleges  Universities  Coaching Institutes     |
+-----------------------------------------------------------+
"""


def parse_args():
    parser = argparse.ArgumentParser(
        prog="edu_scraper",
        description="Scrape contact info (name, email, phone) from educational institutions via Google search.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -q "JEE coaching in Delhi" -n 20
  python main.py -q "CBSE schools in Bangalore" -n 15 -o schools_bangalore.xlsx
  python main.py -q "engineering colleges Chennai" -n 25 -d 3.0
        """
    )
    parser.add_argument(
        "-q", "--query",
        required=True,
        help='Search query, e.g. "JEE coaching in Delhi"'
    )
    parser.add_argument(
        "-n", "--results",
        type=int,
        default=20,
        help="Number of websites to scrape (default: 20)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output Excel filename (default: auto-generated with timestamp)"
    )
    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between requests (default: 2.0)"
    )
    return parser.parse_args()


def print_results_table(results: list[dict]):
    """Print a summary table to the console."""
    table = Table(title="📊 Scraping Results", show_lines=True, style="blue")
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Institution", style="bold cyan", min_width=25)
    table.add_column("Email(s)", style="green", min_width=25)
    table.add_column("Phone(s)", style="yellow", min_width=18)

    for i, item in enumerate(results, 1):
        emails = "\n".join(item.get("emails", [])[:2]) or "[dim]—[/dim]"
        phones = "\n".join(item.get("phones", [])[:2]) or "[dim]—[/dim]"
        name = item.get("name", "Unknown")[:40]
        table.add_row(str(i), name, emails, phones)

    console.print(table)


def main():
    args = parse_args()

    # Pretty banner
    print(BANNER)

    # Auto-generate output filename if not provided
    if not args.output:
        safe_query = args.query[:40].replace(" ", "_").replace('"', "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"{safe_query}_{timestamp}.xlsx"

    console.print(Panel.fit(
        f"[bold]Query:[/bold] {args.query}\n"
        f"[bold]Results:[/bold] {args.results} websites\n"
        f"[bold]Output:[/bold] {args.output}\n"
        f"[bold]Delay:[/bold] {args.delay}s between requests",
        title="[cyan]Configuration[/cyan]",
        border_style="cyan"
    ))

    # Step 1: Google Search
    console.print("\n[bold]Step 1:[/bold] Searching Google...")
    urls = google_search(args.query, num_results=args.results)

    if not urls:
        console.print("[red bold]No URLs found. Try a different query.[/red bold]")
        sys.exit(1)

    # Step 2: Scrape Each Website
    console.print(f"\n[bold]Step 2:[/bold] Scraping {len(urls)} websites...\n")
    results = scrape_all(urls, delay=args.delay)

    if not results:
        console.print("[red bold]No data could be scraped.[/red bold]")
        sys.exit(1)

    # Step 3: Show Results Table
    console.print("\n[bold]Step 3:[/bold] Results preview:\n")
    print_results_table(results)

    # Step 4: Export to Excel
    console.print(f"\n[bold]Step 4:[/bold] Exporting to Excel...")
    output_path = export_to_excel(results, args.output)

    # ── Summary ───────────────────────────────────────────────────────────────
    with_email = sum(1 for r in results if r.get("emails"))
    with_phone = sum(1 for r in results if r.get("phones"))
    both = sum(1 for r in results if r.get("emails") and r.get("phones"))

    console.print(Panel.fit(
        f"[green bold]Done![/green bold]\n\n"
        f"Total scraped  : [bold]{len(results)}[/bold] institutions\n"
        f"With email     : [green]{with_email}[/green]\n"
        f"With phone     : [yellow]{with_phone}[/yellow]\n"
        f"With both      : [cyan]{both}[/cyan]\n\n"
        f"Saved to: [underline]{output_path}[/underline]",
        title="[green]Scraping Complete[/green]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
