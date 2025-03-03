"""Download a list of URLs with tenacity and grace."""

import os
import random
import re
import sys
from typing import Union
from urllib.parse import urlparse

import click
import requests  # type: ignore[import-untyped]
from loguru import logger

from downlow.downlow_data_classes import (
    CONNECTION_ERROR,
    DownloadResult,
    blank_rate_limits,
    get_rate_limits,
)
from downlow.utils import (
    humanize_bytes,
    is_file_with_extension,
    is_valid_url,
    longest_common_prefix,
    sleep,
)


class Downloader:
    def __init__(
        self,
        urls: list[str],
        download_dir: str,
        prefixes_to_remove: Union[list[str], None] = None,
        max_tries: int = 10,
    ) -> None:
        self.urls = urls
        self.download_dir = download_dir
        self.prefixes_to_remove = prefixes_to_remove or []
        self.number_of_successful_downloads = 0
        self.number_of_failed_downloads = 0
        self.number_of_existing_files = 0
        self.max_tries = max_tries

    def download_file(self, url: str, attempt_number: int) -> DownloadResult:  # noqa: C901
        """
        Download a file from a URL.

        Args:
            url: URL to download.
            attempt_number: Number of the download attempt.
        """
        url = url.strip()
        parsed = is_valid_url(url)
        if not parsed:
            logger.error(f"Invalid URL: {url}")
            return DownloadResult(url, False, 0, blank_rate_limits(), True, attempt_number)
        path = parsed.path.lstrip("/")  # type: ignore[union-attr]
        old_path = path
        for prefix in self.prefixes_to_remove:
            path = path.replace(prefix.lstrip("/"), "")
        local_path = os.path.join(self.download_dir, path.lstrip("/"))
        logger.debug(
            f"Old path: {old_path} new path: {path}; Local path: {local_path}; URL: {url}; Prefixes: {self.prefixes_to_remove}"
        )
        if not is_file_with_extension(local_path):
            logger.error(f"Invalid filename: {local_path}")
            return DownloadResult(url, False, 0, blank_rate_limits(), True, attempt_number)
        if os.path.exists(local_path):
            logger.info(f"{local_path} already exists, skipping.")
            self.number_of_existing_files += 1
            return DownloadResult(url, True, 200, blank_rate_limits(), True, attempt_number)
        # OK, let's try to download the file
        try:
            r = requests.get(url, stream=True, timeout=31)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Request failed: {e}")
            self.number_of_failed_downloads += 1
            return DownloadResult(url, False, CONNECTION_ERROR, blank_rate_limits(), False, attempt_number)

        status_code = r.status_code
        logger.trace(f"Headers: {r.headers}")
        rate_limits = get_rate_limits(dict(r.headers))
        logger.debug(f"RATE LIMITS: {rate_limits}")
        success = status_code >= 200 and status_code < 300
        logger.debug(f"SUCCESS: {success}; STATUS CODE: {status_code}; URL: {url}")
        content_length = r.headers.get("Content-Length")
        sz = "Unknown"
        if content_length:
            sz = humanize_bytes(int(content_length))
        logger.debug(f"Content length: {sz}")
        download_result = DownloadResult(url, success, status_code, rate_limits, False, attempt_number)
        if success:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            # if we fail to write the content, well, let's just fail
            try:
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            except Exception as e:
                logger.error(f"Error writing to {local_path}: {e}")
                self.number_of_failed_downloads += 1
                return download_result
            logger.info(f"Downloaded {url} to {local_path}; Content size: {sz}")
            self.number_of_successful_downloads += 1
        else:
            logger.error(f"Error downloading {url}, result: {download_result}")
            self.number_of_failed_downloads += 1
        return download_result

    def download_all(self) -> None:
        """
        Download all URLs in the list.


        """
        number_of_urls = len(self.urls)
        for i, url in enumerate(self.urls, start=1):
            percent_done = 100.0 * i / number_of_urls
            logger.info(f"Downloading {i}/{number_of_urls} ({percent_done:.2f}%): {url} ...")
            result = None
            for attempt_number in range(self.max_tries):
                if attempt_number > 0:
                    logger.info(f"Attempt number {attempt_number + 1} to download {url}")
                result = self.download_file(url, attempt_number + 1)
                sleep_time = result.wait_time_policy()
                if sleep_time > 0:
                    sleep(sleep_time)
                if result.success or result.skip:
                    break
            if not (result or result.success) and not result.skip:  # type: ignore[union-attr]
                logger.error(f"Failed to download {url} after {self.max_tries} attempts")


