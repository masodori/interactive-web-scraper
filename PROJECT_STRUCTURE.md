# Project Structure - Interactive Web Scraper v2.0

## 📁 Directory Overview

```
interactive-web-scraper/
├── README.md                    # Main documentation
├── requirements.txt             # Dependencies
├── setup.py                     # Package configuration
├── test_installation.py         # Installation verification
├── PROJECT_STRUCTURE.md         # This file
├── src/scraper/                 # Main package
│   ├── __init__.py             # Package exports
│   ├── improved_cli.py         # Enhanced CLI (main entry point)
│   ├── config/                 # Configuration
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── core/                   # Core scraping functionality
│   │   ├── __init__.py
│   │   ├── base_scraper.py             # Base scraper class
│   │   ├── enhanced_interactive_scraper.py  # Main interactive scraper
│   │   ├── enhanced_template_scraper.py     # Template application
│   │   ├── multi_engine_scraper.py          # Multi-engine support
│   │   ├── playwright_scraper.py            # Playwright engine
│   │   ├── requests_scraper.py              # Requests engine
│   │   └── template_scraper.py              # Template functionality
│   ├── exporters/              # Export formats
│   │   ├── __init__.py
│   │   ├── base_exporter.py
│   │   ├── csv_exporter.py
│   │   ├── excel_exporter.py
│   │   ├── html_exporter.py
│   │   └── json_exporter.py
│   ├── extractors/             # Data extraction
│   │   ├── __init__.py
│   │   ├── advanced_selectors.py
│   │   ├── element_extractor.py
│   │   ├── enhanced_element_extractor.py
│   │   ├── metadata_extractor.py
│   │   ├── pattern_extractor.py
│   │   ├── requests_extractor.py
│   │   └── table_extractor.py
│   ├── handlers/               # Specialized handlers
│   │   ├── __init__.py
│   │   ├── cookie_handler.py
│   │   ├── load_more_handler.py
│   │   └── pagination_handler.py
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   └── data_models.py
│   └── utils/                  # Utilities
│       ├── __init__.py
│       ├── input_validators.py
│       ├── logging_config.py
│       ├── rate_limiter.py
│       ├── retry.py
│       ├── selectors.py
│       ├── template_migration.py
│       └── user_experience.py      # Enhanced UX utilities
├── examples/                   # Example scripts
│   ├── advanced_features_demo.py
│   ├── basic_usage.py
│   └── error_handling_demo.py
├── templates/                  # Scraping templates
│   └── example_template.json
├── output/                     # Exported data
├── logs/                       # Log files
└── assets/                     # Static assets
    └── js/
        └── interactive_selector.js
```

## 🎯 Key Components

### Main Entry Point
- **`src/scraper/improved_cli.py`**: Enhanced CLI with user-friendly interface

### Core Engines
- **`enhanced_interactive_scraper.py`**: Main scraper with interactive selection
- **`multi_engine_scraper.py`**: Support for Selenium, Playwright, Requests
- **`enhanced_template_scraper.py`**: Apply saved templates

### User Experience
- **`utils/user_experience.py`**: Colored output, progress bars, tutorials
- **`utils/input_validators.py`**: Input validation and suggestions

### Data Processing
- **`extractors/pattern_extractor.py`**: Smart pattern recognition
- **`exporters/`**: Multiple output formats (JSON, CSV, Excel, HTML)

### Configuration
- **`config/settings.py`**: Application settings and paths
- **`models/data_models.py`**: Template and result structures

## 🚀 Usage Patterns

### 1. Interactive Mode
```bash
python -m scraper.improved_cli
```

### 2. Command Line
```bash
python -m scraper.improved_cli --apply template.json --format csv
```

### 3. Programmatic
```python
from scraper.core import EnhancedInteractiveScraper
scraper = EnhancedInteractiveScraper()
scraper.create_template()
```

## 🎨 Features by Module

### Enhanced CLI (`improved_cli.py`)
- First-time user detection
- Interactive tutorials
- Engine comparison
- Step-by-step guidance
- Batch processing
- Error recovery

### User Experience (`utils/user_experience.py`)
- Colored terminal output
- Progress bars and animations
- CSS selector help
- Common issues guide
- Input validation

### Pattern Extraction (`extractors/pattern_extractor.py`)
- Email detection
- Phone number extraction
- Date parsing
- Price recognition
- Education credentials
- Address parsing

### Multi-Engine Support
- **Selenium**: Maximum compatibility
- **Playwright**: Modern performance
- **Requests**: Speed for static sites

## 📝 Template Structure

Templates are JSON files with this structure:
- `engine`: selenium|playwright|requests
- `scraping_type`: single_page|list_only|list_detail
- `list_page_rules`: Container and field selectors
- `detail_page_rules`: Individual page field extraction
- `extraction_patterns`: Automatic pattern detection
- `fallback_strategies`: Alternative selection methods
- `rate_limiting`: Respectful scraping configuration

## 🔧 Removed Components

The following files were removed during streamlining:
- Redundant CLI versions (cli.py, enhanced_cli.py)
- Multiple interactive scraper versions
- Temporary fix scripts
- Test templates
- Duplicate documentation
- Playwright sync wrapper (consolidated)

## 🧪 Testing

Run the installation test:
```bash
python test_installation.py
```

This verifies:
- All modules import correctly
- Dependencies are installed
- CLI functionality works

## 📚 Documentation

- **README.md**: Main user guide
- **examples/**: Practical usage examples
- Built-in help system in CLI
- Interactive tutorials for new users

---

The project is now streamlined with clear separation of concerns and enhanced user experience while maintaining all core functionality.