"""Export all contacts from Apple Contacts (iCloud) via AppleScript.

This module uses osascript to read vCard data and email addresses from the
macOS Contacts app and writes them to disk as .vcf files and an emails CSV.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

BATCH_SIZE = 100
CONTACT_SEP = "<<<CONTACT_SEP>>>"
EMAIL_SEP = "<<<EMAIL_SEP>>>"


def _sanitize_filename(name: str) -> str:
    """Turn a display name into a safe filename (without extension).

    Keeps ASCII alphanumerics, hyphens and underscores. Spaces become
    underscores. Falls back to ``"unnamed"`` if the result is empty.
    """
    sanitized = re.sub(r"[^\w\-]", "", name.replace(" ", "_"), flags=re.ASCII)
    return sanitized if sanitized else "unnamed"


def _extract_fn_from_vcard(vcard_text: str) -> str:
    """Return the FN (formatted name) from a vCard string, or ``""``."""
    for line in vcard_text.splitlines():
        if line.startswith("FN:"):
            return line[3:].strip()
    return ""


def _build_batch_script(start: int, end: int) -> str:
    """Return the AppleScript source to export contacts *start* through *end*.

    The script writes one block per contact to stdout using well-known
    separators so that the Python side can split the output reliably.
    """
    return f'''\
tell application "Contacts"
    set output to ""
    set endIdx to {end}
    set totalPeople to count of people
    if endIdx > totalPeople then set endIdx to totalPeople
    repeat with i from {start} to endIdx
        set p to person i
        set vc to vcard of p
        set emailList to value of every email of p
        set emailStr to ""
        repeat with j from 1 to count of emailList
            if j > 1 then set emailStr to emailStr & "{EMAIL_SEP}"
            set emailStr to emailStr & (item j of emailList as text)
        end repeat
        if i > {start} then set output to output & "{CONTACT_SEP}"
        set output to output & vc & "\\n---EMAILS---\\n" & emailStr
    end repeat
    return output
end tell'''


def _parse_batch_output(output: str) -> list[dict[str, Any]]:
    """Parse the raw stdout of a batch AppleScript run.

    Returns a list of dicts, each containing:
    - ``vcard``: the raw vCard text
    - ``emails``: a list of email address strings
    """
    if not output or not output.strip():
        return []

    results: list[dict[str, Any]] = []
    blocks = output.split(CONTACT_SEP)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if "---EMAILS---" in block:
            vcard_part, email_part = block.split("---EMAILS---", 1)
        else:
            vcard_part = block
            email_part = ""

        vcard_text = vcard_part.strip()
        email_part = email_part.strip()
        emails = [e.strip() for e in email_part.split(EMAIL_SEP) if e.strip()] if email_part else []

        results.append({"vcard": vcard_text, "emails": emails})
    return results


def _run_applescript_batch(start: int, count: int) -> list[dict[str, Any]]:
    """Execute one AppleScript batch and return parsed contact dicts.

    Parameters
    ----------
    start:
        1-based index of the first contact to export.
    count:
        Number of contacts to export in this batch.

    Raises
    ------
    RuntimeError
        If the ``osascript`` process exits with a non-zero return code.
    """
    end = start + count - 1
    script = _build_batch_script(start, end)
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error (batch {start}-{end}): {result.stderr.strip()}")
    return _parse_batch_output(result.stdout)


def _get_contact_count() -> int:
    """Ask Apple Contacts how many people are in the address book."""
    result = subprocess.run(
        ["osascript", "-e", 'tell application "Contacts" to count of people'],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error (count): {result.stderr.strip()}")
    return int(result.stdout.strip())


def _extract_emails_from_vcards(
    contacts: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build email CSV rows from parsed contact dicts.

    Each input dict must have keys ``vcard``, ``emails``, and ``filename``.
    Returns one row per email address with columns ``name``, ``email``,
    ``vcard_filename``.
    """
    rows: list[dict[str, str]] = []
    for contact in contacts:
        if not contact["emails"]:
            continue
        name = _extract_fn_from_vcard(contact["vcard"])
        for email in contact["emails"]:
            rows.append({
                "name": name,
                "email": email,
                "vcard_filename": contact["filename"],
            })
    return rows


def _unique_filename(stem: str, suffix: str, used: set[str]) -> str:
    """Return a filename not yet in *used* and register it.

    Appends ``_2``, ``_3``, ... to *stem* if necessary.
    """
    candidate = f"{stem}{suffix}"
    if candidate not in used:
        used.add(candidate)
        return candidate
    counter = 2
    while True:
        candidate = f"{stem}_{counter}{suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        counter += 1


def export_icloud_contacts(
    output_dir: Path,
    fmt: str = "individual",
    emails_file: Path | None = None,
) -> None:
    """Export contacts from Apple Contacts via AppleScript.

    Parameters
    ----------
    output_dir:
        Directory to write ``.vcf`` files into (created if missing).
    fmt:
        ``"individual"`` for one ``.vcf`` per contact, ``"multi"`` for a
        single ``all_contacts.vcf`` containing every vCard.
    emails_file:
        Path for the email CSV.  ``None`` skips CSV generation.
    """
    if sys.platform != "darwin":
        raise RuntimeError("iCloud contact export is only supported on macOS.")

    import typer

    total = _get_contact_count()
    typer.echo(f"Found {total} contacts in Apple Contacts.")

    if total == 0:
        typer.echo("Nothing to export.")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_contacts: list[dict[str, Any]] = []
    used_filenames: set[str] = set()
    exported = 0

    for batch_start in range(1, total + 1, BATCH_SIZE):
        batch_count = min(BATCH_SIZE, total - batch_start + 1)
        typer.echo(f"Exporting contacts {batch_start}–{batch_start + batch_count - 1} of {total} ...")
        batch = _run_applescript_batch(start=batch_start, count=batch_count)

        for contact in batch:
            name = _extract_fn_from_vcard(contact["vcard"])
            stem = _sanitize_filename(name)
            filename = _unique_filename(stem, ".vcf", used_filenames)
            contact["filename"] = filename
            all_contacts.append(contact)
            exported += 1

    # Write vCard files
    if fmt == "individual":
        for contact in all_contacts:
            path = output_dir / contact["filename"]
            path.write_text(contact["vcard"])
        typer.echo(f"Wrote {exported} individual .vcf files to {output_dir}")
    else:
        multi_path = output_dir / "all_contacts.vcf"
        multi_path.write_text("\n".join(c["vcard"] for c in all_contacts))
        typer.echo(f"Wrote {exported} contacts to {multi_path}")

    # Write emails CSV
    if emails_file is not None:
        emails_file = Path(emails_file)
        emails_file.parent.mkdir(parents=True, exist_ok=True)
        rows = _extract_emails_from_vcards(all_contacts)
        with open(emails_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "email", "vcard_filename"])
            writer.writeheader()
            writer.writerows(rows)
        typer.echo(f"Wrote {len(rows)} email entries to {emails_file}")
