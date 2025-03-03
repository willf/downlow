import enum
import re
import time
from dataclasses import dataclass
from typing import Union

MAX_WAIT_TIME = 2**20  # seconds, about 292 hours
CONNECTION_ERROR = -1  # magic number for connection error


class RateLimitState(enum.Enum):
    """
    Record state of rate limit information.
    UNKNOWN: We don't know anything about the rate limit.
    KNOWN: We know the rate limit.
    """

    UNKNOWN = 1
    KNOWN = 2


def find_key_matching(headers: dict[str, str], regex: re.Pattern) -> Union[None, str]:
    """
    Given a regular expression, find the first key in the headers that matches
    the regular expression.

    Args:
        headers: A dictionary of headers.
        regex: A regular expression to match against the keys in the headers.
    Returns:
        The first key that matches the regular expression, or None if no key
        matches.

    Examples:

    > find_key_matching({"X-Rate-Limit-Remaining": "100"}, re.compile(r"(X-|)Rate-?Limit-Remaining", re.IGNORECASE))
    "X-Rate-Limit-Remaining"
    > find_key_matching({"Retry-After": "100"}, re.compile(r"Retry-?After", re.IGNORECASE))
    "Retry-After"
    > find_key_matching({}, re.compile(r"Retry-?After", re.IGNORECASE))
    None
    """
    for key in headers:
        if regex.fullmatch(key):
            return key
    return None


@dataclass
class RateLimitPair:
    """
    A pair of rate limit values, with a state indicating whether the value is
    actually known or unknown.

    Attributes:
        n: The value of the rate limit.
        state: The state of the rate limit, indicating whether it is known or
            unknown.
    """

    n: int
    state: RateLimitState


@dataclass
class RateLimits:
    """
    A collection of rate limit values, with a state indicating whether the
    value is actually known or unknown.
    Attributes:
        remaining: The number of requests remaining in the current rate limit
            window.
        rate_limit: The maximum number of requests allowed in the current
            rate limit window.
        retry_after: The amount of time to wait before making another request.
        reset_after: The amount of time until the rate limit window resets.
    """

    remaining: RateLimitPair
    rate_limit: RateLimitPair
    retry_after: RateLimitPair
    reset_after: RateLimitPair


@dataclass
class DownloadResult:
    """
    A result of a download attempt, including the URL, success status,
    status code, rate limits, and whether the download should be skipped.
    Also includes the attempt number for retry logic.
    Attributes:
        url: The URL that was attempted to be downloaded.
        success: Whether the download was successful.
        status_code: The HTTP status code returned by the server.
        rate_limits: The rate limits returned by the server.
        skip: Whether the download should be skipped.
        attempt_number: The number of attempts made to download the URL.
    """

    url: str
    success: bool
    status_code: int
    rate_limits: RateLimits
    skip: bool
    attempt_number: int = 0

    def wait_time_policy(self) -> Union[int, float]:
        """
        Define the wait time policy for the download result.

        This method calculates the wait time based on the rate limits and
        other conditions.

        Returns:
            The wait time in seconds.
        """
        # if for some reason we are skipping this item, we do not need to wait
        if self.skip:
            return 0
        # if we have a retry-after header, we should wait that amount of time
        # but perhaps not more than the MAX_WAIT_TIME
        if self.rate_limits.retry_after.n > 0 and self.rate_limits.retry_after.state == RateLimitState.KNOWN:
            return min(self.rate_limits.retry_after.n, MAX_WAIT_TIME)
        ## If we have both a RateLimitRemaining and RateLimitReset header, we
        ## can calculate how long to wait. But we need to check if the
        ## RateLimitReset is a Unix epoch time or a duration in seconds
        if (
            self.rate_limits.remaining.n > 0
            and self.rate_limits.remaining.state == RateLimitState.KNOWN
            and self.rate_limits.reset_after.n > 0
            and self.rate_limits.reset_after.state == RateLimitState.KNOWN
        ):
            if self.rate_limits.reset_after.n > 1000000000:
                duration = self.rate_limits.reset_after.n - time.time()
            else:
                duration = self.rate_limits.reset_after.n
            # we can only do n calls in duration seconds, so we should wait
            # duration / n seconds
            return duration / self.rate_limits.remaining.n
        ## if the status is 429, a server problem, or a connection problem
        ## we should wait 2^attempt_number seconds
        ## Or, we are just at attempt 2 etc.
        if self.status_code in [429, 503, CONNECTION_ERROR] or self.attempt_number > 1:
            return 2 ** (self.attempt_number - 1)  # type: ignore[no-any-return]
        ## if we know *nothing* then don't wait
        return 0


