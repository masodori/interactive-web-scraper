# Interactive Web Scraper v2.0

A powerful, user-friendly web scraping framework with multi-engine support, intelligent pattern extraction, and enhanced user experience.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# For Playwright support (recommended)
pip install playwright
playwright install

# Run the improved CLI
python -m scraper.improved_cli
```

## 🎯 Key Features

### 🎨 Enhanced User Experience
- **Colored output** with progress bars and loading animations
- **Interactive tutorials** for first-time users
- **Step-by-step guidance** with helpful tips
- **Smart error recovery** with suggested actions

### ⚙️ Multi-Engine Support
Choose the best engine for your needs:

| Engine | JavaScript | Speed | Best For |
|--------|------------|-------|----------|
| **Selenium** | ✅ Full | ⭐⭐ | Complex interactions, maximum compatibility |
| **Playwright** | ✅ Full | ⭐⭐⭐⭐ | Modern web apps, better performance |
| **Requests** | ❌ None | ⭐⭐⭐⭐⭐ | Static HTML sites, APIs |

### 🔍 Smart Pattern Extraction
Automatically find common data types without selectors:
- **Emails**: Various formats with validation
- **Phone Numbers**: US and international formats  
- **Dates**: Multiple date formats
- **Prices**: Currency amounts
- **Education**: Degrees (JD, MBA, PhD, etc.)
- **Addresses**: Street addresses with validation

### 🛡️ Fallback Strategies
- **Text-based selection**: Find elements by label text
- **Proximity selection**: Find elements near other elements
- **CSS selector fallbacks**: Multiple selectors per field

### ⏱️ Rate Limiting
Be respectful with built-in rate limiting:
- **Respectful Bot**: 0.2 req/sec (very safe)
- **Conservative**: 0.5 req/sec (slow but respectful)
- **Moderate**: 1 req/sec (balanced)
- **Aggressive**: 5 req/sec (fast but risky)

## 📋 Usage

### Interactive Mode
```bash
python -m scraper.improved_cli
```

### Command Line Mode
```bash
# Apply template directly
python -m scraper.improved_cli --apply my_template.json --format csv

# Show tutorial
python -m scraper.improved_cli --tutorial

