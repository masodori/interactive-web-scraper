# src/scraper/utils/template_migration.py
"""
Template versioning and migration system for updating old templates.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class MigrationInfo:
    """Information about a migration"""
    from_version: str
    to_version: str
    description: str
    breaking_changes: List[str]
    migration_date: str


class Migration(ABC):
    """Abstract base class for template migrations"""
    
    @property
    @abstractmethod
    def from_version(self) -> str:
        """Source version"""
        pass
    
    @property
    @abstractmethod
    def to_version(self) -> str:
        """Target version"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Migration description"""
        pass
    
    @abstractmethod
    def migrate(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform migration on template data
        
        Args:
            template: Template data to migrate
            
        Returns:
            Migrated template data
        """
        pass
    
    def is_applicable(self, template: Dict[str, Any]) -> bool:
        """Check if migration is applicable to template"""
        return template.get('version', '1.0') == self.from_version
    
    def validate(self, template: Dict[str, Any]) -> List[str]:
        """
        Validate template after migration
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check version
        if template.get('version') != self.to_version:
            errors.append(f"Version mismatch: expected {self.to_version}, got {template.get('version')}")
        
        return errors


class MigrationV10ToV20(Migration):
    """Migration from version 1.0 to 2.0"""
    
    @property
    def from_version(self) -> str:
        return "1.0"
    
    @property
    def to_version(self) -> str:
        return "2.0"
    
    @property
    def description(self) -> str:
        return "Add pattern-based extraction support and engine selection"
    
    def migrate(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from 1.0 to 2.0"""
        # Update version
        template['version'] = self.to_version
        
        # Add engine field if not present
        if 'engine' not in template:
            template['engine'] = 'selenium'
        
        # Add pattern extraction to detail rules
        if 'detail_page_rules' in template and template['detail_page_rules']:
            if 'extraction_patterns' not in template['detail_page_rules']:
                template['detail_page_rules']['extraction_patterns'] = {
                    'email': {
                        'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                        'context_keywords': ['email', 'contact']
                    },
                    'phone': {
                        'pattern': r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                        'context_keywords': ['phone', 'tel', 'call']
                    }
                }
        
        # Update load strategy format
        for rule_type in ['list_page_rules', 'detail_page_rules']:
            if rule_type in template and template[rule_type]:
                rules = template[rule_type]
                if 'load_strategy' in rules:
                    strategy = rules['load_strategy']
                    # Remove deprecated fields
                    strategy.pop('max_scrolls', None)
                    strategy.pop('max_clicks', None)
                    # Add new fields
                    if 'consecutive_failure_limit' not in strategy:
                        strategy['consecutive_failure_limit'] = 3
                    if 'extended_wait_multiplier' not in strategy:
                        strategy['extended_wait_multiplier'] = 2.0
        
        return template


class MigrationV20ToV21(Migration):
    """Migration from version 2.0 to 2.1"""
    
    @property
    def from_version(self) -> str:
        return "2.0"
    
    @property
    def to_version(self) -> str:
        return "2.1"
    
    @property
    def description(self) -> str:
        return "Add fallback strategies and rate limiting configuration"
    
    def migrate(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from 2.0 to 2.1"""
        template['version'] = self.to_version
        
        # Add rate limiting configuration
        if 'rate_limiting' not in template:
            template['rate_limiting'] = {
                'enabled': True,
                'preset': 'respectful_bot',
                'custom': None
            }
        
        # Add fallback strategies
        if 'fallback_strategies' not in template:
            template['fallback_strategies'] = {
                'text_based_selection': True,
                'proximity_selection': True,
                'pattern_matching_primary': False
            }
        
        # Add advanced selectors section
        if 'detail_page_rules' in template and template['detail_page_rules']:
            rules = template['detail_page_rules']
            if 'advanced_selectors' not in rules:
                rules['advanced_selectors'] = {
                    'use_text_content': {},
                    'use_proximity': {},
                    'use_ai_detection': False
                }
        
        return template


class TemplateMigrationManager:
    """Manages template migrations and versioning"""
    
    def __init__(self):
        self.logger = logging.getLogger(f'{__name__}.TemplateMigrationManager')
        self.migrations: List[Migration] = []
        self._register_migrations()
    
    def _register_migrations(self):
        """Register all available migrations"""
        self.migrations = [
            MigrationV10ToV20(),
            MigrationV20ToV21(),
        ]
        
        # Sort by version
        self.migrations.sort(key=lambda m: m.from_version)
    
    def get_current_version(self) -> str:
        """Get the latest template version"""
        if self.migrations:
            return self.migrations[-1].to_version
        return "1.0"
    
    def needs_migration(self, template: Dict[str, Any]) -> bool:
        """Check if template needs migration"""
        template_version = template.get('version', '1.0')
        return template_version != self.get_current_version()
    
    def get_migration_path(self, from_version: str, to_version: Optional[str] = None) -> List[Migration]:
        """
        Get list of migrations needed to reach target version
        
        Args:
            from_version: Starting version
            to_version: Target version (latest if None)
            
        Returns:
            List of migrations to apply in order
        """
        if to_version is None:
            to_version = self.get_current_version()
        
        path = []
        current_version = from_version
        
        while current_version != to_version:
            # Find migration from current version
            migration = None
            for m in self.migrations:
                if m.from_version == current_version:
                    migration = m
                    break
            
            if migration is None:
                raise ValueError(f"No migration path from {current_version} to {to_version}")
            
            path.append(migration)
            current_version = migration.to_version
        
        return path
    
    def migrate_template(self, template: Dict[str, Any], 
                        target_version: Optional[str] = None,
                        backup: bool = True) -> Dict[str, Any]:
        """
        Migrate template to target version
        
        Args:
            template: Template data to migrate
            target_version: Target version (latest if None)
            backup: Create backup of original
            
        Returns:
            Migrated template
        """
        current_version = template.get('version', '1.0')
        target_version = target_version or self.get_current_version()
        
        if current_version == target_version:
            self.logger.info(f"Template already at version {target_version}")
            return template
        
        # Get migration path
        migrations = self.get_migration_path(current_version, target_version)
        
        # Create backup if requested
        if backup:
            template['_backup'] = {
                'version': current_version,
                'data': json.loads(json.dumps(template))
            }
        
        # Apply migrations
        migrated = template.copy()
        for migration in migrations:
            self.logger.info(f"Applying migration: {migration.description}")
            migrated = migration.migrate(migrated)
            
            # Validate
            errors = migration.validate(migrated)
            if errors:
                raise ValueError(f"Migration validation failed: {errors}")
        
        # Add migration metadata
        migrated['migration_history'] = migrated.get('migration_history', [])
        migrated['migration_history'].append({
            'from': current_version,
            'to': target_version,
            'date': datetime.now().isoformat(),
            'migrations_applied': len(migrations)
        })
        
        return migrated
    
    def migrate_file(self, template_path: Path, 
                    target_version: Optional[str] = None,
                    create_backup: bool = True) -> bool:
        """
        Migrate template file
        
        Args:
            template_path: Path to template file
            target_version: Target version
            create_backup: Create .backup file
            
        Returns:
            True if migration performed
        """
        try:
            # Load template
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            # Check if migration needed
            if not self.needs_migration(template):
                self.logger.info(f"Template {template_path.name} is up to date")
                return False
            
            # Create backup file
            if create_backup:
                backup_path = template_path.with_suffix('.json.backup')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2)
                self.logger.info(f"Created backup: {backup_path}")
            
            # Migrate
            migrated = self.migrate_template(template, target_version)
            
            # Save migrated template
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(migrated, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Successfully migrated {template_path.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate {template_path}: {e}")
            raise
    
    def migrate_directory(self, directory: Path, 
                         target_version: Optional[str] = None,
                         create_backups: bool = True) -> Dict[str, bool]:
        """
        Migrate all templates in directory
        
        Returns:
            Dict mapping file names to migration success
        """
        results = {}
        
        for template_path in directory.glob("*.json"):
            # Skip backup files
            if template_path.name.endswith('.backup'):
                continue
            
            try:
                migrated = self.migrate_file(
                    template_path, 
                    target_version, 
                    create_backups
                )
                results[template_path.name] = migrated
            except Exception as e:
                self.logger.error(f"Failed to migrate {template_path.name}: {e}")
                results[template_path.name] = False
        
        return results
    
    def check_compatibility(self, template: Dict[str, Any], 
                           features: List[str]) -> Dict[str, bool]:
        """
        Check if template supports specific features
        
        Args:
            template: Template to check
            features: List of feature names
            
        Returns:
            Dict mapping features to support status
        """
        version = template.get('version', '1.0')
        compatibility = {}
        
        feature_versions = {
            'pattern_extraction': '2.0',
            'engine_selection': '2.0',
            'rate_limiting': '2.1',
            'fallback_strategies': '2.1',
            'ai_detection': '2.1'
        }
        
        for feature in features:
            if feature in feature_versions:
                required_version = feature_versions[feature]
                compatibility[feature] = version >= required_version
            else:
                compatibility[feature] = False
        
        return compatibility


def create_migration_script():
    """Create a standalone migration script"""
    script = '''#!/usr/bin/env python
"""
Migrate scraper templates to the latest version
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.scraper.utils.template_migration import TemplateMigrationManager
from src.scraper.config import Config

def main():
    manager = TemplateMigrationManager()
    
    print(f"Template Migration Tool")
    print(f"Current version: {manager.get_current_version()}")
    print("-" * 50)
    
    # Migrate all templates
    results = manager.migrate_directory(Config.TEMPLATES_DIR)
    
    # Display results
    migrated = sum(1 for v in results.values() if v)
    print(f"\\nMigration complete:")
    print(f"  Migrated: {migrated}")
    print(f"  Already up-to-date: {len(results) - migrated}")
    
    if migrated > 0:
        print(f"\\nBackup files created with .backup extension")

if __name__ == "__main__":
    main()
'''
    
    return script