def get_rate_limit_key(regex: re.Pattern, headers: dict) -> RateLimitPair:
    """
    Get a rate limit key from the headers.

    Args:
        regex: A regular expression to match against the keys in the headers.
        headers: A dictionary of headers.

    Returns:
        A RateLimitPair with the value of the rate limit and whether it is actually
        known or unknown.
    """
    key = find_key_matching(headers, regex)
    if key:
        return RateLimitPair(int(headers[key]), RateLimitState.KNOWN)
    return RateLimitPair(0, RateLimitState.UNKNOWN)


def get_quota_remaining(headers: dict) -> RateLimitPair:  # pragma: no cover
    """
    Get the remaining quota from the headers.

    Args:
        headers: A dictionary of headers.

    Returns:
        A RateLimitPair with the remaining quota and its state.

    Examples:
    > get_quota_remaining({"X-Rate-Limit-Remaining": "100"})
    RateLimitPair(100, RateLimitState.KNOWN)
    > get_quota_remaining({"X-Rate-Limit-Remaining": "0"})
    RateLimitPair(0, RateLimitState.KNOWN)
    > get_quota_remaining({})
    RateLimitPair(0, RateLimitState.UNKNOWN)
    """
    regex = re.compile(r"(X-|)Rate-?Limit-Remaining", re.IGNORECASE)
    return get_rate_limit_key(regex, headers)


def get_rate_limit(headers: dict) -> RateLimitPair:  # pragma: no cover
    """
    > get_rate_limit({"X-Rate-Limit-Limit": "100"})
    RateLimitPair(100, RateLimitState.KNOWN)
    > get_rate_limit({"X-Rate-Limit-Limit": "0"})
    RateLimitPair(0, RateLimitState.KNOWN)
    > get_rate_limit({})
    RateLimitPair(0, RateLimitState.UNKNOWN)
    """
    regex = re.compile(r"(X-|)Rate-?Limit-Limit", re.IGNORECASE)
    return get_rate_limit_key(regex, headers)


def get_retry_after(headers: dict) -> RateLimitPair:  # pragma: no cover
    """
    > get_retry_after({"Retry-After": "100"})
    RateLimitPair(100, RateLimitState.KNOWN)
    > get_retry_after({"Retry-After": "0"})
    RateLimitPair(0, RateLimitState.KNOWN)
    > get_retry_after({})
    RateLimitPair(0, RateLimitState.UNKNOWN)
    """
    regex = re.compile(r"Retry-?After", re.IGNORECASE)
    return get_rate_limit_key(regex, headers)


def get_ratelimit_reset(headers: dict) -> RateLimitPair:  # pragma: no cover
    """
    > get_ratelimit_reset({"X-Rate-Limit-Reset": "100"})
    RateLimitPair(100, RateLimitState.KNOWN)
    > get_ratelimit_reset({"X-Rate-Limit-Reset": "0"})
    RateLimitPair(0, RateLimitState.KNOWN)
    > get_ratelimit_reset({})
    RateLimitPair(0, RateLimitState.UNKNOWN)
    """
    regex = re.compile(r"(X-|)Rate-?Limit-Reset", re.IGNORECASE)
    return get_rate_limit_key(regex, headers)


def get_rate_limits(headers: dict) -> RateLimits:
    """
    Get all the rate limits from the headers.

    Args:
        headers: A dictionary of headers.

    Returns:
        A RateLimits object with all the rate limits and their states.
    """
    quota_remaining = get_quota_remaining(headers)
    rate_limit = get_rate_limit(headers)
    retry_after = get_retry_after(headers)
    reset_after = get_ratelimit_reset(headers)
    return RateLimits(quota_remaining, rate_limit, retry_after, reset_after)


def blank_rate_limits() -> RateLimits:
    """
    Return a blank RateLimits object with all values set to 0 and state set to UNKNOWN.
    This is useful for initializing a RateLimits object when no headers are available.

    Returns:
        A RateLimits object with all values set to 0 and state set to UNKNOWN.
    """
    return RateLimits(
        RateLimitPair(0, RateLimitState.UNKNOWN),
        RateLimitPair(0, RateLimitState.UNKNOWN),
        RateLimitPair(0, RateLimitState.UNKNOWN),
        RateLimitPair(0, RateLimitState.UNKNOWN),
    )
