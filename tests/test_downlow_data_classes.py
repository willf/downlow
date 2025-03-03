import re

from downlow.downlow_data_classes import (
    CONNECTION_ERROR,
    MAX_WAIT_TIME,
    DownloadResult,
    RateLimitState,
    find_key_matching,
    get_rate_limits,
)


def test_find_key_matching():
    headers = {"X-Rate-Limit-Remaining": "100", "X-Rate-Limit-Limit": "1000", "Retry-After": "60"}
    assert find_key_matching(headers, re.compile(r"X-Rate-Limit-Remaining", re.IGNORECASE)) == "X-Rate-Limit-Remaining"
    assert find_key_matching(headers, re.compile(r"X-Rate-Limit-Limit", re.IGNORECASE)) == "X-Rate-Limit-Limit"
    assert find_key_matching(headers, re.compile(r"Retry-After", re.IGNORECASE)) == "Retry-After"
    assert find_key_matching(headers, re.compile(r"Non-Existent-Key", re.IGNORECASE)) is None
    assert find_key_matching(headers, re.compile(r"X-Rate-Limit-Remaining", re.IGNORECASE)) == "X-Rate-Limit-Remaining"


def test_get_rate_limits():
    headers = {"X-Rate-Limit-Remaining": "100", "X-Rate-Limit-Limit": "1000", "Retry-After": "60"}
    rate_limits = get_rate_limits(headers)
    assert rate_limits.remaining.n == 100
    assert rate_limits.remaining.state == RateLimitState.KNOWN
    assert rate_limits.rate_limit.n == 1000
    assert rate_limits.rate_limit.state == RateLimitState.KNOWN
    assert rate_limits.retry_after.n == 60
    assert rate_limits.retry_after.state == RateLimitState.KNOWN
    assert rate_limits.reset_after.n == 0
    assert rate_limits.reset_after.state == RateLimitState.UNKNOWN


def test_wait_time_policy_skipped():
    result = DownloadResult(
        url="https://example.com/file.txt",
        success=False,
        status_code=200,
        rate_limits=get_rate_limits({
            "X-Rate-Limit-Remaining": "100",
            "X-Rate-Limit-Limit": "1000",
            "Retry-After": "60",
        }),
        skip=True,
        attempt_number=1,
    )
    assert result.wait_time_policy() == 0


def test_wait_time_policy_retry_after():
    result = DownloadResult(
        url="https://example.com/file.txt",
        success=False,
        status_code=429,
        rate_limits=get_rate_limits({
            "X-Rate-Limit-Remaining": "0",
            "X-Rate-Limit-Limit": "1000",
            "Retry-After": "60",
        }),
        skip=False,
        attempt_number=1,
    )
    assert result.wait_time_policy() == 60
    result_2 = DownloadResult(
        url="https://example.com/file.txt",
        success=False,
        status_code=429,
        rate_limits=get_rate_limits({
            "X-Rate-Limit-Remaining": "0",
            "X-Rate-Limit-Limit": "1000",
            "Retry-After": f"{MAX_WAIT_TIME + 1}",
        }),
        skip=False,
        attempt_number=1,
    )
    assert result_2.wait_time_policy() == MAX_WAIT_TIME


def test_wait_time_policy_rate_limit_reset_and_limit_remaining():
    result = DownloadResult(
        url="https://example.com/file.txt",
        success=False,
        status_code=429,
        rate_limits=get_rate_limits({
            "X-Rate-Limit-Remaining": "30",
            "X-Rate-Limit-Limit": "1000",
            "X-Rate-Limit-Reset": "60",
        }),
        skip=False,
        attempt_number=1,
    )
    assert result.wait_time_policy() == 2  # (60 / 30)


def test_wait_time_policy_various_failures():
    for errno in [429, 503, CONNECTION_ERROR]:
        result = DownloadResult(
            url="https://example.com/file.txt",
            success=False,
            status_code=errno,
            rate_limits=get_rate_limits({
                "X-Rate-Limit-Remaining": "1000",
                "X-Rate-Limit-Limit": "1000",
            }),
            skip=False,
            attempt_number=4,
        )
        assert result.wait_time_policy() == 8  # 2 ** (4-1)


def test_wait_time_policy_unknown_infomation():
    result = DownloadResult(
        url="https://example.com/file.txt",
        success=False,
        status_code=200,
        rate_limits=get_rate_limits({}),
        skip=False,
        attempt_number=1,
    )
    assert result.wait_time_policy() == 0
    result_2 = DownloadResult(
        url="https://example.com/file.txt",
        success=False,
        status_code=200,
        rate_limits=get_rate_limits({}),
        skip=False,
        attempt_number=2,
    )
    assert result_2.wait_time_policy() == 2
