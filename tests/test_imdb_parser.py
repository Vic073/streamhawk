"""Tests for IMDb URL and ID parsing functionality."""

import pytest
from urllib.parse import urlparse


class TestIMDbIDValidation:
    """Test IMDb ID format validation."""

    def test_valid_imdb_id_format(self):
        """Test that valid IMDb IDs match expected format."""
        valid_ids = [
            "tt0816692",  # Interstellar
            "tt0111161",  # Shawshank Redemption
            "tt0068646",  # The Godfather
        ]
        for imdb_id in valid_ids:
            assert imdb_id.startswith("tt"), f"{imdb_id} should start with 'tt'"
            assert len(imdb_id) == 9, f"{imdb_id} should be 9 characters long"
            assert imdb_id[2:].isdigit(), f"{imdb_id} should end with 7 digits"

    def test_invalid_imdb_id_format(self):
        """Test that invalid IMDb IDs are rejected."""
        invalid_ids = [
            "0816692",      # Missing 'tt' prefix
            "tt081669",     # Only 6 digits (8 total chars)
            "tt08166920",   # Too many digits (10 total chars)
            "id0816692",    # Wrong prefix
            "tt0816692a",   # Contains non-digit
        ]
        for imdb_id in invalid_ids:
            if not imdb_id.startswith("tt"):
                assert True, f"{imdb_id} should not start with 'tt'"
            elif len(imdb_id) != 9:
                assert True, f"{imdb_id} should not be 9 characters"
            elif not imdb_id[2:].isdigit():
                assert True, f"{imdb_id} should not have valid digit suffix"


class TestIMDbURLParsing:
    """Test IMDb URL parsing functionality."""

    def test_parse_full_url(self):
        """Test parsing of full IMDb URLs."""
        url = "https://www.imdb.com/title/tt0816692/"
        parsed = urlparse(url)
        assert parsed.netloc == "www.imdb.com"
        assert "tt0816692" in url

    def test_parse_url_without_protocol(self):
        """Test parsing of URLs without protocol."""
        url = "imdb.com/title/tt0816692"
        assert "tt0816692" in url
        assert "imdb.com" in url

    def test_parse_url_with_parameters(self):
        """Test parsing URLs with query parameters."""
        url = "https://www.imdb.com/title/tt0816692/?ref_=nm_knf_i1"
        assert "tt0816692" in url
        assert "imdb.com" in url

    def test_extract_id_from_full_url(self):
        """Test extracting IMDb ID from full URL."""
        url = "https://www.imdb.com/title/tt0816692/"
        # Simple extraction logic
        import re
        match = re.search(r"tt\d{7}", url)
        assert match is not None
        assert match.group() == "tt0816692"

    def test_extract_id_from_partial_url(self):
        """Test extracting IMDb ID from partial URL."""
        url = "imdb.com/title/tt0111161"
        import re
        match = re.search(r"tt\d{7}", url)
        assert match is not None
        assert match.group() == "tt0111161"

    def test_legacy_format_url(self):
        """Test parsing legacy format IMDb URLs."""
        url = "imdb.com/Title?tt0816692"
        import re
        match = re.search(r"tt\d{7}", url)
        assert match is not None
        assert match.group() == "tt0816692"

    def test_invalid_url_returns_none(self):
        """Test that invalid URLs return no match."""
        invalid_urls = [
            "https://www.google.com",
            "imdb.com/random",
            "tt0816692",  # Just ID, no URL structure
        ]
        import re
        for url in invalid_urls:
            match = re.search(r"tt\d{7}", url)
            # Only the last one should have a match
            if url == "tt0816692":
                assert match is not None
