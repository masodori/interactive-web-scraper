# src/scraper/exporters/excel_exporter.py
"""
Concrete implementation of BaseExporter for exporting data to an Excel file
with multiple sheets for summary, data, and errors.
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from .base_exporter import BaseExporter
from ..models import ScrapeResult, ExportFormat


class ExcelExporter(BaseExporter):
    """Exports scraped data to a multi-sheet Excel file."""

    def __init__(self, output_dir: Path = None):
        """Initializes the ExcelExporter."""
        super().__init__(ExportFormat.EXCEL, output_dir)

    def export(self, data: ScrapeResult) -> Optional[Path]:
        """
        Saves the ScrapeResult to an Excel file with three sheets:
        1.  **Summary**: High-level statistics about the scrape.
        2.  **Data**: The core scraped data, with complex fields serialized.
        3.  **Errors**: A log of all errors encountered.

        Args:
            data: The ScrapeResult object to export.

        Returns:
            The Path to the exported file, or None if export fails.
        """
        filepath = self._get_filepath(data.template_name)
        self.logger.info(f"Exporting data to Excel file: {filepath}")

        try:
            with pd.ExcelWriter(filepath, engine=self.config.EXPORT_FORMATS['excel']['engine']) as writer:
                # 1. Summary Sheet
                summary_data = {
                    'Metric': ['Template Name', 'Start Time', 'End Time', 'Total Items',
                               'Successful Items', 'Failed Items', 'Success Rate (%)', 'General Errors'],
                    'Value': [data.template_name, data.start_time, data.end_time,
                              data.total_items, data.successful_items, data.failed_items,
                              f"{data.success_rate():.2f}", len(data.errors)]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

                # 2. Data Sheet
                if data.items:
                    rows = []
                    for item in data.items:
                        item_dict = item.to_dict()
                        row = {'url': item_dict.get('url'), 'timestamp': item_dict.get('timestamp')}
                        # Serialize complex fields to JSON strings for clarity in Excel
                        for key, value in item_dict.get('data', {}).items():
                            if isinstance(value, (dict, list)):
                                row[key] = json.dumps(value, ensure_ascii=False)
                            else:
                                row[key] = value
                        rows.append(row)
                    pd.DataFrame(rows).to_excel(writer, sheet_name='Data', index=False)

                # 3. Errors Sheet
                has_errors = data.errors or any(item.errors for item in data.items)
                if has_errors:
                    error_rows = []
                    for error in data.errors:
                        error_rows.append({'Type': 'General', 'URL': '', 'Error': error})
                    for item in data.items:
                        for error in item.errors:
                            error_rows.append({'Type': 'Item Specific', 'URL': item.url, 'Error': error})
                    if error_rows:
                        pd.DataFrame(error_rows).to_excel(writer, sheet_name='Errors', index=False)

            self.logger.info(f"Successfully exported {len(data.items)} items to {filepath}")
            return filepath
        except (IOError, Exception) as e:
            self.logger.error(f"Failed to export to Excel: {e}")
            return None