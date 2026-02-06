"""JSON export for cloud-seer reports."""

import json
from pathlib import Path

from cloud_seer.core.models import Report


def generate_json_report(report: Report, indent: int = 2) -> str:
    """Generate JSON report string.

    Args:
        report: Report to convert.
        indent: JSON indentation level.

    Returns:
        JSON string representation of the report.
    """
    return json.dumps(report.to_dict(), indent=indent, default=str)


def save_json_report(report: Report, path: str | Path, indent: int = 2) -> Path:
    """Save report as JSON file.

    Args:
        report: Report to save.
        path: Output file path.
        indent: JSON indentation level.

    Returns:
        Path to the saved file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write(generate_json_report(report, indent))

    return path
