#!/usr/bin/env python3
"""
Main launcher for Interactive Web Scraper
Unified entry point that uses the consolidated CLI
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

try:
    from scraper.unified_cli import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all dependencies are installed:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)