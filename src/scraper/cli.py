# src/scraper/cli.py
"""
Command-Line Interface for the Interactive Web Scraper.

Provides commands to create templates, apply them, run batches,
and an interactive menu for ease of use.
"""

import argparse
import logging
import sys
from pathlib import Path

from .core import InteractiveScraper, TemplateScraper
from .models import ExportFormat
from .utils.logging_config import setup_logging
from .config import Config

def _create_parser() -> argparse.ArgumentParser:
    """Creates and configures the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="A modular, extensible web scraper with interactive template creation.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # 'create' command
    create_parser = subparsers.add_parser('create', help='Create a new scraping template interactively.')
    create_parser.set_defaults(func=_run_create)

    # 'apply' command
    apply_parser = subparsers.add_parser('apply', help='Apply an existing template to scrape a site.')
    apply_parser.add_argument('template', type=Path, help='Path to the scraping template JSON file.')
    apply_parser.add_argument('--headless', action='store_true', help='Run the browser in headless mode.')
    apply_parser.add_argument(
        '--export',
        nargs='+',
        choices=[f.value for f in ExportFormat],
        default=[ExportFormat.JSON.value],
        help='One or more formats to export the data to (default: json).'
    )
    apply_parser.set_defaults(func=_run_apply)
    
    # 'batch' command
    batch_parser = subparsers.add_parser('batch', help='Run all templates in a directory.')
    batch_parser.add_argument(
        '--templates-dir',
        type=Path,
        default=Config.TEMPLATES_DIR,
        help=f'Directory containing templates (default: {Config.TEMPLATES_DIR}).'
    )
    batch_parser.add_argument('--headless', action='store_true', help='Run the browser in headless mode.')
    batch_parser.set_defaults(func=_run_batch)

    return parser

def _run_create(args: argparse.Namespace = None):
    """Handles the 'create' command."""
    print("Starting interactive template creation...")
    with InteractiveScraper() as scraper:
        scraper.create_template()
    print("Interactive session finished.")

def _run_apply(args: argparse.Namespace = None):
    """Handles the 'apply' command, can be called from menu or CLI."""
    if args and args.template:
        template_path = args.template
        headless = args.headless
        export_formats = [ExportFormat(fmt) for fmt in args.export]
    else: # Interactive menu mode
        templates = list(Config.TEMPLATES_DIR.glob("*.json"))
        if not templates:
            print("\nNo templates found in the 'templates' directory.")
            return
        print("\nAvailable templates:")
        for i, t in enumerate(templates):
            print(f"  {i+1}) {t.name}")
        choice = input("Select template number: ")
        try:
            template_path = templates[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return
        
        headless = input("Run in headless mode? (y/N): ").lower() == 'y'
        formats_input = input("Export formats (e.g., json,csv): ") or "json"
        export_formats = [ExportFormat(f.strip()) for f in formats_input.split(',')]

    if not template_path.exists():
        logging.error(f"Template file not found: {template_path}")
        return

    print(f"Applying template: {template_path.name}")
    
    with TemplateScraper(headless=headless) as scraper:
        result = scraper.apply_template(str(template_path), export_formats)
        print("\n--- Scraping Summary ---")
        print(f"  Template:       {result.template_name}")
        print(f"  Total Items:    {result.total_items}")
        print(f"  Successful:     {result.successful_items}")
        print(f"  Failed:         {result.failed_items}")
        print("------------------------")


def _run_batch(args: argparse.Namespace = None):
    """Handles the 'batch' command."""
    # This function can be expanded to be more interactive if needed
    templates_dir = args.templates_dir if args else Config.TEMPLATES_DIR
    if not templates_dir.exists():
        logging.error(f"Templates directory not found: {templates_dir}")
        return

    templates = list(templates_dir.glob("*.json"))
    if not templates:
        logging.warning(f"No templates found in {templates_dir}")
        return
        
    print(f"Starting batch process for {len(templates)} templates...")
    headless = args.headless if args else True
    with TemplateScraper(headless=headless) as scraper:
        for template_path in templates:
            print(f"\n--- Applying template: {template_path.name} ---")
            scraper.apply_template(str(template_path), [ExportFormat.JSON])
    print("\nBatch process finished.")

def _run_interactive_menu():
    """Displays the main interactive menu."""
    while True:
        print("\n--- Interactive Scraper Menu ---")
        print("1. Create a new scraping template")
        print("2. Apply an existing template")
        print("3. Exit")
        choice = input("Enter your choice: ")
        
        if choice == '1':
            _run_create()
        elif choice == '2':
            _run_apply()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice, please try again.")

def main():
    """The main entry point for the command-line interface."""
    setup_logging()
    Config.ensure_directories()
    
    # If no command-line arguments are given, run interactive menu
    if len(sys.argv) == 1:
        _run_interactive_menu()
    else:
        parser = _create_parser()
        args = parser.parse_args()
        args.func(args)

if __name__ == '__main__':
    main()