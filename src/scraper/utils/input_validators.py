# src/scraper/utils/input_validators.py
"""
Input validation and error handling utilities for user prompts.
"""

import re
import logging
from typing import Optional, Tuple, List, Dict, Any, Union
from urllib.parse import urlparse
from pathlib import Path


class InputValidator:
    """Centralized input validation for user prompts"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """
        Comprehensive URL validation.
        
        Args:
            url: URL string to validate
            
        Returns:
            Tuple of (is_valid, result_or_error_message)
        """
        if not url or not isinstance(url, str):
            return False, "URL must be a non-empty string"
        
        url = url.strip()
        
        # Common URL mistakes
        common_mistakes = {
            'www.': 'https://www.',
            'http//': 'http://',
            'https//': 'https://',
            'htp://': 'http://',
            'htps://': 'https://',
        }
        
        for mistake, correction in common_mistakes.items():
            if url.startswith(mistake) and not url.startswith(('http://', 'https://')):
                url = url.replace(mistake, correction, 1)
        
        # Add protocol if missing
        if not re.match(r'^[a-zA-Z][a-zA-Z\d+\-.]*:', url):
            url = 'https://' + url
        
        # Validate URL structure
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https', 'file']:
                return False, f"Unsupported URL scheme: {parsed.scheme}"
            
            # Check netloc for web URLs
            if parsed.scheme in ['http', 'https']:
                if not parsed.netloc:
                    return False, "URL must include a domain name"
                
                # Check for valid domain
                domain_parts = parsed.netloc.split('.')
                if len(domain_parts) < 2:
                    return False, "Invalid domain name (missing TLD)"
                
                # Check for spaces or invalid characters
                if ' ' in parsed.netloc or '\t' in parsed.netloc:
                    return False, "Domain name contains invalid characters (spaces)"
                
                # Basic domain validation
                domain_pattern = re.compile(
                    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*'
                    r'[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
                )
                
                if not domain_pattern.match(parsed.netloc.split(':')[0]):
                    return False, "Invalid domain name format"
            
            return True, url
            
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"
    
    @staticmethod
    def validate_selector(selector: str, selector_type: str = 'css') -> Tuple[bool, str]:
        """
        Validate CSS selector or XPath.
        
        Args:
            selector: Selector string
            selector_type: 'css' or 'xpath'
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not selector or not isinstance(selector, str):
            return False, "Selector must be a non-empty string"
        
        selector = selector.strip()
        
        if selector_type == 'css':
            # Basic CSS selector validation
            invalid_chars = ['<', '>', '{', '}', '|', '\\']
            for char in invalid_chars:
                if char in selector:
                    return False, f"Invalid character in CSS selector: {char}"
            
            # Check for balanced brackets
            if selector.count('[') != selector.count(']'):
                return False, "Unbalanced square brackets in selector"
            
            if selector.count('(') != selector.count(')'):
                return False, "Unbalanced parentheses in selector"
                
        elif selector_type == 'xpath':
            # Basic XPath validation
            if not selector.startswith(('//', '/', './', '../')):
                return False, "XPath must start with //, /, ./, or ../"
            
            # Check for balanced brackets and quotes
            if selector.count('[') != selector.count(']'):
                return False, "Unbalanced square brackets in XPath"
            
            # Check quotes
            single_quotes = selector.count("'")
            double_quotes = selector.count('"')
            
            if single_quotes % 2 != 0:
                return False, "Unbalanced single quotes in XPath"
            
            if double_quotes % 2 != 0:
                return False, "Unbalanced double quotes in XPath"
        
        else:
            return False, f"Unknown selector type: {selector_type}"
        
        return True, ""
    
    @staticmethod
    def validate_field_name(name: str, existing_fields: List[str] = None) -> Tuple[bool, str]:
        """
        Validate field name for template.
        
        Args:
            name: Field name to validate
            existing_fields: List of existing field names
            
        Returns:
            Tuple of (is_valid, sanitized_name_or_error)
        """
        if not name or not isinstance(name, str):
            return False, "Field name must be a non-empty string"
        
        # Remove leading/trailing whitespace
        name = name.strip()
        
        if not name:
            return False, "Field name cannot be empty"
        
        # Check length
        if len(name) > 50:
            return False, "Field name too long (max 50 characters)"
        
        # Sanitize name (replace spaces and special chars with underscore)
        sanitized = re.sub(r'[^\w\s-]', '_', name)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        sanitized = sanitized.strip('_')
        
        # Ensure it starts with a letter or underscore
        if sanitized and not re.match(r'^[a-zA-Z_]', sanitized):
            sanitized = 'field_' + sanitized
        
        if not sanitized:
            return False, "Field name contains no valid characters"
        
        # Check against reserved words
        reserved_words = [
            'id', 'class', 'type', 'name', 'value', 'data',
            'url', 'timestamp', 'errors', 'detail_url', 'detail_data'
        ]
        
        if sanitized.lower() in reserved_words:
            sanitized = sanitized + '_field'
        
        # Check for duplicates
        if existing_fields and sanitized in existing_fields:
            # Try to make it unique
            counter = 1
            base_name = sanitized
            while sanitized in existing_fields:
                sanitized = f"{base_name}_{counter}"
                counter += 1
                if counter > 100:  # Prevent infinite loop
                    return False, "Cannot create unique field name"
        
        return True, sanitized
    
    @staticmethod
    def validate_template_name(name: str) -> Tuple[bool, str]:
        """
        Validate template name.
        
        Args:
            name: Template name to validate
            
        Returns:
            Tuple of (is_valid, sanitized_name_or_error)
        """
        if not name or not isinstance(name, str):
            return False, "Template name must be a non-empty string"
        
        name = name.strip()
        
        if not name:
            return False, "Template name cannot be empty"
        
        # Check length
        if len(name) > 100:
            return False, "Template name too long (max 100 characters)"
        
        # Sanitize name (allow only alphanumeric, underscore, and hyphen)
        sanitized = re.sub(r'[^\w\s-]', '', name)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        sanitized = sanitized.strip('_').lower()
        
        if not sanitized:
            return False, "Template name contains no valid characters"
        
        # Ensure it starts with a letter or underscore
        if not re.match(r'^[a-zA-Z_]', sanitized):
            sanitized = 'template_' + sanitized
        
        return True, sanitized
    
    @staticmethod
    def validate_file_path(path: str, must_exist: bool = False, 
                          extensions: List[str] = None) -> Tuple[bool, Union[Path, str]]:
        """
        Validate file path.
        
        Args:
            path: File path to validate
            must_exist: Whether file must exist
            extensions: Allowed file extensions
            
        Returns:
            Tuple of (is_valid, Path_or_error_message)
        """
        if not path or not isinstance(path, str):
            return False, "Path must be a non-empty string"
        
        try:
            file_path = Path(path).resolve()
            
            if must_exist and not file_path.exists():
                return False, f"File does not exist: {file_path}"
            
            if must_exist and not file_path.is_file():
                return False, f"Path is not a file: {file_path}"
            
            if extensions:
                if not any(file_path.suffix.lower() == ext.lower() for ext in extensions):
                    return False, f"Invalid file extension. Expected one of: {', '.join(extensions)}"
            
            # Check if directory is writable (for new files)
            if not must_exist:
                parent_dir = file_path.parent
                if not parent_dir.exists():
                    return False, f"Parent directory does not exist: {parent_dir}"
                
                if not os.access(parent_dir, os.W_OK):
                    return False, f"No write permission for directory: {parent_dir}"
            
            return True, file_path
            
        except Exception as e:
            return False, f"Invalid path: {str(e)}"
    
    @staticmethod
    def validate_integer(value: str, min_val: int = None, 
                        max_val: int = None) -> Tuple[bool, Union[int, str]]:
        """
        Validate integer input.
        
        Args:
            value: String value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Tuple of (is_valid, int_value_or_error)
        """
        if not value or not isinstance(value, str):
            return False, "Value must be a non-empty string"
        
        value = value.strip()
        
        try:
            int_value = int(value)
            
            if min_val is not None and int_value < min_val:
                return False, f"Value must be at least {min_val}"
            
            if max_val is not None and int_value > max_val:
                return False, f"Value must be at most {max_val}"
            
            return True, int_value
            
        except ValueError:
            return False, "Invalid integer value"
    
    @staticmethod
    def validate_choice(value: str, choices: List[str], 
                       case_sensitive: bool = False) -> Tuple[bool, str]:
        """
        Validate choice from list of options.
        
        Args:
            value: User input value
            choices: List of valid choices
            case_sensitive: Whether comparison is case sensitive
            
        Returns:
            Tuple of (is_valid, matched_choice_or_error)
        """
        if not value or not isinstance(value, str):
            return False, "Choice must be a non-empty string"
        
        if not choices:
            return False, "No valid choices provided"
        
        value = value.strip()
        
        if not case_sensitive:
            value_lower = value.lower()
            for choice in choices:
                if choice.lower() == value_lower:
                    return True, choice
        else:
            if value in choices:
                return True, value
        
        # Try to match by number (1-based index)
        try:
            index = int(value) - 1
            if 0 <= index < len(choices):
                return True, choices[index]
        except ValueError:
            pass
        
        # Try partial match
        matches = []
        value_lower = value.lower()
        for choice in choices:
            if value_lower in choice.lower():
                matches.append(choice)
        
        if len(matches) == 1:
            return True, matches[0]
        elif len(matches) > 1:
            return False, f"Ambiguous choice. Matches: {', '.join(matches)}"
        
        return False, f"Invalid choice. Options: {', '.join(choices)}"


