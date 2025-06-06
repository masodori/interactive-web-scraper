# src/scraper/exporters/base_exporter.py
"""
Defines the abstract base class for all data exporters, ensuring a
consistent interface for exporting scraped data.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Optional
from ..config import Config
from ..models import ScrapeResult, ExportFormat


class BaseExporter(ABC):
    """Abstract base class for data exporters."""

    def __init__(self, export_format: ExportFormat, output_dir: Path = None):
        """
        Initializes the exporter.

        Args:
            export_format: The format the exporter handles (e.g., JSON, CSV).
            output_dir: The directory to save exported files to.
                        Defaults to the path in the global Config.
        """
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self.export_format = export_format
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        
        # Ensure the output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_filepath(self, template_name: str) -> Path:
        """
        Generates a standardized filepath for the export.

        Args:
            template_name: The name of the template used for scraping.

        Returns:
            A Path object representing the full output filepath.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{template_name}_{timestamp}.{self.export_format.value}"
        return self.output_dir / filename

    @abstractmethod
    def export(self, data: ScrapeResult) -> Optional[Path]:
        """
        Exports the scraping results to a file.

        This method must be implemented by all concrete exporter subclasses.

        Args:
            data: The ScrapeResult object containing the data to export.

        Returns:
            The Path to the exported file, or None if export fails.
        """
        pass