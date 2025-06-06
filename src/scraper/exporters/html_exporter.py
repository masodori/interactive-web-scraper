# src/scraper/exporters/html_exporter.py
"""
Concrete implementation of BaseExporter for creating a user-friendly
HTML report of the scraping results.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List

from .base_exporter import BaseExporter
from ..models import ScrapeResult, ExportFormat, ScrapedItem


class HtmlExporter(BaseExporter):
    """Exports scraped data to a single HTML report file."""

    def __init__(self, output_dir: Path = None):
        """Initializes the HtmlExporter."""
        super().__init__(ExportFormat.HTML, output_dir)

    def _generate_item_html(self, item: ScrapedItem) -> str:
        """Generates the HTML block for a single scraped item."""
        item_html = f"<div class='item'>"
        item_html += f"<h3>Item from <a href='{item.url}' target='_blank' rel='noopener noreferrer'>{item.url}</a></h3>"
        item_html += f"<p><strong>Timestamp:</strong> {item.timestamp}</p>"

        if item.errors:
            item_html += "<div class='errors'><strong>Errors:</strong><ul>"
            for error in item.errors:
                item_html += f"<li>{error}</li>"
            item_html += "</ul></div>"

        for key, value in item.data.items():
            item_html += "<div class='field'>"
            item_html += f"<span class='field-name'>{key}:</span>"
            item_html += self._format_value_html(value)
            item_html += "</div>"
        
        item_html += "</div>"
        return item_html

    def _format_value_html(self, value: Any) -> str:
        """Recursively formats a value into an HTML representation."""
        if isinstance(value, dict):
            table = "<table>"
            for k, v in value.items():
                table += f"<tr><td>{k}</td><td>{self._format_value_html(v)}</td></tr>"
            table += "</table>"
            return table
        elif isinstance(value, list):
            if not value: return ""
            lst = "<ul>"
            for v_item in value:
                lst += f"<li>{self._format_value_html(v_item)}</li>"
            lst += "</ul>"
            return lst
        else:
            return f"<span class='field-value'>{value}</span>"

    def export(self, data: ScrapeResult) -> Optional[Path]:
        """
        Generates and saves an HTML report from the ScrapeResult.

        Args:
            data: The ScrapeResult object to export.

        Returns:
            The Path to the exported file, or None if export fails.
        """
        filepath = self._get_filepath(data.template_name)
        self.logger.info(f"Exporting data to HTML report: {filepath}")
        
        # Build HTML content for items
        items_section = "".join([self._generate_item_html(item) for item in data.items])
        
        # Build HTML for general errors
        errors_section = ""
        if data.errors:
            errors_section += "<div class='summary-errors'><h2>General Errors</h2><ul>"
            for error in data.errors:
                errors_section += f"<li class='error'>{error}</li>"
            errors_section += "</ul></div>"
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Scraping Report: {data.template_name}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 20px; background-color: #f9f9f9; color: #333; }}
                h1, h2 {{ color: #1a2533; }}
                .container {{ max-width: 1200px; margin: auto; }}
                .summary, .item {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 20px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
                .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                .summary-item {{ background: #f2f6fa; padding: 10px; border-radius: 5px; }}
                .summary-item strong {{ display: block; color: #555; }}
                .errors, .summary-errors {{ color: #d8000c; background-color: #ffbaba; border: 1px solid; margin: 10px 0; padding: 15px; border-radius: 8px; }}
                .field {{ margin: 10px 0; }}
                .field-name {{ font-weight: bold; color: #005a9c; display: block; margin-bottom: 5px; }}
                .field-value {{ word-wrap: break-word; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 5px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #e9f2fa; }}
                ul {{ padding-left: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Scraping Report</h1>
                <h2>Template: {data.template_name}</h2>
                <div class="summary">
                    <h2>Summary</h2>
                    <div class="summary-grid">
                        <div class="summary-item"><strong>Start Time:</strong><span>{data.start_time}</span></div>
                        <div class="summary-item"><strong>End Time:</strong><span>{data.end_time}</span></div>
                        <div class="summary-item"><strong>Total Items:</strong><span>{data.total_items}</span></div>
                        <div class="summary-item"><strong>Successful:</strong><span>{data.successful_items}</span></div>
                        <div class="summary-item"><strong>Failed:</strong><span>{data.failed_items}</span></div>
                        <div class="summary-item"><strong>Success Rate:</strong><span>{data.success_rate():.2f}%</span></div>
                    </div>
                    {errors_section}
                </div>
                <h2>Scraped Data ({len(data.items)} items)</h2>
                {items_section}
            </div>
        </body>
        </html>
        """
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_template)
            self.logger.info(f"Successfully exported HTML report to {filepath}")
            return filepath
        except IOError as e:
            self.logger.error(f"Failed to write HTML report: {e}")
            return None