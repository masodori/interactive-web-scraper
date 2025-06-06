# src/scraper/config/settings.py
"""
Central configuration management for the interactive scraper.
"""

from pathlib import Path
from typing import List, Dict, Any


class Config:
    """Central configuration management"""
    
    # Directory Configuration
    BASE_DIR = Path(__file__).parent.parent.parent.parent
    CONFIG_DIR = BASE_DIR / 'config'
    TEMPLATES_DIR = BASE_DIR / 'templates'
    OUTPUT_DIR = BASE_DIR / 'output'
    LOGS_DIR = BASE_DIR / 'logs'
    ASSETS_DIR = BASE_DIR / 'assets'
    
    # Selenium Configuration
    DEFAULT_TIMEOUT = 10
    IMPLICIT_WAIT = 5
    PAGE_LOAD_TIMEOUT = 30
    
    # Retry Configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    RETRY_BACKOFF = 1.5  # Exponential backoff multiplier
    
    # Batch Processing
    BATCH_SIZE = 250  # Process items in chunks
    LARGE_DATASET_THRESHOLD = 100  # When to enable batch mode
    PROGRESS_LOG_INTERVAL = 100  # Log progress every N items
    INTERMEDIATE_SAVE_INTERVAL = 500  # Save results every N items
    
    # Load More Detection
    LOAD_MORE_MAX_RETRIES = 5  # Retry clicking if no new items
    LOAD_MORE_STABILITY_CHECK = 3  # Check N times for stable item count
    LOAD_MORE_PAUSE_TIME = 2.0  # Default pause between actions
    
    # Cookie Handling
    COOKIE_ACCEPTANCE_TIMEOUT = 5
    COOKIE_XPATHS = [
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'got it')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'yes')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
        "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
    ]
    
    COOKIE_CSS_SELECTORS = [
        "button.accept-cookies", "button.cookie-accept",
        "button#accept-cookies", "button#cookie-accept",
        "button[data-cookie-accept]", "button[data-accept-cookies]",
        ".cookie-banner button.primary", ".cookie-notice button.agree"
    ]
    
    # Load More Keywords
    LOAD_MORE_KEYWORDS = [
        'load more', 'show more', 'see more', 'view more', 
        'more results', 'next', 'show all', 'view all', 
        'load all', 'show additional', 'more', 'expand', 
        'show next', 'load next', 'more people', 'view additional',
        'show more results', '+', '→', 'next page', 'older posts'
    ]
    
    # Browser Configuration
    CHROME_OPTIONS = {
        'default': [
            '--log-level=3',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ],
        'headless': [
            '--headless=new',
            '--window-size=1920,1080',
            '--start-maximized',
            '--disable-extensions',
            '--disable-plugins'
        ],
        'experimental': {
            'excludeSwitches': ['enable-automation'],
            'useAutomationExtension': False,
            'prefs': {
                'credentials_enable_service': False,
                'profile.password_manager_enabled': False
            }
        }
    }
    
    # Export Configuration
    EXPORT_FORMATS = {
        'json': {
            'extension': '.json',
            'mime_type': 'application/json',
            'encoding': 'utf-8'
        },
        'csv': {
            'extension': '.csv',
            'mime_type': 'text/csv',
            'encoding': 'utf-8-sig'  # BOM for Excel compatibility
        },
        'excel': {
            'extension': '.xlsx',
            'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'engine': 'openpyxl'
        },
        'html': {
            'extension': '.html',
            'mime_type': 'text/html',
            'encoding': 'utf-8'
        }
    }
    
    # Logging Configuration
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            },
            'simple': {
                'format': '%(levelname)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': 'scraper.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'loggers': {
            'scraper': {
                'level': 'DEBUG',
                'handlers': ['console', 'file'],
                'propagate': False
            }
        }
    }
    
    # Field Mappings for Common Sites
    DEFAULT_FIELD_MAPPINGS = {
        "gibson_dunn": {
            "Name": "name",
            "Position": "position",
            "Office": "office",
            "EmailAddress": "email",
            "PhoneNumber": "phone",
            "Education1": "education_1",
            "Education2": "education_2",
            "Creds": "bar_admissions",
            "practice_areas": "practice_areas",
            "bio": "bio"
        }
    }
    
    # JavaScript Assets
    INTERACTIVE_JS_FILENAME = 'interactive_selector.js'
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        for dir_path in [cls.CONFIG_DIR, cls.TEMPLATES_DIR, 
                        cls.OUTPUT_DIR, cls.LOGS_DIR, cls.ASSETS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_field_mapping(cls, template_name: str) -> Dict[str, str]:
        """Get field mapping for a specific template"""
        return cls.DEFAULT_FIELD_MAPPINGS.get(template_name, {})
    
    @classmethod
    def get_chrome_options(cls, headless: bool = False) -> List[str]:
        """Get Chrome options based on mode"""
        options = cls.CHROME_OPTIONS['default'].copy()
        if headless:
            options.extend(cls.CHROME_OPTIONS['headless'])
        return options
    
    @classmethod
    def get_js_asset_path(cls) -> Path:
        """Get path to JavaScript assets"""
        return cls.ASSETS_DIR / 'js' / cls.INTERACTIVE_JS_FILENAME