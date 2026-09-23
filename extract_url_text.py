#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "requests",
#   "beautifulsoup4",
#   "lxml",
#   "readability-lxml",
#   "markdownify",
#   "playwright",
#   "ddgs",
#   "pypdf",
# ]
# ///
"""
Fetch a URL and print its title + plain article text to stdout, for
tts-clipboard.py to speak. Reuses the better-research skill's fetch/extract
pipeline (requests-first, Playwright-fallback, readability + guarded region
extraction) instead of a second, weaker scraper.

Usage: uv run extract_url_text.py "<url>"
"""
import sys
import os

sys.path.insert(0, os.path.join(
    os.path.expanduser("~"), ".claude", "skills", "better-research", "scripts"
))

from bs4 import BeautifulSoup
from research_lib import fetch_page


def main():
    if len(sys.argv) != 2:
        print("usage: extract_url_text.py <url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    result = fetch_page(url)

    if result["method"] == "blocked" or result["text_len"] == 0:
        print(f"ERROR: could not extract content from {url}", file=sys.stderr)
        sys.exit(1)

    text = BeautifulSoup(result["html"], "lxml").get_text(" ", strip=True)
    title = result["title"] or url

    print(title)
    print()
    print(text)


if __name__ == "__main__":
    main()
