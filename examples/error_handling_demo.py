# examples/error_handling_demo.py
"""
Demonstration of enhanced error handling in the interactive web scraper.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.scraper.core import EnhancedInteractiveScraper
from src.scraper.utils.input_validators import (
    get_validated_url,
    get_validated_field_name,
    get_validated_choice,
    InputValidator,
    ErrorHandler,
    PromptFormatter
)


def demo_url_validation():
    """Demonstrate URL validation with error handling"""
    print("\n" + "="*50)
    print("🌐 URL Validation Demo")
    print("="*50)
    
    # Get URL with validation
    url = get_validated_url(
        prompt="Enter a website URL to scrape",
        default="https://example.com",
        max_attempts=3
    )
    
    if url:
        print(f"\n✅ Valid URL accepted: {url}")
    else:
        print("\n❌ Failed to get valid URL")


def demo_field_validation():
    """Demonstrate field name validation"""
    print("\n" + "="*50)
    print("📝 Field Name Validation Demo")
    print("="*50)
    
    existing_fields = ["name", "price", "description"]
    print(f"Existing fields: {', '.join(existing_fields)}")
    
    # Get multiple field names
    fields = []
    while len(fields) < 3:
        field_name = get_validated_field_name(
            prompt=f"Enter field name #{len(fields) + 1} (or 'done' to finish)",
            existing_fields=existing_fields + fields,
            max_attempts=3
        )
        
        if not field_name or field_name.lower() == 'done':
            break
        
        fields.append(field_name)
        print(f"✅ Added field: {field_name}")
    
    print(f"\n📋 Total fields collected: {fields}")


def demo_choice_validation():
    """Demonstrate choice validation"""
    print("\n" + "="*50)
    print("🔢 Choice Selection Demo")
    print("="*50)
    
    scraping_types = {
        "list": "Extract data from a list page",
        "detail": "Extract data from detail pages",
        "both": "Extract from both list and detail pages"
    }
    
    choice = get_validated_choice(
        prompt="Select scraping type",
        choices=scraping_types,
        default="both",
        max_attempts=3
    )
    
    if choice:
        print(f"\n✅ Selected: {choice} - {scraping_types[choice]}")
    else:
        print("\n❌ No choice made")


def demo_error_recovery():
    """Demonstrate error recovery in scraping"""
    print("\n" + "="*50)
    print("🔧 Error Recovery Demo")
    print("="*50)
    
    error_handler = ErrorHandler()
    formatter = PromptFormatter()
    
    # Simulate operations with potential errors
    operations = [
        ("Navigate to website", True),
        ("Find cookie banner", False),  # This will "fail"
        ("Extract data", True),
        ("Save results", True)
    ]
    
    for operation, will_succeed in operations:
        print(f"\n🔄 Attempting: {operation}")
        
        if will_succeed:
            print(formatter.format_success(f"{operation} completed"))
        else:
            print(formatter.format_warning(
                f"{operation} failed",
                "Will retry with alternative method"
            ))
            
            # Simulate retry
            print("   🔄 Retrying...")
            print(formatter.format_success(f"{operation} completed (alternative method)"))


def demo_interactive_scraper_with_validation():
    """Demonstrate the enhanced interactive scraper"""
    print("\n" + "="*50)
    print("🕷️ Interactive Scraper with Enhanced Error Handling")
    print("="*50)
    
    # This would normally create a real scraper instance
    print("\nThe enhanced scraper now includes:")
    print("  ✅ URL validation with auto-correction")
    print("  ✅ Field name sanitization")
    print("  ✅ Duplicate field detection")
    print("  ✅ Retry logic for failed operations")
    print("  ✅ User-friendly error messages")
    print("  ✅ Suggestions for fixing errors")
    print("  ✅ Graceful handling of interruptions")
    
    # Example of how errors are now handled
    print("\n📋 Example Error Scenarios:")
    
    scenarios = [
        {
            "input": "example.com",
            "error": "Missing protocol",
            "fix": "Automatically adds https://",
            "result": "https://example.com"
        },
        {
            "input": "my field name!",
            "error": "Invalid characters in field name",
            "fix": "Sanitizes to valid format",
            "result": "my_field_name"
        },
        {
            "input": "name (duplicate)",
            "error": "Field already exists",
            "fix": "Suggests alternative or adds number",
            "result": "name_1"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n  Input: '{scenario['input']}'")
        print(f"  ⚠️  {scenario['error']}")
        print(f"  🔧 {scenario['fix']}")
        print(f"  ✅ Result: '{scenario['result']}'")


def demo_batch_validation():
    """Demonstrate batch input validation"""
    print("\n" + "="*50)
    print("📦 Batch Validation Demo")
    print("="*50)
    
    validator = InputValidator()
    formatter = PromptFormatter()
    
    # Validate multiple URLs
    test_urls = [
        "https://example.com",
        "www.test.com",
        "invalid url with spaces",
        "htp://typo.com",
        "example",
        "http://valid-domain.org/path"
    ]
    
    print("\n🌐 Validating URLs:")
    for url in test_urls:
        is_valid, result = validator.validate_url(url)
        if is_valid:
            print(f"  ✅ '{url}' → '{result}'")
        else:
            print(f"  ❌ '{url}' → {result}")
    
    # Validate selectors
    test_selectors = [
        ("div.class", "css", True),
        ("//div[@id='test']", "xpath", True),
        ("div[data-id='test", "css", False),  # Unbalanced bracket
        ("div > span", "css", True),
        ("invalid<selector>", "css", False)
    ]
    
    print("\n🎯 Validating Selectors:")
    for selector, selector_type, expected in test_selectors:
        is_valid, error = validator.validate_selector(selector, selector_type)
        status = "✅" if is_valid else "❌"
        message = "Valid" if is_valid else error
        print(f"  {status} {selector_type.upper()}: '{selector}' → {message}")


def main():
    """Run all demos"""
    print("🚀 Enhanced Error Handling Demonstration")
    print("="*70)
    
    demos = [
        ("URL Validation", demo_url_validation),
        ("Field Name Validation", demo_field_validation),
        ("Choice Selection", demo_choice_validation),
        ("Error Recovery", demo_error_recovery),
        ("Batch Validation", demo_batch_validation),
        ("Interactive Scraper Features", demo_interactive_scraper_with_validation)
    ]
    
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"{i}. {name}")
    print(f"{len(demos) + 1}. Run all demos")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nSelect demo (0-{}): ".format(len(demos) + 1)).strip()
            
            if not choice:
                continue
                
            choice_num = int(choice)
            
            if choice_num == 0:
                print("\n👋 Goodbye!")
                break
            elif 1 <= choice_num <= len(demos):
                demos[choice_num - 1][1]()
                input("\n\nPress Enter to continue...")
            elif choice_num == len(demos) + 1:
                for name, func in demos:
                    try:
                        func()
                        input("\n\nPress Enter to continue to next demo...")
                    except KeyboardInterrupt:
                        print("\n\n⚠️  Demo interrupted")
                        break
            else:
                print("❌ Invalid choice. Please try again.")
                
        except ValueError:
            print("❌ Please enter a valid number.")
        except KeyboardInterrupt:
            print("\n\n⚠️  Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()