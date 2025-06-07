# src/scraper/utils/user_experience.py
"""
Enhanced user experience utilities for better guidance and usability.
"""

import time
from typing import Dict, List, Optional, Tuple
from colorama import init, Fore, Back, Style
import textwrap

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class UserExperience:
    """Provides enhanced user experience utilities"""
    
    @staticmethod
    def print_header(title: str, subtitle: str = "", emoji: str = "🔧"):
        """Print a styled header"""
        print("\n" + "=" * 60)
        print(f"{emoji}  {Fore.CYAN}{Style.BRIGHT}{title}{Style.RESET_ALL}")
        if subtitle:
            print(f"   {Fore.YELLOW}{subtitle}{Style.RESET_ALL}")
        print("=" * 60)
    
    @staticmethod
    def print_success(message: str):
        """Print a success message"""
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")
    
    @staticmethod
    def print_error(message: str):
        """Print an error message"""
        print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")
    
    @staticmethod
    def print_warning(message: str):
        """Print a warning message"""
        print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")
    
    @staticmethod
    def print_info(message: str):
        """Print an info message"""
        print(f"{Fore.BLUE}ℹ️  {message}{Style.RESET_ALL}")
    
    @staticmethod
    def print_step(step_num: int, total_steps: int, description: str):
        """Print a step indicator"""
        print(f"\n{Fore.MAGENTA}Step {step_num}/{total_steps}: {description}{Style.RESET_ALL}")
        print("-" * 40)
    
    @staticmethod
    def print_tip(message: str):
        """Print a helpful tip"""
        print(f"{Fore.CYAN}💡 TIP: {message}{Style.RESET_ALL}")
    
    @staticmethod
    def print_engine_comparison():
        """Print a detailed comparison of scraping engines"""
        print("\n" + "=" * 70)
        print(f"{Fore.CYAN}{Style.BRIGHT}🔍 SCRAPING ENGINE COMPARISON{Style.RESET_ALL}")
        print("=" * 70)
        
        engines = [
            {
                "name": "Selenium",
                "pros": [
                    "✓ Full JavaScript support",
                    "✓ Interactive element selection",
                    "✓ Handles dynamic content",
                    "✓ Most compatible"
                ],
                "cons": [
                    "✗ Slower performance",
                    "✗ Higher resource usage"
                ],
                "best_for": "Complex sites with heavy JavaScript",
                "speed": "★★☆☆☆"
            },
            {
                "name": "Playwright",
                "pros": [
                    "✓ Modern & fast",
                    "✓ Full JavaScript support",
                    "✓ Interactive selection",
                    "✓ Better performance than Selenium"
                ],
                "cons": [
                    "✗ Requires separate installation",
                    "✗ Newer, less documentation"
                ],
                "best_for": "Modern web apps, SPAs",
                "speed": "★★★★☆"
            },
            {
                "name": "Requests",
                "pros": [
                    "✓ Extremely fast",
                    "✓ Low resource usage",
                    "✓ No browser needed"
                ],
                "cons": [
                    "✗ No JavaScript support",
                    "✗ Manual selector input only",
                    "✗ Can't handle dynamic content"
                ],
                "best_for": "Static HTML sites, APIs",
                "speed": "★★★★★"
            }
        ]
        
        for engine in engines:
            print(f"\n{Fore.YELLOW}{Style.BRIGHT}{engine['name']}{Style.RESET_ALL}")
            print(f"Speed: {engine['speed']}")
            print(f"Best for: {Fore.CYAN}{engine['best_for']}{Style.RESET_ALL}")
            print("\nPros:")
            for pro in engine['pros']:
                print(f"  {Fore.GREEN}{pro}{Style.RESET_ALL}")
            print("\nCons:")
            for con in engine['cons']:
                print(f"  {Fore.RED}{con}{Style.RESET_ALL}")
            print("-" * 70)
    
    @staticmethod
    def print_selector_help():
        """Print CSS selector help and examples"""
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}{Style.BRIGHT}📚 CSS SELECTOR QUICK GUIDE{Style.RESET_ALL}")
        print("=" * 60)
        
        examples = [
            ("div.classname", "Select div with class 'classname'"),
            ("#id", "Select element with ID 'id'"),
            ("div > p", "Select p that is direct child of div"),
            ("div p", "Select all p inside div (any level)"),
            ("a[href]", "Select links with href attribute"),
            (":nth-child(2)", "Select 2nd child element"),
            (".class1.class2", "Element with both classes"),
            ("h1, h2, h3", "Select multiple elements")
        ]
        
        print("\nCommon CSS Selector Patterns:")
        for selector, description in examples:
            print(f"  {Fore.YELLOW}{selector:<20}{Style.RESET_ALL} → {description}")
        
        print(f"\n{Fore.CYAN}💡 TIP: In browser DevTools, right-click → Inspect → Right-click on element → Copy → Copy selector{Style.RESET_ALL}")
    
    @staticmethod
    def print_progress_bar(current: int, total: int, description: str = "Progress"):
        """Print a progress bar"""
        bar_length = 40
        progress = current / total if total > 0 else 0
        filled_length = int(bar_length * progress)
        
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        percentage = progress * 100
        
        print(f"\r{description}: |{bar}| {percentage:.1f}% ({current}/{total})", end="", flush=True)
        
        if current >= total:
            print()  # New line when complete
    
    @staticmethod
    def show_interactive_tutorial():
        """Show an interactive tutorial for first-time users"""
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}{Style.BRIGHT}🎓 INTERACTIVE SCRAPER TUTORIAL{Style.RESET_ALL}")
        print("=" * 60)
        
        tutorial_steps = [
            {
                "title": "Understanding Web Scraping",
                "content": """
Web scraping extracts data from websites. This tool helps you:
• Create reusable templates by clicking on elements
• Extract data from multiple pages automatically
• Handle different types of websites
                """
            },
            {
                "title": "Choosing the Right Engine",
                "content": """
• Use SELENIUM or PLAYWRIGHT for:
  - Sites with JavaScript (React, Vue, Angular)
  - Dynamic content that loads after page load
  - Interactive element selection
  
• Use REQUESTS for:
  - Simple HTML sites
  - When speed is critical
  - Server-side rendered content
                """
            },
            {
                "title": "Interactive Selection (Selenium/Playwright)",
                "content": """
When using interactive selection:
1. The browser will open (unless headless mode)
2. An overlay appears with instructions
3. Hover over elements - they'll be highlighted
4. Click to select an element
5. Click 'Done Selecting' when finished
                """
            },
            {
                "title": "Manual Selection (Requests)",
                "content": """
For manual selection:
1. Open the website in your browser
2. Right-click → Inspect Element
3. Find the CSS selector
4. Enter it when prompted
                """
            }
        ]
        
        for i, step in enumerate(tutorial_steps, 1):
            print(f"\n{Fore.YELLOW}{Style.BRIGHT}{i}. {step['title']}{Style.RESET_ALL}")
            print(textwrap.dedent(step['content']).strip())
            
            if i < len(tutorial_steps):
                input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}{Style.BRIGHT}✅ Tutorial Complete!{Style.RESET_ALL}")
        print("You're ready to create your first scraping template.\n")
    
    @staticmethod
    def confirm_action(message: str, default: bool = False) -> bool:
        """Enhanced confirmation prompt"""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{message} [{default_text}]: ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes']
    
    @staticmethod
    def get_choice_with_help(prompt: str, options: Dict[str, str], 
                           help_text: Optional[Dict[str, str]] = None,
                           default: Optional[str] = None) -> Optional[str]:
        """Get user choice with optional help text"""
        print(f"\n{prompt}")
        
        # Display options
        for key, description in options.items():
            is_default = f" {Fore.GREEN}(default){Style.RESET_ALL}" if key == default else ""
            print(f"  {Fore.YELLOW}{key}{Style.RESET_ALL}: {description}{is_default}")
        
        # Show help option if help text is provided
        if help_text:
            print(f"  {Fore.CYAN}?{Style.RESET_ALL}: Show detailed help")
        
        while True:
            choice_prompt = f"Choose [{'/'.join(options.keys())}]"
            if help_text:
                choice_prompt += "/?"
            if default:
                choice_prompt += f" (default: {default})"
            choice_prompt += ": "
            
            choice = input(choice_prompt).strip().lower()
            
            # Handle default
            if not choice and default:
                return default
            
            # Handle help
            if choice == "?" and help_text:
                print("\n" + "=" * 60)
                print(f"{Fore.CYAN}📖 DETAILED HELP{Style.RESET_ALL}")
                print("=" * 60)
                for key, help_content in help_text.items():
                    print(f"\n{Fore.YELLOW}{key}: {options.get(key, '')}{Style.RESET_ALL}")
                    print(textwrap.dedent(help_content).strip())
                print("=" * 60)
                continue
            
            # Validate choice
            if choice in options:
                return choice
            
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")
    
    @staticmethod
    def show_common_issues():
        """Show common issues and solutions"""
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}{Style.BRIGHT}🔧 COMMON ISSUES & SOLUTIONS{Style.RESET_ALL}")
        print("=" * 60)
        
        issues = [
            {
                "problem": "No elements found with selector",
                "solutions": [
                    "Check if the page has fully loaded",
                    "Verify the selector in browser DevTools",
                    "Try a more general selector",
                    "Check if content is in an iframe"
                ]
            },
            {
                "problem": "JavaScript content not loading",
                "solutions": [
                    "Switch from Requests to Selenium/Playwright",
                    "Increase wait time in settings",
                    "Check if site requires login/cookies"
                ]
            },
            {
                "problem": "Rate limit errors",
                "solutions": [
                    "Use a slower rate limit preset",
                    "Add delays between requests",
                    "Respect robots.txt"
                ]
            },
            {
                "problem": "Template not working on similar pages",
                "solutions": [
                    "Use more general selectors",
                    "Enable fallback strategies",
                    "Check if page structure varies"
                ]
            }
        ]
        
        for issue in issues:
            print(f"\n{Fore.YELLOW}❓ Problem: {issue['problem']}{Style.RESET_ALL}")
            print("Solutions:")
            for solution in issue['solutions']:
                print(f"  • {solution}")
    
    @staticmethod
    def animate_loading(message: str, duration: float = 2.0):
        """Show an animated loading message"""
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        end_time = time.time() + duration
        
        i = 0
        while time.time() < end_time:
            print(f"\r{frames[i % len(frames)]} {message}", end="", flush=True)
            time.sleep(0.1)
            i += 1
        
        print(f"\r✅ {message} - Done!", flush=True)


