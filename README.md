# Interactive Web Scraper

A powerful, modular Python web scraper built with Selenium that supports interactive template creation, cookie handling, and multiple export formats.

## Features

- **Interactive Template Creation**: Point-and-click interface for selecting elements to scrape
- **Cookie Consent Handling**: Automatic detection and handling of cookie popups
- **Multiple Scraping Modes**:
  - Single page scraping
  - List page scraping
  - List + Detail page scraping
- **Dynamic Content Loading**:
  - Scroll-based loading
  - "Load More" button clicking
  - Pagination support
- **Export Formats**: JSON, CSV, Excel, HTML
- **Large Dataset Support**: Batch processing with progress tracking
- **Robust Error Handling**: Retry mechanisms and detailed logging

## Installation

```bash
# Clone the repository
git clone https://github.com/masodori/interactive-web-scraper.git
cd interactive-web-scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Quick Start

### Basic Usage

```python
from scraper.core import InteractiveScraper
from scraper.config import Config

# Initialize scraper
scraper = InteractiveScraper(headless=False)

# Simple page scraping
scraper.scrape_url('https://example.com')

# Close when done
scraper.close()
```

### Create a Scraping Template

```bash
# Interactive template creation
python examples/template_creation.py
```

### Apply a Template

```python
from scraper.core import TemplateScraper
from scraper.models import ExportFormat

# Initialize scraper
scraper = TemplateScraper(headless=True)

# Apply template and export
result = scraper.apply_template(
    'templates/my_template.json',
    export_formats=[ExportFormat.JSON, ExportFormat.CSV]
)

scraper.close()
```

## Project Structure

- `src/scraper/`: Main package directory
  - `core/`: Core scraping functionality
  - `extractors/`: Data extraction modules
  - `exporters/`: Export format handlers
  - `handlers/`: Special functionality (cookies, pagination)
  - `models/`: Data models and enums
  - `utils/`: Utility functions
  - `config/`: Configuration settings

## Configuration

Edit `src/scraper/config/settings.py` to customize:

```python
# Timeouts
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3

# Batch processing
BATCH_SIZE = 250
PROGRESS_LOG_INTERVAL = 100

# Directories
OUTPUT_DIR = Path('output')
TEMPLATES_DIR = Path('templates')
LOGS_DIR = Path('logs')
```

## Advanced Usage

### Handling Large Datasets

```python
from scraper.core import TemplateScraper
from scraper.handlers import LargeDatasetHandler

scraper = TemplateScraper(headless=True)
scraper.enable_large_dataset_mode()

# Scrapes with batch processing and intermediate saves
result = scraper.apply_template('templates/large_site.json')
```

### Custom Cookie Handling

```python
from scraper.handlers import CookieHandler

# Custom cookie selector
scraper.cookie_handler.add_custom_selector(
    "//button[@id='accept-cookies']"
)

# Or use CSS selector
scraper.cookie_handler.add_custom_selector(
    "button.cookie-accept",
    selector_type='css'
)
```

### Custom Extractors

```python
from scraper.extractors import ElementExtractor

class CustomExtractor(ElementExtractor):
    def extract_custom_data(self, selector):
        # Your custom extraction logic
        pass

# Register custom extractor
scraper.register_extractor('custom', CustomExtractor)
```

## Command Line Interface

```bash
# Create template
python -m scraper create --url https://example.com

# Apply template
python -m scraper apply templates/example.json --export json csv

# Batch scraping
python -m scraper batch --templates-dir ./templates --headless

# Extract specific elements
python -m scraper extract https://example.com --elements tables links
```

## Testing

```bash
# Run all tests
pytest

# Run specific test module
pytest tests/test_extractors.py

# Run with coverage
pytest --cov=scraper tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Selenium WebDriver for browser automation
- BeautifulSoup for HTML parsing assistance
- Pandas for data manipulation and export

```
interactive-web-scraper/
│
├── README.md                    # Project documentation
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup file
│
├── src/
│   └── scraper/
│       ├── __init__.py
│       ├── core/               # Core scraping functionality
│       │   ├── __init__.py
│       │   ├── base_scraper.py
│       │   ├── interactive_scraper.py
│       │   └── template_scraper.py
│       │
│       ├── extractors/         # Data extraction modules
│       │   ├── __init__.py
│       │   ├── element_extractor.py
│       │   ├── table_extractor.py
│       │   └── metadata_extractor.py
│       │
│       ├── exporters/          # Data export modules
│       │   ├── __init__.py
│       │   ├── base_exporter.py
│       │   ├── json_exporter.py
│       │   ├── csv_exporter.py
│       │   ├── excel_exporter.py
│       │   └── html_exporter.py
│       │
│       ├── handlers/           # Special handlers
│       │   ├── __init__.py
│       │   ├── cookie_handler.py
│       │   ├── pagination_handler.py
│       │   └── load_more_handler.py
│       │
│       ├── models/             # Data models
│       │   ├── __init__.py
│       │   └── data_models.py
│       │
│       ├── utils/              # Utility functions
│       │   ├── __init__.py
│       │   ├── selectors.py
│       │   ├── retry.py
│       │   └── logging_config.py
│       │
│       └── config/             # Configuration
│           ├── __init__.py
│           └── settings.py
│
├── assets/                     # Static assets
│   └── js/
│       └── interactive_selector.js
│
├── templates/                  # Scraping templates
│   └── examples/
│       └── gibson_dunn.json
│
├── output/                     # Default output directory
│   └── .gitkeep
│
├── logs/                       # Log files
│   └── .gitkeep
│
├── examples/                   # Usage examples
│   ├── basic_usage.py
│   ├── template_creation.py
│   ├── batch_scraping.py
│   └── large_dataset_example.py
│
└── tests/                      # Unit tests
    ├── __init__.py
    ├── test_base_scraper.py
    ├── test_extractors.py
    ├── test_exporters.py
    └── test_handlers.py
```