@click.command()
@click.option(
    "--url-file",
    default=None,
    help="Path to a file containing URLs (defaults to stdin).",
)
@click.option(
    "--download-dir",
    type=click.Path(dir_okay=True),
    default="download",
    show_default=True,
    help="Directory to save downloads.",
)
@click.option(
    "--prefixes-to-remove",
    multiple=True,
    default=[],
    help="Prefixes to remove from the URL path when saving the file.",
)
@click.option(
    "--auto-remove-prefix",
    is_flag=True,
    default=False,
    help="Remove the longest common prefix from the URL paths",
)
@click.option(
    "--regex",
    type=str,
    default=None,
    help="Regular expression to match URLs to download.",
)
@click.option(
    "--reverse",
    is_flag=True,
    default=False,
    help="Reverse the regex match, i.e., download URLs that do not match the regex.",
)
@click.option(
    "--randomize",
    is_flag=True,
    default=False,
    help="Randomize the order of the URLs",
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False),
    default=None,
    show_default=True,
    help="Path to a file to log output.",
)
@click.option(
    "--log-level",
    default="INFO",
    show_default=True,
    help="Logging level.",
)
@click.option(
    "--max-tries",
    default=10,
    show_default=True,
    help="Maximum number of retries on request failures",
)
@click.version_option(version="1.0.0")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="If set, do not actually download the files, just log what would be done.",
)
def main(
    url_file: str,
    download_dir: str,
    prefixes_to_remove: list[str],
    auto_remove_prefix: bool,
    regex: str,
    reverse: bool,
    randomize: bool,
    log_file: str,
    log_level: str = "INFO",
    max_tries: int = 10,
    dry_run: bool = False,
) -> None:
    """
    Download a list of URLs with tenacity and grace.

    """
    logger.remove()
    logger.add(sys.stdout, level=log_level.upper())
    if log_file:
        logger.add(log_file, level=log_level.upper())
    prefixes_to_remove = list(prefixes_to_remove)
    if not url_file:
        logger.info("Reading URLs from standard input.")
        urls = [url.strip() for url in sys.stdin.readlines()]
    else:
        logger.info(f"Reading URLs from file: {url_file}")
        with open(url_file) as f:
            urls = [url.strip() for url in f.readlines()]

    # strip empty URLs and lines starting with #
    urls = [url for url in urls if url and not url.startswith("#")]

    if regex:
        pattern = re.compile(regex)
        old_len = len(urls)
        if reverse:
            urls = [url for url in urls if not pattern.search(url)]
            logger.info(f"Filtered URLs from {old_len} to {len(urls)} which do not match regex: {regex}")
        else:
            urls = [url for url in urls if pattern.search(url)]
            logger.info(f"Filtered URLs from {old_len} to {len(urls)} which match regex: {regex}")

    if randomize:
        random.shuffle(urls)
    if auto_remove_prefix:
        longest_prefix = longest_common_prefix([urlparse(url).path for url in urls if url])
        prefixes_to_remove.append(longest_prefix)
        logger.info(f"Auto-removing prefix: {longest_prefix}")
    if dry_run:
        logger.info("Dry run enabled; not downloading files.")
        logger.info(f"Would download {len(urls)} URLs to {download_dir}")
        return
    downloader = Downloader(urls, download_dir, prefixes_to_remove, max_tries=max_tries)
    downloader.download_all()
    logger.info(f"Download complete; processed {len(urls)} URLs")
    logger.info(f"Number of existing files: {downloader.number_of_existing_files}")
    logger.info(f"Number of successful downloads: {downloader.number_of_successful_downloads}")
    logger.info(f"Number of failed download attempts: {downloader.number_of_failed_downloads}")


if __name__ == "__main__":
    main()