class ErrorHandler:
    """Centralized error handling for user interactions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_count = 0
        self.max_consecutive_errors = 5
    
    def handle_input_error(self, error: Exception, context: str = "") -> bool:
        """
        Handle input-related errors.
        
        Args:
            error: The exception that occurred
            context: Context information about where error occurred
            
        Returns:
            True if should retry, False if should abort
        """
        self.error_count += 1
        
        if isinstance(error, KeyboardInterrupt):
            print("\n\n⚠️  Operation cancelled by user.")
            return False
        
        elif isinstance(error, EOFError):
            print("\n❌ Input stream ended unexpectedly.")
            return False
        
        elif isinstance(error, ValueError):
            print(f"❌ Invalid input: {error}")
            if self.error_count < self.max_consecutive_errors:
                print("Please try again.")
                return True
            
        else:
            self.logger.error(f"Unexpected error in {context}: {error}")
            print(f"❌ An unexpected error occurred: {error}")
            
            if self.error_count < self.max_consecutive_errors:
                print("Please try again.")
                return True
        
        print(f"❌ Too many errors ({self.error_count}). Aborting operation.")
        return False
    
    def reset_error_count(self):
        """Reset the error counter after successful operation"""
        self.error_count = 0
    
    def wrap_input_operation(self, operation: callable, 
                           context: str = "input operation",
                           max_attempts: int = 3) -> Optional[Any]:
        """
        Wrap an input operation with error handling.
        
        Args:
            operation: Function to execute
            context: Context for error messages
            max_attempts: Maximum retry attempts
            
        Returns:
            Result of operation or None if failed
        """
        attempts = 0
        self.reset_error_count()
        
        while attempts < max_attempts:
            try:
                result = operation()
                self.reset_error_count()
                return result
                
            except Exception as e:
                attempts += 1
                if not self.handle_input_error(e, context):
                    return None
                
                if attempts >= max_attempts:
                    print(f"❌ Maximum attempts ({max_attempts}) exceeded for {context}.")
                    return None
        
        return None


class PromptFormatter:
    """Format prompts for better user experience"""
    
    @staticmethod
    def format_prompt(prompt: str, options: Dict[str, str] = None,
                     default: str = None, hint: str = None) -> str:
        """
        Format a user prompt with options and hints.
        
        Args:
            prompt: Main prompt text
            options: Dictionary of options (key -> description)
            default: Default value
            hint: Additional hint text
            
        Returns:
            Formatted prompt string
        """
        formatted = f"\n{prompt}"
        
        if options:
            formatted += "\n"
            for key, desc in options.items():
                formatted += f"  {key}) {desc}\n"
        
        if hint:
            formatted += f"\n💡 Hint: {hint}"
        
        if default:
            formatted += f"\n[Default: {default}]"
        
        formatted += "\n> "
        return formatted
    
    @staticmethod
    def format_error(error: str, suggestions: List[str] = None) -> str:
        """
        Format error message with suggestions.
        
        Args:
            error: Error message
            suggestions: List of suggestions
            
        Returns:
            Formatted error string
        """
        formatted = f"❌ {error}"
        
        if suggestions:
            formatted += "\n\n💡 Suggestions:"
            for suggestion in suggestions:
                formatted += f"\n  • {suggestion}"
        
        return formatted
    
    @staticmethod
    def format_success(message: str, details: Dict[str, Any] = None) -> str:
        """
        Format success message with details.
        
        Args:
            message: Success message
            details: Additional details
            
        Returns:
            Formatted success string
        """
        formatted = f"✅ {message}"
        
        if details:
            for key, value in details.items():
                formatted += f"\n  {key}: {value}"
        
        return formatted
    
    @staticmethod
    def format_warning(message: str, action: str = None) -> str:
        """
        Format warning message.
        
        Args:
            message: Warning message
            action: Suggested action
            
        Returns:
            Formatted warning string
        """
        formatted = f"⚠️  {message}"
        
        if action:
            formatted += f"\n   → {action}"
        
        return formatted


# Example usage functions
def get_validated_url(prompt: str = "Enter URL: ", 
                     default: str = None,
                     max_attempts: int = 3) -> Optional[str]:
    """
    Get and validate URL from user with error handling.
    
    Args:
        prompt: Prompt message
        default: Default URL
        max_attempts: Maximum attempts
        
    Returns:
        Valid URL or None
    """
    validator = InputValidator()
    formatter = PromptFormatter()
    error_handler = ErrorHandler()
    
    def get_url():
        formatted_prompt = formatter.format_prompt(
            prompt,
            hint="Enter a complete URL (e.g., https://example.com)",
            default=default
        )
        
        response = input(formatted_prompt).strip()
        
        if not response and default:
            response = default
        
        is_valid, result = validator.validate_url(response)
        
        if is_valid:
            return result
        else:
            print(formatter.format_error(
                result,
                suggestions=[
                    "Include the protocol (http:// or https://)",
                    "Check for typos in the domain name",
                    "Ensure there are no spaces in the URL"
                ]
            ))
            raise ValueError(result)
    
    return error_handler.wrap_input_operation(
        get_url,
        context="URL input",
        max_attempts=max_attempts
    )


def get_validated_field_name(prompt: str = "Enter field name: ",
                           existing_fields: List[str] = None,
                           max_attempts: int = 3) -> Optional[str]:
    """
    Get and validate field name from user.
    
    Args:
        prompt: Prompt message
        existing_fields: List of existing field names
        max_attempts: Maximum attempts
        
    Returns:
        Valid field name or None
    """
    validator = InputValidator()
    formatter = PromptFormatter()
    error_handler = ErrorHandler()
    
    def get_field():
        formatted_prompt = formatter.format_prompt(
            prompt,
            hint="Use descriptive names (e.g., 'product_name', 'price')"
        )
        
        response = input(formatted_prompt).strip()
        
        if not response:
            raise ValueError("Field name cannot be empty")
        
        is_valid, result = validator.validate_field_name(response, existing_fields)
        
        if is_valid:
            if result != response:
                print(f"ℹ️  Field name sanitized to: {result}")
            return result
        else:
            print(formatter.format_error(result))
            raise ValueError(result)
    
    return error_handler.wrap_input_operation(
        get_field,
        context="field name input",
        max_attempts=max_attempts
    )


def get_validated_choice(prompt: str,
                        choices: Dict[str, str],
                        default: str = None,
                        max_attempts: int = 3) -> Optional[str]:
    """
    Get validated choice from user.
    
    Args:
        prompt: Prompt message
        choices: Dictionary of choices (key -> description)
        default: Default choice
        max_attempts: Maximum attempts
        
    Returns:
        Selected choice key or None
    """
    validator = InputValidator()
    formatter = PromptFormatter()
    error_handler = ErrorHandler()
    
    choice_keys = list(choices.keys())
    
    def get_choice():
        formatted_prompt = formatter.format_prompt(
            prompt,
            options=choices,
            default=default
        )
        
        response = input(formatted_prompt).strip()
        
        if not response and default:
            response = default
        
        is_valid, result = validator.validate_choice(response, choice_keys)
        
        if is_valid:
            return result
        else:
            print(formatter.format_error(result))
            raise ValueError(result)
    
    return error_handler.wrap_input_operation(
        get_choice,
        context="choice selection",
        max_attempts=max_attempts
    )