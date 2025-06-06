# src/scraper/exporters/csv_exporter.py
"""
Concrete implementation of BaseExporter for exporting data to CSV format.
Handles flattening of nested data structures.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd

from .base_exporter import BaseExporter
from ..models import ScrapeResult, ExportFormat


class CsvExporter(BaseExporter):
    """Exports scraped data to a CSV file."""

    def __init__(self, output_dir: Path = None):
        """Initializes the CsvExporter."""
        super().__init__(ExportFormat.CSV, output_dir)

    def _flatten_data(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Flattens the list of scraped items for CSV export.
        Nested dictionaries are expanded, and lists are JSON-serialized.
        """
        rows = []
        for item in items:
            row = {
                'url': item.get('url'),
                'timestamp': item.get('timestamp'),
                'errors': '; '.join(item.get('errors', []))
            }
            
            # Process the main data dictionary
            item_data = item.get('data', {})
            for key, value in item_data.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        row[f"{key}_{sub_key}"] = str(sub_value) if sub_value is not None else ''
                elif isinstance(value, list):
                    # Serialize lists to a JSON string
                    row[key] = json.dumps(value) if value else ''
                else:
                    row[key] = str(value) if value is not None else ''
            rows.append(row)
        return rows

    def export(self, data: ScrapeResult) -> Optional[Path]:
        """
        Flattens the scraped data and saves it to a CSV file.

        The export uses pandas for robust CSV writing and includes a
        UTF-8 BOM for better compatibility with Microsoft Excel.

        Args:
            data: The ScrapeResult object to export.

        Returns:
            The Path to the exported file, or None if export fails.
        """
        if not data.items:
            self.logger.warning("No items to export. Skipping CSV creation.")
            return None

        filepath = self._get_filepath(data.template_name)
        self.logger.info(f"Exporting data to CSV file: {filepath}")

        try:
            # Get items as dicts and flatten them
            item_dicts = [item.to_dict() for item in data.items]
            flattened_rows = self._flatten_data(item_dicts)

            # Create DataFrame and export
            df = pd.DataFrame(flattened_rows)
            
            # Use encoding from config for Excel compatibility
            encoding = self.config.EXPORT_FORMATS['csv']['encoding']
            df.to_csv(filepath, index=False, encoding=encoding)

            self.logger.info(f"Successfully exported {len(data.items)} items to {filepath}")
            return filepath
        except (IOError, pd.errors.EmptyDataError) as e:
            self.logger.error(f"Failed to export to CSV: {e}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during CSV export: {e}")
            return None