#!/usr/bin/env python3
"""
Convert Omi memories JSON exports to an iCalendar (.ics) timeline.

Usage:
    python memories_to_ics.py memories.ics memories.json [memories2.json ...]

Each memory becomes an iCalendar event at its capture timestamp (created_at),
allowing users to visualize facts, learnings, and personal notes alongside
their daily calendar schedule in Google Calendar, Apple Calendar, or Outlook.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_DURATION = timedelta(minutes=15)


def ics_text(value: Any) -> str:
    """Escape text for an iCalendar property value (RFC 5545 §3.3.11)."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def ics_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp into an aware UTC datetime, or None if unusable."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def stamp(dt: datetime) -> str:
    """Format an aware UTC datetime into an iCalendar timestamp string."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def fold(line: str) -> List[str]:
    """Fold a content line at 75 octets (RFC 5545 §3.1), never splitting a UTF-8 character."""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return [line]
    parts: List[str] = []
    chunk, limit = b"", 75
    for ch in line:
        b = ch.encode("utf-8")
        if len(chunk) + len(b) > limit:
            parts.append(chunk.decode("utf-8"))
            chunk, limit = b" " + b, 75
        else:
            chunk += b
    parts.append(chunk.decode("utf-8"))
    return parts


def validate_destination_path(destination: str) -> None:
    """Refuse paths containing '..' components to prevent directory traversal."""
    p = Path(destination)
    if ".." in p.parts:
        raise ValueError(
            f"Destination path {destination!r} contains '..'; refusing to write outside target directory."
        )


def memory_to_vevent(item: Dict[str, Any], now_stamp: str) -> Optional[List[str]]:
    """Convert a single memory item to a list of RFC 5545 VEVENT property lines."""
    if not isinstance(item, dict):
        return None

    item_id = item.get("id")
    if not item_id or not str(item_id).strip():
        return None

    created_dt = ics_datetime(item.get("created_at"))
    if created_dt is None:
        return None

    end_dt = created_dt + DEFAULT_DURATION
    content = str(item.get("content") or item.get("title") or item.get("text") or "Untitled memory").strip()
    category = str(item.get("category") or "general").strip()

    # Short summary for calendar agenda view
    short_content = content.replace("\r\n", " ").replace("\n", " ")
    if len(short_content) > 60:
        short_content = short_content[:57] + "..."
    summary = f"[{category.capitalize()}] {short_content}"

    lines = [
        "BEGIN:VEVENT",
        f"UID:{item_id}@omi.me",
        f"DTSTAMP:{now_stamp}",
        f"DTSTART:{stamp(created_dt)}",
        f"DTEND:{stamp(end_dt)}",
        f"SUMMARY:{ics_text(summary)}",
        f"DESCRIPTION:{ics_text(content)}",
        f"CATEGORIES:{ics_text(category.upper())}",
        "END:VEVENT",
    ]
    return lines


def convert(destination: str, sources: Sequence[str]) -> int:
    """Convert one or more memory export files into a single RFC 5545 iCalendar file."""
    validate_destination_path(destination)
    now_stamp = stamp(datetime.now(timezone.utc))

    items: List[Dict[str, Any]] = []
    for source in sources:
        raw = Path(source).read_bytes().decode("utf-8-sig")
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            for key in ("memories", "items", "data"):
                if isinstance(parsed.get(key), list):
                    parsed = parsed[key]
                    break
            else:
                parsed = [parsed]
        if not isinstance(parsed, list):
            raise ValueError(f"{source}: expected a JSON array or object containing memories")
        items.extend(parsed)

    vevent_lines: List[str] = []
    converted_count = 0
    seen_ids = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id or item_id in seen_ids:
            continue
        lines = memory_to_vevent(item, now_stamp)
        if lines:
            seen_ids.add(item_id)
            converted_count += 1
            for line in lines:
                vevent_lines.extend(fold(line))

    calendar_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Omi//Memories Timeline//EN",
        "CALSCALE:GREGORIAN",
        *vevent_lines,
        "END:VCALENDAR",
    ]

    out_path = Path(destination)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\r\n".join(calendar_lines) + "\r\n", encoding="utf-8")

    return converted_count


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: python memories_to_ics.py DESTINATION.ics INPUT.json [INPUT2.json ...]")
    try:
        count = convert(sys.argv[1], sys.argv[2:])
    except (OSError, ValueError) as exc:
        sys.exit(f"iCalendar export failed: {exc}")
    print(f"Exported {count} memory event(s) to {sys.argv[1]}")
