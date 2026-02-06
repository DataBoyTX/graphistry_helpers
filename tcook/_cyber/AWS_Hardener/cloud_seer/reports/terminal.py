"""Rich terminal output for cloud-seer reports."""

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from cloud_seer.core.models import Finding, KPI, Report, Severity


def get_severity_color(severity: Severity) -> str:
    """Get Rich color for severity level."""
    colors = {
        Severity.CRITICAL: "red bold",
        Severity.HIGH: "red",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "blue",
        Severity.INFO: "dim",
    }
    return colors.get(severity, "white")


def get_severity_icon(severity: Severity) -> str:
    """Get icon for severity level."""
    icons = {
        Severity.CRITICAL: "[!]",
        Severity.HIGH: "[H]",
        Severity.MEDIUM: "[M]",
        Severity.LOW: "[L]",
        Severity.INFO: "[i]",
    }
    return icons.get(severity, "[ ]")


def render_progress_spinner(console: Console) -> Progress:
    """Create a progress spinner for scan progress."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


def render_kpis_table(kpis: list[KPI], console: Console) -> None:
    """Render KPIs as a Rich table.

    Args:
        kpis: List of KPIs to display.
        console: Rich console instance.
    """
    table = Table(
        title="Security KPIs",
        title_style="bold cyan",
        show_header=True,
        header_style="bold",
    )

    table.add_column("KPI", style="cyan")
    table.add_column("Value", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Status", justify="center")

    for kpi in kpis:
        # Format value based on unit
        if kpi.unit == "percent":
            value_str = f"{kpi.value:.1f}%"
            target_str = f"{kpi.target:.0f}%"
        elif kpi.unit == "count":
            value_str = f"{int(kpi.value)}"
            target_str = f"{int(kpi.target)}"
        else:
            value_str = f"{kpi.value:.1f} {kpi.unit}"
            target_str = f"{kpi.target:.0f} {kpi.unit}"

        # Status indicator
        if kpi.is_met:
            status = Text("PASS", style="green bold")
        else:
            if kpi.compliance_ratio < 0.5:
                status = Text("FAIL", style="red bold")
            else:
                status = Text("WARN", style="yellow bold")

        table.add_row(kpi.name, value_str, target_str, status)

    console.print(table)
    console.print()


def render_findings_summary(findings: list[Finding], console: Console) -> None:
    """Render findings summary by severity.

    Args:
        findings: List of findings.
        console: Rich console instance.
    """
    # Count by severity
    severity_counts = {s: 0 for s in Severity}
    for finding in findings:
        severity_counts[finding.severity] += 1

    # Build summary text
    summary_parts = []
    for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
        count = severity_counts[severity]
        if count > 0:
            color = get_severity_color(severity)
            summary_parts.append(f"[{color}]{severity.value.upper()}: {count}[/]")

    summary_text = " | ".join(summary_parts) if summary_parts else "No findings"

    panel = Panel(
        summary_text,
        title="Findings Summary",
        title_align="left",
        border_style="cyan",
    )
    console.print(panel)
    console.print()


def render_findings_table(
    findings: list[Finding],
    console: Console,
    max_findings: int = 50,
    severity_filter: list[Severity] | None = None,
) -> None:
    """Render findings as a Rich table.

    Args:
        findings: List of findings to display.
        console: Rich console instance.
        max_findings: Maximum findings to show.
        severity_filter: Optional filter for specific severities.
    """
    # Filter findings
    if severity_filter:
        findings = [f for f in findings if f.severity in severity_filter]

    # Sort by severity
    severity_order = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 4,
    }
    findings = sorted(findings, key=lambda f: severity_order[f.severity])

    if not findings:
        console.print("[dim]No findings to display[/]")
        return

    table = Table(
        title=f"Security Findings ({len(findings)} total)",
        title_style="bold cyan",
        show_header=True,
        header_style="bold",
        row_styles=["", "dim"],
    )

    table.add_column("Sev", width=4, justify="center")
    table.add_column("Account", width=14)
    table.add_column("Region", width=14)
    table.add_column("Resource", width=20)
    table.add_column("Finding", width=50)

    for finding in findings[:max_findings]:
        severity_color = get_severity_color(finding.severity)
        severity_icon = get_severity_icon(finding.severity)

        # Truncate long titles
        title = finding.title
        if len(title) > 48:
            title = title[:45] + "..."

        # Truncate resource ID
        resource = finding.resource_id
        if len(resource) > 18:
            resource = resource[:15] + "..."

        table.add_row(
            Text(severity_icon, style=severity_color),
            finding.account_id[:14],
            finding.region,
            resource,
            title,
        )

    console.print(table)

    if len(findings) > max_findings:
        console.print(
            f"[dim]... and {len(findings) - max_findings} more findings[/]"
        )

    console.print()


def render_finding_details(finding: Finding, console: Console) -> None:
    """Render detailed view of a single finding.

    Args:
        finding: Finding to display.
        console: Rich console instance.
    """
    severity_color = get_severity_color(finding.severity)

    content = Text()
    content.append(f"Severity: ", style="bold")
    content.append(f"{finding.severity.value.upper()}\n", style=severity_color)
    content.append(f"Provider: ", style="bold")
    content.append(f"{finding.provider}\n")
    content.append(f"Account: ", style="bold")
    content.append(f"{finding.account_id}\n")
    content.append(f"Region: ", style="bold")
    content.append(f"{finding.region}\n")
    content.append(f"Resource: ", style="bold")
    content.append(f"{finding.resource_type} / {finding.resource_id}\n\n")
    content.append(f"Description:\n", style="bold")
    content.append(f"{finding.description}\n\n")
    content.append(f"Remediation:\n", style="bold cyan")
    content.append(f"{finding.remediation}")

    panel = Panel(
        content,
        title=finding.title,
        title_align="left",
        border_style=severity_color.split()[0],
    )
    console.print(panel)


def render_report(report: Report, console: Console | None = None) -> None:
    """Render a complete report to the terminal.

    Args:
        report: Report to display.
        console: Optional Rich console (creates new if not provided).
    """
    if console is None:
        console = Console()

    # Header
    console.print()
    console.print(
        Panel(
            f"[bold]Cloud-Seer Security Audit Report[/]\n"
            f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"Accounts: {len(report.accounts)} | "
            f"Findings: {len(report.findings)} | "
            f"Duration: {report.scan_duration_seconds:.1f}s",
            border_style="cyan",
        )
    )
    console.print()

    # KPIs
    render_kpis_table(report.kpis, console)

    # Findings summary
    render_findings_summary(report.findings, console)

    # Findings table (exclude INFO)
    actionable_findings = [
        f for f in report.findings if f.severity != Severity.INFO
    ]
    if actionable_findings:
        render_findings_table(actionable_findings, console)

    # Critical findings detail
    critical_findings = [
        f for f in report.findings if f.severity == Severity.CRITICAL
    ]
    if critical_findings:
        console.print("[bold red]CRITICAL FINDINGS - Immediate Action Required:[/]\n")
        for finding in critical_findings:
            render_finding_details(finding, console)
            console.print()
