#!/usr/bin/env python3
"""
setup.py for cli-anything-rekordbox

Install: pip install -e .
Publish: python -m build && twine upload dist/*
Modified 2026-10-22: library-only base install; optional MIDI dependencies.
Modified 2026-10-23: standalone root packaging and rekordbox command alias.
"""
from setuptools import setup, find_namespace_packages
from pathlib import Path

ROOT = Path(__file__).resolve().parent
long_description = (ROOT / "README.md").read_text(encoding="utf-8")

setup(
    name="cli-anything-rekordbox",
    version="0.2.0",
    author="cli-anything contributors",
    author_email="",
    description="Standalone RekordboxCLI: library metadata management and optional MIDI control for rekordbox 6/7.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Jaek-Kein/CLI-Anything/tree/RecordboxCLI",
    project_urls={"Upstream": "https://github.com/HKUDS/CLI-Anything"},
    packages=find_namespace_packages(include=["cli_anything.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Sound/Audio :: MIDI",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    license_files=["LICENSE", "NOTICE"],
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "pyrekordbox>=0.5.0,<0.6",
    ],
    extras_require={
        "midi": ["mido>=1.3.0", "python-rtmidi>=1.5.0"],
        "windows": ["pyautogui>=0.9.54", "pygetwindow>=0.0.9", "pywin32>=306"],
        "dev": ["pytest>=7.0.0", "pytest-cov>=4.0.0"],
    },
    entry_points={
        "console_scripts": [
            "rekordbox=cli_anything.rekordbox.rekordbox_cli:main",
            "cli-anything-rekordbox=cli_anything.rekordbox.rekordbox_cli:main",
        ],
    },
    package_data={
        "cli_anything.rekordbox": ["README.md", "skills/*.md", "data/*.csv"],
    },
    include_package_data=True,
    zip_safe=False,
)