# Show version
python -m scraper.improved_cli --version
```

## 🔧 Creating Your First Template

1. **Start the tool**: Run the improved CLI
2. **Select "Create Template"**: Option 1 in the main menu
3. **Enter URL**: Tool validates and adds https:// if needed
4. **Choose Engine**: See comparison and select best option
5. **Select Elements**: 
   - **Selenium/Playwright**: Interactive overlay for clicking elements
   - **Requests**: Manual CSS selector entry with examples
6. **Configure Options**: Rate limiting, pattern extraction, fallbacks
7. **Save Template**: Give it a descriptive name

## 📄 Template Structure

```json
{
  "name": "example_scraper",
  "engine": "playwright",
  "version": "2.1",
  "site_info": {
    "url": "https://example.com"
  },
  "scraping_type": "list_detail",
  "list_page_rules": {
    "fields": {
      "title": "h3.title",
      "link": "a.profile-link"
    },
    "repeating_item_selector": ".item",
    "load_strategy": {
      "type": "auto",
      "consecutive_failure_limit": 3
    }
  },
  "detail_page_rules": {
    "fields": {
      "email": "",  // Pattern extraction
      "phone": "",  // Pattern extraction
      "bio": ".biography"
    },
    "extraction_patterns": {
      "email": {
        "enabled": true,
        "context_keywords": ["email", "contact"]
      },
      "phone": {
        "enabled": true,
        "context_keywords": ["phone", "tel"]
      }
    }
  },
  "rate_limiting": {
    "enabled": true,
    "preset": "respectful_bot"
  },
  "fallback_strategies": {
    "text_based_selection": true,
    "proximity_selection": true
  }
}
```

## 🎓 Tutorial Features

The tool includes comprehensive help:

### 1. Engine Comparison
Visual comparison showing pros/cons of each engine

### 2. CSS Selector Guide
```
div.classname     → Select div with class 'classname'
#id              → Select element with ID 'id'  
div > p          → Select p that is direct child of div
a[href]          → Select links with href attribute
```

### 3. Common Issues & Solutions
- No elements found
- JavaScript not loading  
- Rate limit errors
- Template compatibility issues

## 📦 Project Structure

```
src/scraper/
├── improved_cli.py              # Main CLI with enhanced UX
├── config/                      # Configuration settings
├── core/
│   ├── enhanced_interactive_scraper.py  # Main scraper implementation
│   ├── enhanced_template_scraper.py     # Template application
│   ├── multi_engine_scraper.py          # Multi-engine support
│   ├── playwright_scraper.py            # Playwright engine
│   └── requests_scraper.py              # Requests engine
├── extractors/                  # Data extraction modules
├── exporters/                   # Export formats (JSON, CSV, Excel, HTML)
├── handlers/                    # Cookie, pagination, load more handlers
├── models/                      # Data models and templates
└── utils/                       # Utilities and user experience helpers
```

## 🛠️ Installation Options

### Option 1: Development Mode
```bash
git clone <repository-url>
cd interactive-web-scraper
pip install -r requirements.txt
python -m scraper.improved_cli
```

### Option 2: Package Installation
```bash
pip install -e .
scraper-improved
```

## 🎯 Best Practices

1. **Start with interactive tutorials** for first-time users
2. **Choose the right engine**:
   - Selenium/Playwright for JavaScript sites
   - Requests for simple HTML sites
3. **Use pattern extraction** for common data types
4. **Enable fallback strategies** for resilience
5. **Respect rate limits** to avoid blocks
6. **Test templates** before batch processing

## 🔍 Example Workflows

### Scraping Contact Information
```python
# Enable pattern extraction for automatic detection
template = {
    "detail_page_rules": {
        "fields": {
            "email": "",     # Empty = pattern extraction
            "phone": "",     # Empty = pattern extraction
            "name": "h1"     # CSS selector
        },
        "extraction_patterns": {
            "email": {"enabled": True},
            "phone": {"enabled": True}
        }
    }
}
```

### E-commerce Product Scraping
```python
# List + detail pages with fallbacks
template = {
    "scraping_type": "list_detail",
    "list_page_rules": {
        "fields": {
            "title": ".product-title",
            "price": ".price",
            "link": "a.product-link"
        },
        "advanced_selectors": {
            "use_text_content": {
                "price": "Price:"  # Fallback: find by label
            }
        }
    }
}
```

## 🚨 Troubleshooting

### Engine Issues
- **Playwright not installed**: Run `pip install playwright && playwright install`
- **Browser not found**: Run `playwright install chromium`
- **Selenium WebDriver**: Automatically managed by webdriver-manager

### Scraping Issues  
- **No elements found**: Try text-based fallbacks or more general selectors
- **Rate limited**: Use slower preset or check robots.txt
- **JavaScript not loading**: Switch from Requests to Selenium/Playwright

### Template Issues
- **Empty selectors**: Check that interactive selection worked
- **Validation errors**: Ensure template structure matches models
- **Migration needed**: Old templates auto-migrate to new format

## 📊 Export Formats

- **JSON**: Structured data with metadata
- **CSV**: Flat format for spreadsheets  
- **Excel**: Formatted with headers and styling
- **HTML**: Styled tables with search functionality

## 🎉 What's New in v2.0

- ✅ **Enhanced User Experience** with colors and animations
- ✅ **Multi-Engine Support** (Selenium, Playwright, Requests)
- ✅ **Interactive Tutorials** for first-time users
- ✅ **Smart Pattern Extraction** for common data types
- ✅ **Fallback Strategies** for resilient scraping
- ✅ **Rate Limiting** with respectful presets
- ✅ **Batch Processing** for multiple templates
- ✅ **Better Error Handling** with recovery suggestions
- ✅ **Command-Line Support** for automation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

**Happy Scraping!** 🕷️✨

For questions or issues, please check the built-in tutorials and help system first.