class ValidationHelper:
    """Provides validation and suggestions for user input"""
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate URL and provide suggestions
        Returns: (is_valid, cleaned_url, error_message)
        """
        import re
        from urllib.parse import urlparse
        
        # Clean up URL
        url = url.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            return False, url, "Invalid URL format. Please enter a valid URL (e.g., https://example.com)"
        
        # Parse URL
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, url, "URL must include a domain (e.g., example.com)"
        
        return True, url, None
    
    @staticmethod
    def validate_css_selector(selector: str) -> Tuple[bool, Optional[str]]:
        """
        Validate CSS selector syntax
        Returns: (is_valid, error_message)
        """
        if not selector or not selector.strip():
            return False, "Selector cannot be empty"
        
        # Check for common CSS selector issues
        invalid_chars = ['<', '>', '{', '}', '|', '^', '~', '`']
        for char in invalid_chars:
            if char in selector and char not in ['^=', '~=', '|=']:  # Allow in attribute selectors
                return False, f"Invalid character '{char}' in selector"
        
        # Check for balanced brackets
        if selector.count('[') != selector.count(']'):
            return False, "Unbalanced square brackets"
        
        if selector.count('(') != selector.count(')'):
            return False, "Unbalanced parentheses"
        
        # Warn about overly specific selectors
        if selector.count('>') > 5:
            return True, "Warning: Very specific selector may break if page structure changes"
        
        return True, None
    
    @staticmethod
    def suggest_selector_improvements(selector: str) -> List[str]:
        """Suggest improvements for CSS selectors"""
        suggestions = []
        
        # Check for nth-of-type usage
        if ':nth-of-type(' in selector or ':nth-child(' in selector:
            suggestions.append(
                "Consider using classes or IDs instead of position-based selectors for better reliability"
            )
        
        # Check for very long selectors
        if len(selector) > 100:
            suggestions.append(
                "Very long selector detected. Try to simplify by using more specific classes or IDs"
            )
        
        # Check for body/html in selector
        if selector.startswith(('body ', 'html ')):
            suggestions.append(
                "Avoid starting selectors with 'body' or 'html' - use more specific parent elements"
            )
        
        return suggestions