"""
Tests for utility functions.
"""
import unittest
from pathlib import Path
import tempfile

from streamhawk.utils import (
    extract_imdb_id, 
    sanitize_filename, 
    parse_quality,
    HistoryManager,
    format_bytes
)


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""
    
    def test_extract_imdb_id_direct(self):
        """Test extracting IMDb ID from direct input."""
        self.assertEqual(extract_imdb_id("tt0816692"), "tt0816692")
        self.assertEqual(extract_imdb_id("tt0468569"), "tt0468569")
    
    def test_extract_imdb_id_from_url(self):
        """Test extracting IMDb ID from URL."""
        test_cases = [
            ("https://www.imdb.com/title/tt0816692/", "tt0816692"),
            ("imdb.com/title/tt0468569", "tt0468569"),
            ("https://imdb.com/Title?tt1375666", "tt1375666"),
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url):
                self.assertEqual(extract_imdb_id(url), expected)
    
    def test_extract_imdb_id_invalid(self):
        """Test invalid IMDb ID extraction."""
        self.assertIsNone(extract_imdb_id("invalid"))
        self.assertIsNone(extract_imdb_id(""))
        self.assertIsNone(extract_imdb_id("not-an-id"))
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("movie: title", "movie_ title"),
            ("file<name>.mp4", "file_name_.mp4"),
            ("path\\to\\file", "path_to_file"),
            ("normal_file", "normal_file"),
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                self.assertEqual(sanitize_filename(input_name), expected)
    
    def test_parse_quality(self):
        """Test quality parsing."""
        test_cases = [
            ("best", 9999),
            ("4k", 2160),
            ("1080p", 1080),
            ("720p", 720),
            ("worst", 0),
            ("invalid", 1080),  # default
        ]
        
        for quality, expected in test_cases:
            with self.subTest(quality=quality):
                self.assertEqual(parse_quality(quality), expected)
    
    def test_format_bytes(self):
        """Test byte formatting."""
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.00 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.00 GB")
    
    def test_history_manager(self):
        """Test history management."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            history = HistoryManager(str(history_file))
            
            # Add entry
            history.add("tt0816692", "Interstellar", "success")
            
            # Check recent
            recent = history.get_recent(1)
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0]["imdb_id"], "tt0816692")
            
            # Find by IMDb
            found = history.find_by_imdb("tt0816692")
            self.assertEqual(len(found), 1)


if __name__ == "__main__":
    unittest.main()
