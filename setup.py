# setup.py
"""
Setup script for the Interactive Web Scraper package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = (this_directory / "requirements.txt").read_text().splitlines()
requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="interactive-web-scraper",
    version="2.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A modular, extensible web scraper with interactive template creation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/interactive-web-scraper",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/interactive-web-scraper/issues",
        "Documentation": "https://github.com/yourusername/interactive-web-scraper/wiki",
        "Source Code": "https://github.com/yourusername/interactive-web-scraper",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "sphinx-autodoc-typehints>=1.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "scraper=scraper.unified_cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "scraper": [
            "assets/js/*.js",
            "templates/examples/*.json",
        ],
    },
    zip_safe=False,
)