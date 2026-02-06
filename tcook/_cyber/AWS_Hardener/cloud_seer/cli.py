"""Cloud-seer CLI entry point."""

import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console

from cloud_seer.core.config import CloudSeerConfig, generate_sample_config
from cloud_seer.core.models import AccountSummary, Report, Severity
from cloud_seer.kpis.calculator import calculate_kpis
from cloud_seer.providers.aws.scanner import AWSScanner
from cloud_seer.providers.aws.session import AWSSessionManager
from cloud_seer.reports.html.generator import save_html_report
from cloud_seer.reports.json_report import save_json_report
from cloud_seer.reports.markdown import save_markdown_report
from cloud_seer.reports.terminal import render_report, render_progress_spinner

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="cloud-seer")
def cli():
    """Cloud-seer: Multi-cloud security audit tool.

    Scan AWS (and future GCP/Azure) accounts for security issues and
    generate comprehensive reports with KPIs.
    """
    pass


@cli.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Path to configuration file for multi-account scanning",
)
@click.option(
    "--output", "-o",
    multiple=True,
    type=click.Choice(["terminal", "json", "html", "markdown", "all"]),
    default=["terminal"],
    help="Output formats (can specify multiple)",
)
@click.option(
    "--output-dir", "-d",
    type=click.Path(),
    default="./reports",
    help="Directory for output files",
)
@click.option(
    "--checks",
    type=str,
    help="Comma-separated list of checks to run (e.g., iam,cloudtrail)",
)
@click.option(
    "--regions",
    type=str,
    help="Comma-separated list of regions to scan",
)
@click.option(
    "--account",
    type=str,
    help="Single account ID to scan (uses assume-role)",
)
@click.option(
    "--role",
    type=str,
    default="SecurityAuditRole",
    help="IAM role name to assume in target accounts",
)
def audit(config, output, output_dir, checks, regions, account, role):
    """Run security audit and generate reports.

    Examples:

        # Scan current account, terminal output
        cloud-seer audit

        # Scan with all outputs
        cloud-seer audit --output all --output-dir ./reports

        # Scan specific checks
        cloud-seer audit --checks iam,cloudtrail

        # Multi-account via config file
        cloud-seer audit --config accounts.yaml
    """
    start_time = datetime.utcnow()

    # Handle "all" output option
    output_formats = set(output)
    if "all" in output_formats:
        output_formats = {"terminal", "json", "html", "markdown"}

    # Parse checks if provided
    enabled_checks = None
    if checks:
        enabled_checks = [c.strip() for c in checks.split(",")]

    # Parse regions if provided
    scan_regions = None
    if regions:
        scan_regions = [r.strip() for r in regions.split(",")]

    # Load config if provided
    cfg = None
    if config:
        cfg = CloudSeerConfig.from_file(config)
        if not scan_regions and cfg.default_regions:
            scan_regions = cfg.default_regions
        if cfg.default_role_name:
            role = cfg.default_role_name

    # Initialize session manager and scanner
    session_manager = AWSSessionManager(default_role_name=role)
    scanner = AWSScanner(
        session_manager=session_manager,
        checks=enabled_checks,
        progress_callback=lambda msg: console.print(f"[dim]{msg}[/]"),
    )

    console.print("\n[bold cyan]Cloud-Seer Security Audit[/]\n")

    # Determine accounts to scan
    accounts_to_scan = []

    if cfg and cfg.accounts:
        # Multi-account from config
        accounts_to_scan = [
            (acc.id, acc.name, acc.role_name or role)
            for acc in cfg.accounts
            if acc.enabled
        ]
    elif account:
        # Single specified account
        accounts_to_scan = [(account, account, role)]
    else:
        # Current account
        try:
            current_account = session_manager.get_current_account_id()
            accounts_to_scan = [(current_account, "Current Account", None)]
        except Exception as e:
            console.print(f"[red]Error getting current account: {e}[/]")
            console.print("[yellow]Ensure AWS credentials are configured.[/]")
            sys.exit(1)

    console.print(f"Scanning {len(accounts_to_scan)} account(s)...")

    # Run scans
    all_findings = []
    account_summaries = []

    with render_progress_spinner(console) as progress:
        for acc_id, acc_name, acc_role in accounts_to_scan:
            task = progress.add_task(f"Scanning {acc_name}...", total=None)

            try:
                findings = scanner.scan(
                    account_id=acc_id,
                    regions=scan_regions,
                    role_name=acc_role,
                )
                all_findings.extend(findings)

                # Get account summary
                summary = scanner.get_account_summary(acc_id, acc_role)
                summary.account_name = acc_name

                # Count findings for this account
                severity_counts = {s.value: 0 for s in Severity}
                for f in findings:
                    if f.account_id == acc_id:
                        severity_counts[f.severity.value] += 1
                summary.finding_counts = severity_counts

                account_summaries.append(summary)

            except Exception as e:
                console.print(f"[red]Error scanning {acc_name}: {e}[/]")
                account_summaries.append(AccountSummary(
                    account_id=acc_id,
                    account_name=acc_name,
                    provider="aws",
                ))

            progress.remove_task(task)

    # Calculate KPIs
    kpis = calculate_kpis(all_findings)

    # Build report
    end_time = datetime.utcnow()
    report = Report(
        generated_at=end_time,
        accounts=account_summaries,
        findings=all_findings,
        kpis=kpis,
        overall_score=kpis[0].value if kpis else 0,
        scan_duration_seconds=(end_time - start_time).total_seconds(),
    )

    # Generate outputs
    output_dir = Path(output_dir)
    timestamp = end_time.strftime("%Y%m%d-%H%M%S")

    if "terminal" in output_formats:
        render_report(report, console)

    if "json" in output_formats:
        json_path = output_dir / f"cloud-seer-report-{timestamp}.json"
        save_json_report(report, json_path)
        console.print(f"[green]JSON report saved:[/] {json_path}")

    if "markdown" in output_formats:
        md_path = output_dir / f"cloud-seer-report-{timestamp}.md"
        save_markdown_report(report, md_path)
        console.print(f"[green]Markdown report saved:[/] {md_path}")

    if "html" in output_formats:
        html_path = output_dir / f"cloud-seer-report-{timestamp}.html"
        save_html_report(report, html_path)
        console.print(f"[green]HTML dashboard saved:[/] {html_path}")

    # Exit with appropriate code
    critical_count = sum(1 for f in all_findings if f.severity == Severity.CRITICAL)
    if critical_count > 0:
        sys.exit(2)  # Critical findings
    elif any(1 for f in all_findings if f.severity == Severity.HIGH):
        sys.exit(1)  # High findings
    sys.exit(0)


