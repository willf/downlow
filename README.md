# downlow: A Bulk Downloader with Grace and Tenacity

[![Build status](https://img.shields.io/github/actions/workflow/status/willf/downlow/main.yml?branch=main)](https://github.com/willf/downlow/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/willf/downlow)](https://img.shields.io/github/commit-activity/m/willf/downlow)
[![License](https://img.shields.io/github/license/willf/downlow)](https://img.shields.io/github/license/willf/downlow)

A bulk downloader with tenacity and grace

- **Github repository**: <https://github.com/willf/downlow/>
- **Documentation** <https://pypi.org/project/downlow/>

Attempt to bulk download a list of URLs with some tenacity, but also
some grace. Attempts to honor the server's rate limiting and retries
on various failures.

## Understanding the use case

This was originally written to download approximately 226,000 URLs
from a website that allows only 1000 requests per hour. Well, that's
too many hours, but a subset of the data could be collected of only
59,000 URLs. There is a HTTP 429 response code, to indicate when
too many requests are being made, and the server will return a
`Retry-After` header to indicate how long to wait before retrying.
These are web standards; some web servers also return headers
that indicate:

1. The maximum number of requests allowed per hour
2. The number of requests remaining in the current hour
3. The time when the rate limit will reset

Different servers call these by different names. The rate limit header usually
looks something like `RateLimit-Limit`. The remaining requests header usually looks like
`RateLimit-Remaining`. The reset time header usually looks like `RateLimit-Reset`,
although the reset might be a duration (the rate limit will reset in so many
seconds) or a point in time (the rate limit will reset at this time). Servers
are free to do what they will, of course, and not of these are exactly
promises.

Of course, there are lots of other things that can go wrong.

This script attempts to not go beyond the server's declared rate limits,
and pay attention to the other headers if they are present. It also. It tries
to be tenacious in the face of failures, and tries a number of times to
download a file before giving up, using exponential backoff.

## Installation

This script requires Python 3.8 or later, and the `uv` package. This
is not a package yet, so you have to clone the repository and run it
from the repo directory.

You can install it with:

```bash
$ git clone git@github.com:willf/downlow.git
$ cd downlow
$ uv sync
```

## Usage

```bash
$ uv run downlow --help
Usage: downlow [OPTIONS]

Usage: downlow [OPTIONS]

Options:
  --url-file TEXT            Path to a file containing URLs (defaults to
                             stdin).
  --download-dir PATH        Directory to save downloads.  [default: download]
  --prefixes-to-remove TEXT  Prefixes to remove from the URL path when saving
                             the file.
  --auto-remove-prefix       Remove the longest common prefix from the URL
                             paths
  --regex TEXT               Regular expression to match URLs to download.
  --reverse                  Reverse the regex match, i.e., download URLs that
                             do not match the regex.
  --randomize                Randomize the order of the URLs
  --log-file FILE            Path to a file to log output.
  --log-level TEXT           Logging level.  [default: INFO]
  --max-tries INTEGER        Maximum number of retries on request failures
                             [default: 10]
  --version                  Show the version and exit.
  --dry-run                  If set, do not actually download the files, just
                             log what would be done.
  --help                     Show this message and exit.

```

Examples:

```bash
$ uv run downlow --url-file urls.txt --download-dir downloads --auto-remove-prefix
$ cat urls.txt | uv run downlow --download-dir downloads --max-tries 5
```

## Examplation of the options

- `--url-file`: Path to a file containing URLs. This is the only required
  option. Each line in the file should contain a single URL. Blank lines
  and lines starting with `#` are ignored.
- `--download-dir`: Directory to save downloads. If not specified, it defaults to `download` in the current directory.
- `--prefixes-to-remove`: This can be used multiple times to specify
  prefixes to remove from the URL path when saving the file. For example,
  if the URL is `https://example.com/foo/bar/baz.txt`, and you specify
  `--prefixes-to-remove foo`, then the file will
  be saved as `bar/baz.txt`. This is useful if you want to save the files
  in a directory structure that is shallower than the URL path.
- `--auto-remove-prefix`: If set, the script will automatically remove the longest common prefix from the URL paths when saving the file. For example, if the URLs are all under `https://example.com/foo/`, then the files will be saved in the `foo` directory.
- `--regex`: Regular expression to match URLs to download. If specified,
  only URLs that match the regex will be downloaded. This is useful if
  you want to download a subset of the URLs in the file.
- `--reverse`: If set, the script will download URLs that do _not_ match
  the regex. This is useful if you want to download all URLs except
  a subset.
- `--randomize`: If set, the script will randomize the order of the URLs before downloading them. You might want to do this in order to collect a random set of results before the server is no longer available.
- `--log-file`: Path to a file to log output. If not specified, the log will only be printed to the console.
- `--log-level`: Logging level. This can be one of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. The default is `INFO`.
- `--max-tries`: Maximum number of retries on request failures. The default is 10 (all told, this is about half an hour of waiting if everything fails). The max is around 20 (around 83 weeks total, hehe).
- `--dry-run`: If set, the script will not actually download the files, but will log what would be done. This is useful if you want to see what the script would do without actually downloading the files.
- `--version`: Show the version and exit.
- `--help`: Show this message and exit.

Notice that this is a single-threaded script; it is most useful when rate limits are likely to be present.
