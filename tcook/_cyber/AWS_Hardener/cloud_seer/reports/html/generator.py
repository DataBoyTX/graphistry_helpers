"""HTML report generator using Jinja2 templates."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cloud_seer.core.models import KPI, Report, Severity


def _get_template_dir() -> Path:
    """Get the templates directory path."""
    return Path(__file__).parent / "templates"


def _format_kpi_value(kpi: KPI) -> str:
    """Format KPI value for display."""
    if kpi.unit == "percent":
        return f"{kpi.value:.1f}%"
    elif kpi.unit == "count":
        return f"{int(kpi.value)}"
    return f"{kpi.value:.1f}"


def _format_kpi_target(kpi: KPI) -> str:
    """Format KPI target for display."""
    if kpi.unit == "percent":
        return f"{kpi.target:.0f}%"
    elif kpi.unit == "count":
        return f"{int(kpi.target)}"
    return f"{kpi.target:.0f}"


def _get_kpi_bar_width(kpi: KPI) -> float:
    """Calculate progress bar width percentage."""
    if kpi.unit == "count":
        # For counts (lower is better), invert
        if kpi.target == 0:
            return 100 if kpi.value == 0 else 0
        return max(0, min(100, 100 - (kpi.value / max(kpi.target, 1)) * 100))
    # For percentages, direct mapping
    return min(100, max(0, kpi.value))


def _get_status_class(kpi: KPI) -> str:
    """Get CSS class for KPI status."""
    if kpi.is_met:
        return "pass"
    if kpi.compliance_ratio < 0.5:
        return "fail"
    return "warn"


def _get_score_class(score: float) -> str:
    """Get CSS class for overall score."""
    if score >= 80:
        return "good"
    if score >= 60:
        return "warning"
    return "critical"


def generate_html_report(report: Report) -> str:
    """Generate HTML report string.

    Args:
        report: Report to convert.

    Returns:
        HTML string representation of the report.
    """
    template_dir = _get_template_dir()
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template("dashboard.html")

    # Prepare KPI data for template
    kpi_data = []
    for kpi in report.kpis:
        kpi_data.append({
            "name": kpi.name,
            "value_formatted": _format_kpi_value(kpi),
            "target_formatted": _format_kpi_target(kpi),
            "bar_width": _get_kpi_bar_width(kpi),
            "status_class": _get_status_class(kpi),
        })

    # Prepare severity counts
    severity_counts = {s.value: 0 for s in Severity}
    for finding in report.findings:
        severity_counts[finding.severity.value] += 1

    # Separate findings by severity
    critical_findings = [
        {
            "title": f.title,
            "account_id": f.account_id,
            "region": f.region,
            "resource_id": f.resource_id,
            "description": f.description,
            "remediation": f.remediation,
            "severity": f.severity.value,
        }
        for f in report.findings
        if f.severity == Severity.CRITICAL
    ]

    high_findings = [
        {
            "title": f.title,
            "account_id": f.account_id,
            "region": f.region,
            "resource_id": f.resource_id,
            "description": f.description,
            "remediation": f.remediation,
            "severity": f.severity.value,
        }
        for f in report.findings
        if f.severity == Severity.HIGH
    ]

    other_findings = [
        {
            "title": f.title,
            "account_id": f.account_id,
            "region": f.region,
            "resource_id": f.resource_id,
            "severity": f.severity.value,
        }
        for f in report.findings
        if f.severity in [Severity.MEDIUM, Severity.LOW]
    ]

    # Get overall score
    overall_kpi = next(
        (k for k in report.kpis if k.name == "Overall Security Score"), None
    )
    overall_score = overall_kpi.value if overall_kpi else 0

    # Render template
    html = template.render(
        generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        accounts_count=len(report.accounts),
        scan_duration=f"{report.scan_duration_seconds:.1f}",
        overall_score=f"{overall_score:.0f}",
        score_class=_get_score_class(overall_score),
        kpis=kpi_data,
        severity_counts=severity_counts,
        critical_findings=critical_findings,
        high_findings=high_findings,
        other_findings=other_findings,
    )

    return html


def save_html_report(report: Report, path: str | Path) -> Path:
    """Save report as HTML file.

    Args:
        report: Report to save.
        path: Output file path.

    Returns:
        Path to the saved file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write(generate_html_report(report))

    return path
