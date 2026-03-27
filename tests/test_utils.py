"""Unit tests for utility functions in ProQuest Scraper."""

import os
import pytest
import tempfile
from datetime import datetime, timedelta
from proquest_download import (
    get_next_start_date,
    extract_date_from_page,
)


class TestGetNextStartDate:
    """Tests for the get_next_start_date function."""

    def test_no_files_returns_none(self):
        """Test that None is returned when download directory doesn't exist."""
        result = get_next_start_date("/nonexistent/directory")
        assert result is None

    def test_empty_directory_returns_none(self):
        """Test that None is returned for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_next_start_date(tmpdir)
            assert result is None

    def test_single_dated_file(self):
        """Test date detection with a single dated file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with date 20230101
            test_file = os.path.join(tmpdir, "20230101_0.pdf")
            open(test_file, 'a').close()
            
            result = get_next_start_date(tmpdir)
            expected = (datetime.strptime("20230101", "%Y%m%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            assert result == expected

    def test_multiple_dated_files_returns_next_after_latest(self):
        """Test that the next date after the latest file is returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with different dates
            for date_str in ["20230101_0.pdf", "20230105_0.pdf", "20230103_0.pdf"]:
                test_file = os.path.join(tmpdir, date_str)
                open(test_file, 'a').close()
            
            result = get_next_start_date(tmpdir)
            # Latest date is 20230105, so next should be 20230106
            expected = (datetime.strptime("20230105", "%Y%m%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            assert result == expected

    def test_ignores_non_dated_files(self):
        """Test that files without date pattern are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dated file and non-dated files
            open(os.path.join(tmpdir, "20230101_0.pdf"), 'a').close()
            open(os.path.join(tmpdir, "random_file.txt"), 'a').close()
            open(os.path.join(tmpdir, "document.docx"), 'a').close()
            
            result = get_next_start_date(tmpdir)
            expected = (datetime.strptime("20230101", "%Y%m%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            assert result == expected


class TestDateExtraction:
    """Tests for date extraction functionality."""

    def test_date_format_parsing(self):
        """Test that date strings are parsed correctly."""
        # This would require mocking the Playwright page object
        # For now, we'll keep it as a placeholder for integration tests
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
