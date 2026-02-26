from __future__ import annotations

import csv
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from fmcli.commands.icloud_export import (
    export_icloud_contacts,
    _run_applescript_batch,
    _extract_emails_from_vcards,
    _parse_batch_output,
    _sanitize_filename,
)


# ---------------------------------------------------------------------------
# Sample vCard data
# ---------------------------------------------------------------------------

VCARD_JOHN = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-john-001
FN:John Doe
EMAIL;type=INTERNET;type=HOME:john@example.com
EMAIL;type=INTERNET;type=WORK:john.doe@work.com
TEL;type=CELL:+1234567890
END:VCARD"""

VCARD_JANE = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-jane-002
FN:Jane Smith
EMAIL;type=INTERNET:jane@example.com
END:VCARD"""

VCARD_NO_EMAIL = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-bob-003
FN:Bob No-Email
TEL;type=CELL:+9876543210
END:VCARD"""

VCARD_SPECIAL_CHARS = """\
BEGIN:VCARD
VERSION:3.0
UID:uid-special-004
FN:O'Brien / Müller
EMAIL;type=INTERNET:obrien@example.com
END:VCARD"""


# Separator used between contacts in batch output
BATCH_SEP = "<<<CONTACT_SEP>>>"
EMAIL_SEP = "<<<EMAIL_SEP>>>"


def _make_batch_output(*vcards_and_emails: tuple[str, list[str]]) -> str:
    """Build the stdout that _run_applescript_batch would produce.

    Each tuple is (vcard_text, [email1, email2, ...]).
    Format per contact: vcard_text\\n---EMAILS---\\nemail1<<<EMAIL_SEP>>>email2
    Contacts separated by <<<CONTACT_SEP>>>
    """
    parts = []
    for vcard, emails in vcards_and_emails:
        email_str = EMAIL_SEP.join(emails)
        parts.append(f"{vcard}\n---EMAILS---\n{email_str}")
    return BATCH_SEP.join(parts)


# ---------------------------------------------------------------------------
# Tests: _sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_simple_name(self) -> None:
        assert _sanitize_filename("John Doe") == "John_Doe"

    def test_special_characters(self) -> None:
        assert _sanitize_filename("O'Brien / Müller") == "OBrien__Mller"

    def test_empty_string(self) -> None:
        result = _sanitize_filename("")
        assert result == "unnamed"

    def test_only_special_chars(self) -> None:
        result = _sanitize_filename("///")
        assert result == "unnamed"


# ---------------------------------------------------------------------------
# Tests: _parse_batch_output
# ---------------------------------------------------------------------------


class TestParseBatchOutput:
    def test_parses_single_contact(self) -> None:
        output = _make_batch_output((VCARD_JOHN, ["john@example.com", "john.doe@work.com"]))
        results = _parse_batch_output(output)

        assert len(results) == 1
        assert results[0]["vcard"] == VCARD_JOHN
        assert results[0]["emails"] == ["john@example.com", "john.doe@work.com"]

    def test_parses_multiple_contacts(self) -> None:
        output = _make_batch_output(
            (VCARD_JOHN, ["john@example.com"]),
            (VCARD_JANE, ["jane@example.com"]),
        )
        results = _parse_batch_output(output)

        assert len(results) == 2
        assert "John Doe" in results[0]["vcard"]
        assert "Jane Smith" in results[1]["vcard"]

    def test_contact_without_emails(self) -> None:
        output = _make_batch_output((VCARD_NO_EMAIL, []))
        results = _parse_batch_output(output)

        assert len(results) == 1
        assert results[0]["emails"] == []

    def test_empty_output(self) -> None:
        results = _parse_batch_output("")
        assert results == []


# ---------------------------------------------------------------------------
# Tests: _extract_emails_from_vcards
# ---------------------------------------------------------------------------


class TestExtractEmails:
    def test_extracts_emails_with_name(self) -> None:
        contacts = [
            {"vcard": VCARD_JOHN, "emails": ["john@example.com", "john.doe@work.com"], "filename": "John_Doe.vcf"},
        ]
        rows = _extract_emails_from_vcards(contacts)

        assert len(rows) == 2
        assert rows[0] == {"name": "John Doe", "email": "john@example.com", "vcard_filename": "John_Doe.vcf"}
        assert rows[1] == {"name": "John Doe", "email": "john.doe@work.com", "vcard_filename": "John_Doe.vcf"}

    def test_skips_contacts_without_emails(self) -> None:
        contacts = [
            {"vcard": VCARD_NO_EMAIL, "emails": [], "filename": "Bob_No-Email.vcf"},
        ]
        rows = _extract_emails_from_vcards(contacts)

        assert rows == []

    def test_multiple_contacts(self) -> None:
        contacts = [
            {"vcard": VCARD_JOHN, "emails": ["john@example.com"], "filename": "John_Doe.vcf"},
            {"vcard": VCARD_JANE, "emails": ["jane@example.com"], "filename": "Jane_Smith.vcf"},
        ]
        rows = _extract_emails_from_vcards(contacts)

        assert len(rows) == 2
        assert rows[0]["name"] == "John Doe"
        assert rows[1]["name"] == "Jane Smith"

    def test_special_chars_in_name(self) -> None:
        contacts = [
            {"vcard": VCARD_SPECIAL_CHARS, "emails": ["obrien@example.com"], "filename": "OBrien__Mller.vcf"},
        ]
        rows = _extract_emails_from_vcards(contacts)

        assert len(rows) == 1
        assert rows[0]["name"] == "O'Brien / Müller"


# ---------------------------------------------------------------------------
# Tests: _run_applescript_batch
# ---------------------------------------------------------------------------


class TestRunApplescriptBatch:
    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_calls_osascript(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_make_batch_output((VCARD_JOHN, ["john@example.com"])),
            stderr="",
        )

        result = _run_applescript_batch(start=1, count=10)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "osascript"
        assert args[1] == "-e"

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_returns_parsed_contacts(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=_make_batch_output(
                (VCARD_JOHN, ["john@example.com"]),
                (VCARD_JANE, ["jane@example.com"]),
            ),
            stderr="",
        )

        result = _run_applescript_batch(start=1, count=10)

        assert len(result) == 2

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_raises_on_applescript_error(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="execution error: some error",
        )

        with pytest.raises(RuntimeError, match="AppleScript"):
            _run_applescript_batch(start=1, count=10)

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_batch_range_in_script(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        _run_applescript_batch(start=101, count=50)

        script = mock_run.call_args[0][0][2]  # osascript -e <script>
        assert "101" in script
        assert "150" in script  # start + count - 1


# ---------------------------------------------------------------------------
# Tests: export_icloud_contacts (integration with mocks)
# ---------------------------------------------------------------------------


class TestExportIcloudContacts:
    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_creates_output_dir(self, mock_run: MagicMock, tmp_path: Path) -> None:
        output_dir = tmp_path / "export"
        emails_file = tmp_path / "emails.csv"

        # First call: get count. Second call: batch.
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="2", stderr=""),  # count
            MagicMock(
                returncode=0,
                stdout=_make_batch_output(
                    (VCARD_JOHN, ["john@example.com"]),
                    (VCARD_JANE, ["jane@example.com"]),
                ),
                stderr="",
            ),
        ]

        export_icloud_contacts(
            output_dir=output_dir,
            fmt="individual",
            emails_file=emails_file,
        )

        assert output_dir.is_dir()

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_writes_individual_vcf_files(self, mock_run: MagicMock, tmp_path: Path) -> None:
        output_dir = tmp_path / "export"
        emails_file = tmp_path / "emails.csv"

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="2", stderr=""),
            MagicMock(
                returncode=0,
                stdout=_make_batch_output(
                    (VCARD_JOHN, ["john@example.com"]),
                    (VCARD_JANE, ["jane@example.com"]),
                ),
                stderr="",
            ),
        ]

        export_icloud_contacts(
            output_dir=output_dir,
            fmt="individual",
            emails_file=emails_file,
        )

        vcf_files = list(output_dir.glob("*.vcf"))
        assert len(vcf_files) == 2

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_writes_multi_vcf_file(self, mock_run: MagicMock, tmp_path: Path) -> None:
        output_dir = tmp_path / "export"
        emails_file = tmp_path / "emails.csv"

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="2", stderr=""),
            MagicMock(
                returncode=0,
                stdout=_make_batch_output(
                    (VCARD_JOHN, ["john@example.com"]),
                    (VCARD_JANE, ["jane@example.com"]),
                ),
                stderr="",
            ),
        ]

        export_icloud_contacts(
            output_dir=output_dir,
            fmt="multi",
            emails_file=emails_file,
        )

        multi_file = output_dir / "all_contacts.vcf"
        assert multi_file.exists()
        content = multi_file.read_text()
        assert "John Doe" in content
        assert "Jane Smith" in content

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_writes_emails_csv(self, mock_run: MagicMock, tmp_path: Path) -> None:
        output_dir = tmp_path / "export"
        emails_file = tmp_path / "emails.csv"

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="2", stderr=""),
            MagicMock(
                returncode=0,
                stdout=_make_batch_output(
                    (VCARD_JOHN, ["john@example.com", "john.doe@work.com"]),
                    (VCARD_JANE, ["jane@example.com"]),
                ),
                stderr="",
            ),
        ]

        export_icloud_contacts(
            output_dir=output_dir,
            fmt="individual",
            emails_file=emails_file,
        )

        assert emails_file.exists()
        with open(emails_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["name"] == "John Doe"
        assert rows[0]["email"] == "john@example.com"
        assert rows[2]["email"] == "jane@example.com"

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_handles_contacts_without_email(self, mock_run: MagicMock, tmp_path: Path) -> None:
        output_dir = tmp_path / "export"
        emails_file = tmp_path / "emails.csv"

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="1", stderr=""),
            MagicMock(
                returncode=0,
                stdout=_make_batch_output((VCARD_NO_EMAIL, [])),
                stderr="",
            ),
        ]

        export_icloud_contacts(
            output_dir=output_dir,
            fmt="individual",
            emails_file=emails_file,
        )

        vcf_files = list(output_dir.glob("*.vcf"))
        assert len(vcf_files) == 1

        with open(emails_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 0

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_batches_large_contact_lists(self, mock_run: MagicMock, tmp_path: Path) -> None:
        output_dir = tmp_path / "export"
        emails_file = tmp_path / "emails.csv"

        # 250 contacts = 3 batches with BATCH_SIZE=100 (100+100+50)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="250", stderr=""),  # count
            MagicMock(
                returncode=0,
                stdout=_make_batch_output(
                    *[(VCARD_JOHN, ["john@example.com"])] * 100
                ),
                stderr="",
            ),
            MagicMock(
                returncode=0,
                stdout=_make_batch_output(
                    *[(VCARD_JANE, ["jane@example.com"])] * 100
                ),
                stderr="",
            ),
            MagicMock(
                returncode=0,
                stdout=_make_batch_output(
                    *[(VCARD_JOHN, ["john@example.com"])] * 50
                ),
                stderr="",
            ),
        ]

        export_icloud_contacts(
            output_dir=output_dir,
            fmt="individual",
            emails_file=emails_file,
        )

        # 1 count call + 3 batch calls
        assert mock_run.call_count == 4

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_handles_duplicate_filenames(self, mock_run: MagicMock, tmp_path: Path) -> None:
        output_dir = tmp_path / "export"
        emails_file = tmp_path / "emails.csv"

        # Two contacts with same name
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="2", stderr=""),
            MagicMock(
                returncode=0,
                stdout=_make_batch_output(
                    (VCARD_JOHN, ["john@example.com"]),
                    (VCARD_JOHN, ["john2@example.com"]),
                ),
                stderr="",
            ),
        ]

        export_icloud_contacts(
            output_dir=output_dir,
            fmt="individual",
            emails_file=emails_file,
        )

        vcf_files = list(output_dir.glob("*.vcf"))
        assert len(vcf_files) == 2

    def test_platform_check_non_darwin(self, tmp_path: Path) -> None:
        with patch("fmcli.commands.icloud_export.sys") as mock_sys:
            mock_sys.platform = "linux"

            with pytest.raises(RuntimeError, match="macOS"):
                export_icloud_contacts(
                    output_dir=tmp_path / "export",
                    fmt="individual",
                    emails_file=tmp_path / "emails.csv",
                )

    @patch("fmcli.commands.icloud_export.subprocess.run")
    def test_zero_contacts(self, mock_run: MagicMock, tmp_path: Path) -> None:
        output_dir = tmp_path / "export"
        emails_file = tmp_path / "emails.csv"

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="0", stderr=""),
        ]

        export_icloud_contacts(
            output_dir=output_dir,
            fmt="individual",
            emails_file=emails_file,
        )

        # Only the count call, no batch calls
        assert mock_run.call_count == 1
