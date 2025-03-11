import functools
import os
import re
import sys
import urllib.parse
import urllib.request
from enum import Enum, auto
from urllib.parse import urljoin

import click
import dotenv
import requests
from bs4 import BeautifulSoup
from loguru import logger

dotenv.load_dotenv()


class LinkType(Enum):
    """Enum for different types of links."""

    DIRECTORY = auto()
    FILE = auto()
    PARENT = auto()
    WEBSITE = auto()
    UNKNOWN = auto()


@functools.lru_cache(maxsize=128)
def headers(bearer_token=None):
    bearer_token = bearer_token or os.getenv("FTP_LIST_BEARER_TOKEN")
    if not bearer_token:
        raise ValueError("Bearer token")
    return {"Authorization": f"Bearer {bearer_token}"}


def get_page_content(url):
    """Fetch the content of a URL."""
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        return None
    if parsed.scheme not in ("http", "https"):
        logger.error(f"Unsupported scheme: {parsed.scheme}")
        return None
    try:
        response = requests.get(url, timeout=5 * 60, headers=headers())
    except urllib.error.URLError as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return None
    return response.text


def determine_link_type(link_text, url):
    """Determine the type of a link."""
    parsed = urllib.parse.urlparse(url)

    # Check for parent directory
    if "parent directory" in link_text.lower() or url in ("../", "..", "/"):
        return LinkType.PARENT

    # Check for directory
    if parsed.path.endswith("/"):
        return LinkType.DIRECTORY

    # Check for external website
    if parsed.netloc and not parsed.path:
        return LinkType.WEBSITE

    # Check for file
    filename = os.path.basename(parsed.path)
    if filename and "." in filename:
        return LinkType.FILE

    # Default case
    return LinkType.UNKNOWN


def clean_url(url):
    parsed = urllib.parse.urlparse(url)
    url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return url.replace("http://", "https://")


def should_ignore(url, ignore_patterns):
    """Check if URL matches any of the ignore patterns."""
    if not ignore_patterns:
        return False

    return any(re.search(pattern, url) for pattern in ignore_patterns)


def extract_links(html_content, base_url, ignore_patterns=None):
    """Extract all links from HTML content."""
    if not html_content:
        return [], []

    soup = BeautifulSoup(html_content, "html.parser")
    file_links = []
    dir_links = []

    for anchor in soup.find_all("a"):
        if not anchor.has_attr("href"):
            continue

        link_url = anchor["href"]
        link_text = anchor.text.strip()

        # Skip links that are not relative or point to the same domain
        if link_url.startswith("http") and base_url not in link_url:
            continue

        full_url = urljoin(base_url, link_url)

        # Skip ignored URLs
        if should_ignore(full_url, ignore_patterns):
            logger.debug(f"Ignoring: {full_url}")
            continue

        link_type = determine_link_type(link_text, link_url)

        if link_type == LinkType.DIRECTORY:
            dir_links.append(clean_url(full_url))
        elif link_type == LinkType.FILE:
            file_links.append(full_url)

    return sorted(set(file_links)), sorted(set(dir_links))


def crawl_directory(url, visited=None, ignore_patterns=None):
    """Recursively crawl directory listings, yielding URLs as they are found."""
    if visited is None:
        visited = set()

    if url in visited or should_ignore(url, ignore_patterns):
        return

    visited.add(url)
    logger.info(f"Crawling: {url}")

    html_content = get_page_content(url)
    file_links, dir_links = extract_links(html_content, url, ignore_patterns)

    # Yield file URLs as we find them
    for file_url in file_links:
        logger.debug(f"Found file: {file_url}")
        yield file_url

    # Recursively process directories
    for dir_link in dir_links:
        yield from crawl_directory(dir_link, visited, ignore_patterns)


@click.command()
@click.argument("url")
@click.option("-o", "--output", help="Output file to save URLs; if not provided, URLs will be printed to stdout.")
@click.option("-i", "--ignore", multiple=True, help="Pattern to ignore (regex). Can be used multiple times.")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", is_flag=True, help="Only show warnings and errors")
def main(url, output, ignore, verbose, quiet):
    """Extract file URLs from directory listings."""
    # Configure logger
    logger.remove()  # Remove default handler

    if verbose:
        logger.add(sys.stderr, level="DEBUG")
    elif quiet:
        logger.add(sys.stderr, level="WARNING")
    else:
        logger.add(sys.stderr, level="INFO")

    ignore_patterns = list(ignore) if ignore else []
    if ignore_patterns:
        logger.info(f"Ignoring URLs matching: {', '.join(ignore_patterns)}")

    # Process URLs as they are yielded
    url_count = 0
    if output:
        with open(output, "w") as f:
            for file_url in crawl_directory(url, ignore_patterns=ignore_patterns):
                f.write(file_url + "\n")
                url_count += 1
        logger.success(f"Wrote {url_count} URLs to {output}")
    else:
        for file_url in crawl_directory(url, ignore_patterns=ignore_patterns):
            print(file_url)
            url_count += 1
        logger.success(f"Found {url_count} URLs")


if __name__ == "__main__":
    main()
