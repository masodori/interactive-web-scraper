# examples/basic_usage.py
"""
Basic usage examples for the interactive web scraper.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.scraper.core.base_scraper import BaseScraper
from src.scraper.extractors.element_extractor import ElementExtractor
from src.scraper.config.settings import Config
from src.scraper.models.data_models import ExportFormat, ScrapedItem, ScrapeResult
import json
from datetime import datetime


def example_simple_scraping():
    """Example: Basic page scraping with cookie handling"""
    print("=" * 50)
    print("Example 1: Simple Page Scraping")
    print("=" * 50)
    
    # Initialize scraper
    with BaseScraper(headless=False) as scraper:
        # Navigate to a website
        url = "https://example.com"
        print(f"\nNavigating to {url}...")
        scraper.navigate_to(url)
        
        # Handle cookies (if any)
        cookie_result = scraper.cookie_handler.accept_cookies()
        if cookie_result:
            print(f"✓ Cookie banner handled using: {cookie_result}")
        
        # Extract data
        extractor = ElementExtractor(scraper.driver)
        
        # Extract title
        title = scraper.get_page_title()
        print(f"\nPage Title: {title}")
        
        # Extract main heading
        heading = extractor.extract_text("h1")
        print(f"Main Heading: {heading}")
        
        # Extract all paragraphs
        paragraphs = extractor.extract_text("p", multiple=True)
        print(f"\nFound {len(paragraphs)} paragraph(s)")
        if paragraphs:
            print(f"First paragraph: {paragraphs[0][:100]}...")
        
        # Take screenshot
        screenshot_path = scraper.take_screenshot("example_page.png")
        print(f"\nScreenshot saved to: {screenshot_path}")


def example_list_extraction():
    """Example: Extract data from a list/table page"""
    print("\n" + "=" * 50)
    print("Example 2: List Data Extraction")
    print("=" * 50)
    
    with BaseScraper(headless=True) as scraper:
        # Navigate to a page with lists/tables
        url = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
        print(f"\nNavigating to {url}...")
        scraper.navigate_to(url)
        
        # Extract table data
        extractor = ElementExtractor(scraper.driver)
        
        # Find the first table
        print("\nExtracting table data...")
        
        # Extract table headers
        headers = extractor.extract_text("table.wikitable th", multiple=True)
        print(f"Table headers: {headers[:5]}...")  # Show first 5
        
        # Extract first 10 rows
        rows = []
        for i in range(1, 11):
            row_data = extractor.extract_text(f"table.wikitable tbody tr:nth-of-type({i}) td", multiple=True)
            if row_data:
                rows.append(row_data)
        
        print(f"\nExtracted {len(rows)} rows")
        
        # Display first few rows
        for i, row in enumerate(rows[:3]):
            print(f"Row {i+1}: {row[:3]}...")  # Show first 3 columns


def example_link_extraction():
    """Example: Extract all links from a page"""
    print("\n" + "=" * 50)
    print("Example 3: Link Extraction")
    print("=" * 50)
    
    with BaseScraper(headless=True) as scraper:
        url = "https://news.ycombinator.com"
        print(f"\nNavigating to {url}...")
        scraper.navigate_to(url)
        
        extractor = ElementExtractor(scraper.driver)
        
        # Extract all story links
        print("\nExtracting story links...")
        story_links = []
        
        # HackerNews specific selectors
        link_elements = scraper.find_elements_safe(scraper.driver.find_element_by_css_selector, ".titleline > a")
        
        # Use more general selector
        links = extractor.extract_links("table", "a.titleline")
        
        print(f"\nFound {len(links)} story links")
        
        # Display first 5 links
        for i, link in enumerate(links[:5]):
            print(f"\n{i+1}. {link['text']}")
            print(f"   URL: {link['href']}")


def example_form_extraction():
    """Example: Extract form data"""
    print("\n" + "=" * 50)
    print("Example 4: Form Data Extraction")
    print("=" * 50)
    
    with BaseScraper(headless=False) as scraper:
        # Create a simple HTML form for demonstration
        html_content = """
        <html>
        <body>
            <form id="test-form">
                <input name="username" type="text" value="john_doe">
                <input name="email" type="email" value="john@example.com">
                <select name="country">
                    <option value="us" selected>United States</option>
                    <option value="uk">United Kingdom</option>
                </select>
                <textarea name="comments">This is a test comment</textarea>
                <input name="subscribe" type="checkbox" checked>
            </form>
        </body>
        </html>
        """
        
        # Load HTML content
        scraper.driver.get("data:text/html;charset=utf-8," + html_content)
        
        extractor = ElementExtractor(scraper.driver)
        
        # Extract form values
        form_data = extractor.extract_form_values("#test-form")
        
        print("\nExtracted form data:")
        for field, value in form_data.items():
            print(f"  {field}: {value}")


def example_structured_scraping():
    """Example: Extract structured data using field mapping"""
    print("\n" + "=" * 50)
    print("Example 5: Structured Data Extraction")
    print("=" * 50)
    
    with BaseScraper(headless=True) as scraper:
        # Navigate to a product page (example)
        url = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
        print(f"\nNavigating to {url}...")
        scraper.navigate_to(url)
        
        extractor = ElementExtractor(scraper.driver)
        
        # Define field mapping for product data
        field_map = {
            "title": "h1",
            "price": "p.price_color",
            "availability": "p.availability",
            "description": "#product_description + p",
            "upc": "table tr:nth-of-type(1) td",
            "product_type": "table tr:nth-of-type(2) td",
        }
        
        # Extract structured data
        product_data = extractor.extract_structured_data("article.product_page", field_map)
        
        print("\nExtracted product data:")
        for field, value in product_data.items():
            if value:
                display_value = value[:50] + "..." if len(str(value)) > 50 else value
                print(f"  {field}: {display_value}")
        
        # Create scraped item
        item = ScrapedItem(
            url=scraper.get_current_url(),
            timestamp=datetime.now().isoformat(),
            data=product_data
        )
        
        # Save to JSON
        output_path = Config.OUTPUT_DIR / "product_data.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(item.to_dict(), f, indent=2)
        
        print(f"\nData saved to: {output_path}")


def example_error_handling():
    """Example: Demonstrate error handling and retries"""
    print("\n" + "=" * 50)
    print("Example 6: Error Handling")
    print("=" * 50)
    
    with BaseScraper(headless=True) as scraper:
        # Try to navigate to an invalid URL
        print("\nTrying invalid URL...")
        result = scraper.navigate_to("https://this-domain-definitely-does-not-exist-12345.com")
        print(f"Navigation result: {result}")
        
        # Try to find non-existent element
        print("\nTrying to find non-existent element...")
        element = scraper.find_element_safe(scraper.driver.find_element_by_css_selector, "#non-existent-id")
        print(f"Element found: {element is not None}")
        
        # Demonstrate wait timeout
        print("\nDemonstrating wait timeout...")
        element = scraper.wait_for_element(
            scraper.driver.find_element_by_css_selector, 
            "#element-that-will-never-appear",
            timeout=2
        )
        print(f"Element after wait: {element is not None}")


def main():
    """Run all examples"""
    print("Interactive Web Scraper - Basic Usage Examples")
    print("=" * 50)
    
    examples = [
        ("Simple Page Scraping", example_simple_scraping),
        ("List Data Extraction", example_list_extraction),
        ("Link Extraction", example_link_extraction),
        ("Form Data Extraction", example_form_extraction),
        ("Structured Data Extraction", example_structured_scraping),
        ("Error Handling", example_error_handling)
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    print(f"{len(examples) + 1}. Run all examples")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nSelect an example (0-{}): ".format(len(examples) + 1))
            choice = int(choice)
            
            if choice == 0:
                print("Goodbye!")
                break
            elif 1 <= choice <= len(examples):
                examples[choice - 1][1]()
                input("\nPress Enter to continue...")
            elif choice == len(examples) + 1:
                for name, func in examples:
                    try:
                        func()
                    except Exception as e:
                        print(f"\nError in {name}: {e}")
                    input("\nPress Enter to continue to next example...")
            else:
                print("Invalid choice. Please try again.")
                
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    # Ensure output directory exists
    Config.ensure_directories()
    
    # Run examples
    main()