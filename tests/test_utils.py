from unittest.mock import patch

from downlow.utils import get_tld, humanize_bytes, humanize_rate, humanize_seconds, is_valid_url, longest_common_prefix
from downlow.utils import sleep as util_sleep


def test_humanize_bytes():
    assert humanize_bytes(500) == "500 bytes"
    assert humanize_bytes(1024) == "1.00 Kb"
    assert humanize_bytes(1048576) == "1.00 Mb"
    assert humanize_bytes(1073741824) == "1.00 Gb"
    assert humanize_bytes(1099511627776) == "1.00 Tb"
    assert humanize_bytes(1536) == "1.50 Kb"
    assert humanize_bytes(1572864) == "1.50 Mb"
    assert humanize_bytes(1610612736) == "1.50 Gb"
    assert humanize_bytes(1649267441664) == "1.50 Tb"


def test_humanize_seconds():
    assert humanize_seconds(0) == ""
    assert humanize_seconds(1) == "1s"
    assert humanize_seconds(60) == "1m"
    assert humanize_seconds(3600) == "1h"
    assert humanize_seconds(3661) == "1h 1m 1s"
    assert humanize_seconds(3723) == "1h 2m 3s"
    assert humanize_seconds(86400) == "24h"
    assert humanize_seconds(90061) == "25h 1m 1s"


def test_humanize_rate():
    assert humanize_rate(100, 1) == "100.00/s"
    assert humanize_rate(100, 10) == "10.00/s"
    assert humanize_rate(100, 3600) == "1.67/m"
    assert humanize_rate(100, 86400) == "4.17/h"
    assert humanize_rate(86400, 86400) == "1.00/s"


def test_longest_common_prefix():
    assert longest_common_prefix(["flower", "flow", "flight"]) == "fl"
    assert longest_common_prefix(["dog", "racecar", "car"]) == ""
    assert longest_common_prefix(["interspecies", "interstellar", "interstate"]) == "inters"
    assert longest_common_prefix(["throne", "throne"]) == "throne"
    assert longest_common_prefix(["throne", "dungeon"]) == ""
    assert longest_common_prefix(["throne", "throne", "throne"]) == "throne"
    assert longest_common_prefix([]) == ""
    assert longest_common_prefix([""]) == ""
    assert longest_common_prefix(["a"]) == "a"
    assert longest_common_prefix(["a", "b"]) == ""


@patch("time.sleep", return_value=None)
@patch("rich.progress.track", side_effect=lambda x, description: x)
def test_sleep(mock_track, mock_sleep):
    util_sleep(10)
    assert mock_sleep.call_count == 100


def test_get_tld():
    assert get_tld("https://api.epa.gov/easey/bulk-files") == "gov"
    assert get_tld("https://www.example.com") == "com"
    assert get_tld("http://example.co.uk") == "co.uk"
    assert get_tld("ftp://example.org") == "org"
    assert get_tld("http://localhost") == ""
    assert get_tld("http://example") == ""


def test_is_valid_url():
    assert is_valid_url("https://api.epa.gov/easey/bulk-files") is not False
    assert is_valid_url("https://api.epa.gov/easey/bulk-files/") is not False
    assert is_valid_url("http://example.com") is not False
    assert is_valid_url("ftp://example.com") is not False
    assert is_valid_url("Bob") is False
    assert is_valid_url("http://") is False
    assert is_valid_url("http://example") is False
    assert is_valid_url("example.com") is False
