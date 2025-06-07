# Enhanced Web Scraper v2.0 - New Features Guide

## Overview

The Enhanced Web Scraper v2.0 includes powerful new features that make web scraping more robust, intelligent, and respectful. This guide covers all the new capabilities and how to use them.

## 🚀 Quick Start with New Features

```bash
# Install dependencies including new ones
pip install -r requirements.txt

# For Playwright support (optional but recommended)
pip install playwright
playwright install

# For AI-powered element detection (optional)
pip install sentence-transformers numpy

# Run enhanced CLI
python -m scraper
```

## 🎯 New Features

### 1. Pattern-Based Extraction

Automatically extract common data types without specifying selectors:

**Supported Patterns:**
- **Emails**: Finds email addresses with validation
- **Phone Numbers**: US and international formats
- **Addresses**: Street addresses with zip codes
- **Dates**: Various date formats
- **Prices**: Currency amounts
- **Education**: Degrees (JD, MBA, PhD, etc.)
- **Bar Admissions**: Legal credentials
- **Social Media**: LinkedIn, Twitter, Facebook URLs

**Usage in Templates:**
```json
{
  "detail_page_rules": {
    "fields": {
      "email": "",  // Empty selector triggers pattern extraction
      "phone": ""
    },
    "extraction_patterns": {
      "email": {
        "enabled": true,
        "context_keywords": ["contact", "email"]
      },
      "phone": {
        "enabled": true,
        "context_keywords": ["phone", "tel", "call"]
      }
    }
  }
}
```

### 2. Multiple Scraping Engines

Choose the best engine for your needs:

#### **Selenium** (Default)
- ✅ Full JavaScript support
- ✅ Interactive element selection
- ✅ Handles dynamic content
- ❌ Slower performance

#### **Playwright** (Recommended for modern sites)
- ✅ Faster than Selenium
- ✅ Better JavaScript handling
- ✅ Network interception
- ✅ Multiple browser support (Chromium, Firefox, WebKit)
- ❌ Requires separate installation

#### **Requests** (For static sites)
- ✅ Extremely fast
- ✅ Low resource usage
- ✅ Good for APIs
- ❌ No JavaScript support
- ❌ No interactive selection

### 3. Rate Limiting

Be respectful to websites with built-in rate limiting:

**Presets:**
- **respectful_bot**: 0.2 req/sec (very safe)
- **conservative**: 0.5 req/sec (slow but respectful)
- **moderate**: 1 req/sec (balanced)
- **aggressive**: 5 req/sec (fast but risky)

**Features:**
- Per-domain tracking
- Burst tokens for occasional speed-ups
- Request queuing with timeouts
- Statistics tracking

### 4. Template Migration System

Automatically update old templates to use new features:

```bash
# Migrate all templates
python migrate_templates.py

# Or use CLI
python -m scraper migrate
```

**Migration Path:**
- v1.0 → v2.0: Adds pattern extraction, engine selection
- v2.0 → v2.1: Adds rate limiting, fallback strategies

### 5. Advanced Selector Strategies

Multiple fallback methods to find elements:

#### **Text-Based Selection**
Find elements by their visible text:
```python
# Finds "Email:" label with fuzzy matching
elements = advanced.find_by_text_content("Email:", fuzzy=True)
```

#### **Proximity-Based Selection**
Find elements near other elements:
```python
# Find value near a label
nearby = advanced.find_by_proximity(label_element, max_distance=200)
```

#### **Visual Pattern Matching**
Find elements by their visual role:
```python
# Find all buttons on the page
buttons = advanced.find_by_visual_pattern("button")
```

#### **AI-Powered Semantic Matching** (Optional)
Find elements by meaning:
```python
# Find elements semantically similar to description
elements = advanced.find_by_semantic_similarity("contact information")
```

## 📝 Enhanced Template Creation

The interactive template creation now includes:

1. **Engine Selection**: Choose between Selenium, Playwright, or Requests
2. **Rate Limiting Configuration**: Set appropriate speed limits
3. **Pattern Extraction Setup**: Enable automatic data extraction
4. **Fallback Strategies**: Configure backup element selection methods
5. **Advanced Selectors**: Add text-based fallbacks for each field

### Example Enhanced Template Creation Flow:

```
🔧 Enhanced Interactive Template Creation v2.0
==================================================

⚙️  Select Scraping Engine:
1. Selenium (Default) - Full JavaScript support
2. Playwright - Faster JavaScript handling
3. Requests - Fast for static HTML

> 2

⏱️  Configure Rate Limiting:
1. Respectful Bot - 0.2 req/sec
2. Conservative - 0.5 req/sec
3. Moderate - 1 req/sec
4. Aggressive - 5 req/sec
5. No rate limiting

> 1

🔍 Configure Pattern-Based Extraction:
Enable email extraction? [Y/n]: y
Enable phone extraction? [Y/n]: y
Enable education extraction? [Y/n]: y

🛡️  Configure Fallback Strategies:
Enable text-based selection? [Y/n]: y
Enable proximity selection? [Y/n]: y
```

