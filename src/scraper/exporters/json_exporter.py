# src/scraper/exporters/json_exporter.py
"""
Concrete implementation of BaseExporter for exporting data to JSON format.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from .base_exporter import BaseExporter
from ..models import ScrapeResult, ExportFormat


class JsonExporter(BaseExporter):
    """Exports scraped data to a JSON file."""

    def __init__(self, output_dir: Path = None):
        """Initializes the JsonExporter."""
        super().__init__(ExportFormat.JSON, output_dir)

    def export(self, data: ScrapeResult) -> Optional[Path]:
        """
        Serializes the ScrapeResult to a JSON file with pretty-printing.

        The output JSON is structured with a top-level 'metadata' key
        and an 'items' key containing the list of scraped data.

        Args:
            data: The ScrapeResult object to export.

        Returns:
            The Path to the exported file, or None if the export fails.
        """
        filepath = self._get_filepath(data.template_name)
        self.logger.info(f"Exporting data to JSON file: {filepath}")

        try:
            # Use the to_dict method from the data models for clean serialization
            export_data = data.to_dict()

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Successfully exported {len(data.items)} items to {filepath}")
            return filepath
        except (IOError, TypeError) as e:
            self.logger.error(f"Failed to export to JSON: {e}")
            return None