@cli.group()
def checks():
    """Manage security checks."""
    pass


@checks.command("list")
def list_checks():
    """List available security checks."""
    console.print("\n[bold]Available Security Checks[/]\n")

    checks_info = [
        ("iam", "IAM security checks", [
            "Root account MFA status",
            "IAM user MFA enforcement",
            "Access key age (>90 days)",
            "Unused access keys",
            "Recently created users (backdoor detection)",
        ]),
        ("cloudtrail", "CloudTrail logging checks", [
            "Trail enabled in each region",
            "Log file validation",
        ]),
        ("guardduty", "GuardDuty threat detection checks", [
            "Detector enabled in each region",
            "High-severity findings",
        ]),
        ("config", "AWS Config compliance checks", [
            "Configuration recorder status",
            "Config rule compliance",
        ]),
    ]

    for check_id, description, sub_checks in checks_info:
        console.print(f"[cyan bold]{check_id}[/] - {description}")
        for sub in sub_checks:
            console.print(f"  - {sub}")
        console.print()

    console.print("[dim]Use --checks to filter: cloud-seer audit --checks iam,cloudtrail[/]")


@cli.group()
def config():
    """Configuration management."""
    pass


@config.command("init")
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="cloud-seer.yaml",
    help="Output file path",
)
def config_init(output):
    """Generate a sample configuration file."""
    path = Path(output)

    if path.exists():
        if not click.confirm(f"{path} already exists. Overwrite?"):
            return

    with open(path, "w") as f:
        f.write(generate_sample_config())

    console.print(f"[green]Sample configuration written to:[/] {path}")
    console.print("[dim]Edit this file to configure your accounts.[/]")


@config.command("validate")
@click.argument("config_path", type=click.Path(exists=True))
def config_validate(config_path):
    """Validate a configuration file."""
    try:
        cfg = CloudSeerConfig.from_file(config_path)
        console.print(f"[green]Configuration valid![/]")
        console.print(f"  Accounts: {len(cfg.accounts)}")
        console.print(f"  Default role: {cfg.default_role_name}")
        console.print(f"  Organizations: {'enabled' if cfg.organizations.enabled else 'disabled'}")
    except Exception as e:
        console.print(f"[red]Configuration error:[/] {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