## 🔄 Template Structure v2.1

Enhanced templates include new sections:

```json
{
  "name": "enhanced_template",
  "version": "2.1",
  "engine": "playwright",
  "rate_limiting": {
    "enabled": true,
    "preset": "respectful_bot"
  },
  "site_info": {
    "url": "https://example.com"
  },
  "scraping_type": "list_detail",
  "list_page_rules": {
    "fields": {
      "name": "h3.name",
      "title": ".position"
    },
    "advanced_selectors": {
      "use_text_content": {
        "name": "Name:",
        "title": "Position:"
      }
    },
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
  "fallback_strategies": {
    "text_based_selection": true,
    "proximity_selection": true,
    "pattern_matching_primary": false
  }
}
```

## 🛠️ CLI Commands

### New Commands:

```bash
# Create enhanced template
python -m scraper create

# Apply template with options
python -m scraper apply template.json \
  --engine playwright \
  --rate-limit respectful_bot \
  --export json csv

# Migrate templates
python -m scraper migrate [template.json]

# Test pattern extraction
python -m scraper test-patterns --text "Contact: john@example.com (555) 123-4567"

# Analyze website
python -m scraper analyze https://example.com
```

## 🔍 Pattern Extraction Examples

### Test Pattern Extraction:
```python
from scraper.extractors.pattern_extractor import PatternExtractor

extractor = PatternExtractor()
text = """
John Doe, JD, Harvard Law School, 2010
Email: john.doe@lawfirm.com
Phone: (555) 123-4567
Admitted to the New York Bar in 2011.
"""

# Extract specific pattern
email = extractor.extract(text, 'email')  # john.doe@lawfirm.com

# Extract all occurrences
educations = extractor.extract_all(text, 'education')  # ['JD, Harvard Law School, 2010']

# Extract multiple patterns
data = extractor.extract_multiple_patterns(text, ['email', 'phone', 'bar_admission'])
```

## ⚡ Performance Comparison

| Engine | JavaScript | Speed | Resource Usage | Best For |
|--------|------------|-------|----------------|----------|
| Selenium | ✅ Full | ⭐⭐ | High | Complex interactions |
| Playwright | ✅ Full | ⭐⭐⭐⭐ | Medium | Modern web apps |
| Requests | ❌ None | ⭐⭐⭐⭐⭐ | Low | Static sites, APIs |

## 🚨 Troubleshooting

### Playwright Not Working
```bash
# Install Playwright
pip install playwright
playwright install

# If still issues, install specific browser
playwright install chromium
```

### Rate Limiting Too Slow
- Use burst tokens for occasional speed-ups
- Adjust preset in template configuration
- Consider parallel scraping with thread pool

### Pattern Extraction Missing Data
- Add more context keywords
- Check if data format matches pattern
- Use custom patterns for unique formats

### Elements Not Found
1. Try text-based fallback
2. Enable proximity selection
3. Use more general selectors
4. Check if content is dynamically loaded

## 🎯 Best Practices

1. **Always use rate limiting** - Be respectful to websites
2. **Start with pattern extraction** - Let the scraper find data automatically
3. **Configure fallbacks** - Make your scrapers resilient to changes
4. **Use Playwright for modern sites** - Better performance than Selenium
5. **Test patterns first** - Use `test-patterns` command before scraping
6. **Migrate old templates** - Take advantage of new features

## 📚 Advanced Examples

### Custom Pattern Addition
```python
extractor = PatternExtractor()
extractor.add_custom_pattern(
    'case_number',
    r'Case No\.\s*(\d{4}-[A-Z]{2}-\d{4})',
    context_keywords=['case', 'docket']
)
```

### Composite Selection Strategy
```python
# Find element using multiple strategies
strategies = [
    {'type': 'text', 'text': 'Email:', 'fuzzy': True},
    {'type': 'css', 'selector': '.contact-info'}
]
elements = advanced.find_by_composite_strategy(strategies)
```

### Rate-Limited Parallel Scraping
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    for url in urls:
        # Rate limiter ensures respectful scraping
        rate_limiter.acquire(url)
        executor.submit(scrape_page, url)
```

## 🔮 Future Enhancements

Coming soon:
- Visual element detection using computer vision
- Automatic CAPTCHA handling
- Cloud deployment options
- API endpoint generation from templates
- Machine learning for adaptive selectors

---

For more information, see the [examples](examples/) directory or run the interactive demos with `python examples/advanced_features_demo.py`.