import os
import time
from typing import Union
from urllib.parse import ParseResult, urlparse

import tldextract
from rich.progress import track


def humanize_bytes(num_bytes: Union[int, float]) -> str:
    """
    Convert a number of bytes into a human-readable format (e.g., KB, MB, GB).

    Args:
        num_bytes: Number of bytes

    Return:
        Human-readable string
    """
    if num_bytes < 1024:
        return f"{num_bytes} bytes"
    elif num_bytes < 1024**2:
        return f"{num_bytes / 1024:.2f} Kb"
    elif num_bytes < 1024**3:
        return f"{num_bytes / 1024**2:.2f} Mb"
    elif num_bytes < 1024**4:
        return f"{num_bytes / 1024**3:.2f} Gb"
    else:
        return f"{num_bytes / 1024**4:.2f} Tb"


def humanize_seconds(seconds: Union[int, float]) -> str:
    """
    Convert a number of seconds into a human-readable
    format (e.g., 1h 10m 30s).

    Args:
        seconds: Number of seconds

    Returns:
        Human-readable string
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    formatted = ""
    if hours:
        formatted += f"{int(hours)}h "
    if minutes:
        formatted += f"{int(minutes)}m "
    if seconds:
        formatted += f"{int(seconds)}s"
    return formatted.strip()


def humanize_rate(count: int, seconds: Union[int, float]) -> str:
    """
    Convert a rate (count per second) into a human-readable format.

    Args:
        count: Number of items
        seconds: Number of seconds

    Returns:
        Human-readable string

    Examples:
    >>> humanize_rate(100, 1)
    "100.00/s"
    >>> humanize_rate(100, 10)
    "10.00/s"
    >>> humanize_rate(100, 3600)
    "1.67/m"
    >>> humanize_rate(100, 86400)
    "4.17/h"
    >>> humanize_rate(86400, 86400)
    "1.00/s"
    """

    def rates(n: int, seconds: Union[int, float]) -> tuple[float, float, float, float]:
        rate_per_second = n / seconds
        rate_per_minute = (n * 60) / seconds
        rate_per_hour = (n * 3600) / seconds
        rate_per_day = (n * 86400) / seconds
        return rate_per_second, rate_per_minute, rate_per_hour, rate_per_day

    all_rates = rates(count, seconds)
    if all_rates[0] >= 1:
        return f"{all_rates[0]:.2f}/s"
    if all_rates[1] >= 1:
        return f"{all_rates[1]:.2f}/m"
    if all_rates[2] >= 1:
        return f"{all_rates[2]:.2f}/h"
    return f"{all_rates[3]:.2f}/d"


def longest_common_prefix(strs: list[str]) -> str:
    """
    Find the longest common prefix string amongst an array of strings.
    If there is no common prefix, return an empty string "".

    Args:
        strs: List of strings

    Returns:
        The longest common prefix

    Examples:
    > longest_common_prefix(["flower", "flow", "flight"])
    "fl"
    > longest_common_prefix(["dog", "racecar", "car"])
    ""
    > longest_common_prefix(["interspecies", "interstellar", "interstate"])
    "inters"
    > longest_common_prefix(["throne", "throne"])
    "throne"
    > longest_common_prefix(["throne", "dungeon"])
    ""
    """
    if not strs:
        return ""

    # Start with the first string as the prefix
    prefix = strs[0]

    # Compare the prefix with each string in the list
    for string in strs[1:]:
        # Reduce the prefix length until it matches the start of the string
        while string[: len(prefix)] != prefix:
            prefix = prefix[:-1]
            if not prefix:
                return ""

    return prefix


def sleep(seconds: Union[int, float]) -> None:
    """
    Sleep for a given number of seconds, with progress tracking.

    Args:
        seconds: Number of seconds to sleep

    Returns:
        None
    """
    if seconds:
        time_slept = 0.00
        seconds_times_ten = int(seconds * 10)
        for _ in track(range(seconds_times_ten), description="Sleeping"):
            time.sleep(0.01)
            time_slept += 0.01
            if time_slept >= seconds:
                break


def get_tld(url: str) -> str:
    """
    Get the top-level domain (TLD) of a URL.

    Args:
        url: The URL to extract the TLD from.

    Returns:
        The TLD of the URL, or an empty string if it cannot be determined.

    Examples:
    > get_tld("https://api.epa.gov/easey/bulk-files")
    "gov"
    > get_tld("https://www.example.com")
    "com"
    > get_tld("http://example.co.uk")
    "co.uk"
    > get_tld("ftp://example")
    ""
    """
    extracted = tldextract.extract(url)
    return extracted.suffix


def is_valid_url(url: str) -> Union[bool, ParseResult]:
    """
    Is this a valid URL, for our puposes?

    Args:
        url: The URL to check.

    Returns:
        True if the URL is valid, False otherwise.

    Examples:
    > is_valid_url("https://api.epa.gov/easey/bulk-files")
    True
    > is_valid_url("https://api.epa.gov/easey/bulk-files/")
    True
    > is_valid_url("Bob")
    False
    """
    parsed = urlparse(url)
    if all([parsed.scheme, parsed.netloc]) and get_tld(url):
        return parsed
    return False


def is_file_with_extension(path: str) -> bool:
    """
    Is this a file with an extension?

    Args:
        path: The path to check.

    Returns:
        True if the path points to a file with an extension, False otherwise.

    Examples:
    > is_file_with_extension("john")
    False
    > is_file_with_extension("john.txt")
    True
    > is_file_with_extension("john.txt/")
    False
    > is_file_with_extension("/some/dir/john.txt")
    True
    """
    return all(os.path.splitext(os.path.basename(path)))
