import os
import time
from urllib.parse import urlparse

from rich.progress import track
import tldextract


def humanize_bytes(num_bytes):
    """
    Convert a number of bytes into a human-readable format (e.g., KB, MB, GB).

    :param num_bytes: Number of bytes
    :return: Human-readable string
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


def longest_common_prefix(strs):
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


def sleep(seconds):
    if seconds:
        time_slept = 0
        seconds_times_ten = int(seconds * 10)
        for _ in track(range(seconds_times_ten), description="Sleeping"):
            time.sleep(0.01)
            time_slept += 0.01
            if time_slept >= seconds:
                break


def get_tld(url):
    extracted = tldextract.extract(url)
    return extracted.suffix


def is_valid_url(url):
    """
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
    return None


def is_file_with_extension(path):
    """
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
