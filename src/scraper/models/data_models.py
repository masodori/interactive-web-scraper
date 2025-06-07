# src/scraper/models/data_models.py
"""
Data models and structures for the interactive scraper.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path


class ExportFormat(Enum):
    """Supported export formats"""

    JSON = "json"
    CSV = "csv"
    EXCEL = "xlsx"
    HTML = "html"

    @classmethod
    def from_string(cls, value: str) -> "ExportFormat":
        """Create enum from string value"""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Unsupported export format: {value}")


class ScrapingType(Enum):
    """Types of scraping operations"""

    SINGLE_PAGE = "single_page"
    LIST_ONLY = "list_only"
    LIST_DETAIL = "list_detail"


class LoadStrategy(Enum):
    """Content loading strategies"""

    AUTO = "auto"
    SCROLL = "scroll"
    BUTTON = "button"
    PAGINATION = "pagination"
    NONE = "none"


@dataclass
class ScrapedField:
    """Represents a single scraped field"""

    name: str
    selector: str
    value: Optional[Any] = None
    extraction_method: str = "text"  # text, attribute, table, list, etc.
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScrapedItem:
    """Represents a single scraped item with metadata"""

    url: str
    timestamp: str
    data: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    detail_url: Optional[str] = None
    detail_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def is_successful(self) -> bool:
        """Check if item was scraped successfully"""
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScrapeResult:
    """Container for scraping results with metadata"""

    template_name: str
    start_time: str
    end_time: str
    total_items: int
    successful_items: int
    failed_items: int
    items: List[ScrapedItem]
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Calculate success/failure counts if not provided
        if self.successful_items == 0 and self.failed_items == 0:
            self.successful_items = sum(
                1 for item in self.items if item.is_successful()
            )
            self.failed_items = len(self.items) - self.successful_items

    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.successful_items / self.total_items) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "metadata": {
                "template_name": self.template_name,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "total_items": self.total_items,
                "successful_items": self.successful_items,
                "failed_items": self.failed_items,
                "success_rate": self.success_rate(),
                "errors": self.errors,
                **self.metadata,
            },
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class BatchProgress:
    """Track batch processing progress"""

    total_expected: int = 0
    total_processed: int = 0
    current_batch: int = 0
    items_in_batch: int = 0
    last_saved_at: int = 0
    batch_size: int = 250

    def should_save(self) -> bool:
        """Check if we should save current batch"""
        return self.items_in_batch >= self.batch_size

    def update(self, items_processed: int = 1):
        """Update progress counters"""
        self.total_processed += items_processed
        self.items_in_batch += items_processed

    def reset_batch(self):
        """Reset batch counters after saving"""
        self.current_batch += 1
        self.items_in_batch = 0
        self.last_saved_at = self.total_processed

    def get_progress_percentage(self) -> float:
        """Get progress percentage"""
        if self.total_expected == 0:
            return 0.0
        return (self.total_processed / self.total_expected) * 100


@dataclass
class LoadStrategyConfig:
    """Configuration for content loading strategy"""

    type: LoadStrategy = LoadStrategy.AUTO
    # DEPRECATED: max_scrolls: int = 10
    # DEPRECATED: max_clicks: int = 10
    pause_time: float = 2.0
    button_selector: Optional[str] = None
    pagination_next_selector: Optional[str] = None
    wait_for_element: Optional[str] = None

    # New fields for smart detection
    consecutive_failure_limit: int = 3  # Stop after N clicks with no new items
    extended_wait_multiplier: float = (
        2.0  # Wait N times longer if button exists but no items loaded
    )

    @classmethod
    def from_dict(cls, data: dict) -> "LoadStrategyConfig":
        """Create from dictionary, ignoring deprecated fields"""
        # Remove deprecated fields to avoid errors
        data.pop("max_scrolls", None)
        data.pop("max_clicks", None)

        if "type" in data and isinstance(data["type"], str):
            data["type"] = LoadStrategy(data["type"])
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        result = asdict(self)
        result["type"] = self.type.value
        return result


@dataclass
class TemplateRules:
    """Rules for template-based scraping"""

    fields: Dict[str, str] = field(default_factory=dict)
    repeating_item_selector: Optional[str] = None
    profile_link_selector: Optional[str] = None
    load_strategy: LoadStrategyConfig = field(default_factory=LoadStrategyConfig)

    def to_dict(self) -> dict:
        return {
            "fields": self.fields,
            "repeating_item_selector": self.repeating_item_selector,
            "profile_link_selector": self.profile_link_selector,
            "load_strategy": self.load_strategy.to_dict(),
        }


@dataclass
class SiteInfo:
    """Website-specific information"""

    url: str
    cookie_xpath: Optional[str] = None
    cookie_css: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    wait_time: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScrapingTemplate:
    """Complete scraping template"""

    # Non-default fields must come first for dataclasses
    name: str
    site_info: SiteInfo
    scraping_type: ScrapingType
    engine: str = "selenium"
    list_page_rules: Optional[TemplateRules] = None
    detail_page_rules: Optional[TemplateRules] = None
    field_mappings: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    # New v2.1 fields
    rate_limiting: Optional[Dict[str, Any]] = None
    extraction_patterns: Optional[Dict[str, Any]] = None
    fallback_strategies: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            "name": self.name,
            "engine": self.engine,
            "version": self.version,
            "created_at": self.created_at,
            "site_info": self.site_info.to_dict(),
            "scraping_type": self.scraping_type.value,
            "list_page_rules": (
                self.list_page_rules.to_dict() if self.list_page_rules else {}
            ),
            "detail_page_rules": (
                self.detail_page_rules.to_dict() if self.detail_page_rules else {}
            ),
            "field_mappings": self.field_mappings,
        }
        
        # Add v2.1 fields if they exist
        if self.rate_limiting is not None:
            result["rate_limiting"] = self.rate_limiting
        if self.extraction_patterns is not None:
            result["extraction_patterns"] = self.extraction_patterns
        if self.fallback_strategies is not None:
            result["fallback_strategies"] = self.fallback_strategies
            
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapingTemplate":
        """Create template from dictionary"""
        site_info = SiteInfo(**data.get("site_info", {}))
        scraping_type = ScrapingType(data.get("scraping_type", "single_page"))

        list_rules = None
        if data.get("list_page_rules"):
            rules_data = data["list_page_rules"].copy()
            # Filter out fields that TemplateRules doesn't support
            filtered_data = {
                k: v for k, v in rules_data.items() 
                if k in ['fields', 'repeating_item_selector', 'profile_link_selector', 'load_strategy']
            }
            if "load_strategy" in filtered_data:
                filtered_data["load_strategy"] = LoadStrategyConfig.from_dict(
                    filtered_data["load_strategy"]
                )
            list_rules = TemplateRules(**filtered_data)

        detail_rules = None
        if data.get("detail_page_rules"):
            rules_data = data["detail_page_rules"].copy()
            # Filter out fields that TemplateRules doesn't support
            filtered_data = {
                k: v for k, v in rules_data.items() 
                if k in ['fields', 'repeating_item_selector', 'profile_link_selector', 'load_strategy']
            }
            if "load_strategy" in filtered_data:
                filtered_data["load_strategy"] = LoadStrategyConfig.from_dict(
                    filtered_data["load_strategy"]
                )
            detail_rules = TemplateRules(**filtered_data)

        return cls(
            name=data.get("name", "unnamed"),
            engine=data.get("engine", "selenium"),
            site_info=site_info,
            scraping_type=scraping_type,
            list_page_rules=list_rules,
            detail_page_rules=detail_rules,
            field_mappings=data.get("field_mappings", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            version=data.get("version", "1.0"),
            # v2.1 fields
            rate_limiting=data.get("rate_limiting"),
            extraction_patterns=data.get("extraction_patterns"),
            fallback_strategies=data.get("fallback_strategies"),
        )

    def save(self, filepath: Union[str, Path]):
        """Save template to JSON file"""
        import json

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "ScrapingTemplate":
        """Load template from JSON file"""
        import json

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
