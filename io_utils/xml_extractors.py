from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from typing import Any


@dataclass(frozen=True)
class ParsedXmlPayload:
    source_path: Path
    record_type: str
    table_name: str
    rows: list[dict[str, str]]


def discover_xml_files(source_path: str | Path) -> list[Path]:
    path = Path(source_path).expanduser().resolve()

    if path.is_file():
        if path.suffix.lower() != ".xml":
            raise ValueError(f"Expected an XML file, received: {path}")
        return [path]

    if path.is_dir():
        files = sorted(candidate for candidate in path.rglob("*.xml") if candidate.is_file())
        if not files:
            raise FileNotFoundError(f"No XML files found under {path}")
        return files

    raise FileNotFoundError(f"Source path does not exist: {path}")


def parse_sumo_xml_file(file_path: str | Path, job_id: str) -> ParsedXmlPayload:
    path = Path(file_path).expanduser().resolve()
    tree = ET.parse(path)
    root = tree.getroot()

    if root.findall("interval"):
        rows = _parse_interval_rows(root, job_id, path)
        record_type = "e2"
    elif root.findall("tripinfo"):
        rows = _parse_tripinfo_rows(root, job_id, path)
        record_type = "tripinfo"
    else:
        raise ValueError(
            "Unsupported SUMO XML structure. Expected 'interval' (E2) or 'tripinfo' records "
            f"in {path}"
        )

    return ParsedXmlPayload(
        source_path=path,
        record_type=record_type,
        table_name=f"bronze_{record_type}",
        rows=rows,
    )


def sanitize_identifier(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", value).strip("_").lower()
    return cleaned or "simulation_run"


def _parse_interval_rows(root: ET.Element, job_id: str, path: Path) -> list[dict[str, Any]]:
    """Extract raw E2 detector interval records. Casting and unit conversions are handled in dbt."""
    rows: list[dict[str, Any]] = []

    for interval in root.findall("interval"):
        row = interval.attrib.copy()

        # Remove e2_ prefix from id
        if 'id' in row:
            row['id'] = re.sub(r'^e2_', '', row['id'])

        rows.append(_with_metadata(row, job_id, path, "e2"))

    return rows


def _parse_tripinfo_rows(root: ET.Element, job_id: str, path: Path) -> list[dict[str, Any]]:
    """Extract raw TripInfo records. Casting and unit conversions are handled in dbt."""
    rows: list[dict[str, Any]] = []

    for tripinfo in root.findall("tripinfo"):
        row = tripinfo.attrib.copy()
        rows.append(_with_metadata(row, job_id, path, "tripinfo"))

    return rows


def _with_metadata(row: dict[str, Any], job_id: str, path: Path, record_type: str) -> dict[str, Any]:
    row["sim_job_id"] = job_id
    row["source_file_name"] = path.name
    row["source_file_path"] = str(path)
    row["xml_record_type"] = record_type
    return row