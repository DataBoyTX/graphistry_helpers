"""KPI calculation for security posture scoring."""

from cloud_seer.core.models import Finding, KPI, Severity


def calculate_kpis(findings: list[Finding]) -> list[KPI]:
    """Calculate security KPIs from findings.

    Args:
        findings: List of security findings from the scan.

    Returns:
        List of calculated KPIs.
    """
    kpis = []

    # Count findings by severity
    severity_counts = {s: 0 for s in Severity}
    for finding in findings:
        severity_counts[finding.severity] += 1

    # Critical and High findings count
    kpis.append(KPI(
        name="Critical Findings",
        value=float(severity_counts[Severity.CRITICAL]),
        target=0.0,
        unit="count",
        description="Number of critical severity findings requiring immediate attention",
    ))

    kpis.append(KPI(
        name="High Findings",
        value=float(severity_counts[Severity.HIGH]),
        target=0.0,
        unit="count",
        description="Number of high severity findings",
    ))

    # Calculate check-specific KPIs
    kpis.extend(_calculate_mfa_kpi(findings))
    kpis.extend(_calculate_key_rotation_kpi(findings))
    kpis.extend(_calculate_cloudtrail_kpi(findings))
    kpis.extend(_calculate_guardduty_kpi(findings))

    # Calculate overall security score
    overall_score = _calculate_overall_score(findings, kpis)
    kpis.insert(0, KPI(
        name="Overall Security Score",
        value=overall_score,
        target=80.0,
        unit="percent",
        description="Weighted composite security score (0-100)",
    ))

    return kpis


def _calculate_mfa_kpi(findings: list[Finding]) -> list[KPI]:
    """Calculate MFA coverage KPI.

    Args:
        findings: List of security findings.

    Returns:
        MFA coverage KPI if applicable.
    """
    kpis = []

    # Count MFA findings
    mfa_findings = [
        f for f in findings
        if f.check_id == "iam-user-mfa-enabled"
        and f.severity != Severity.INFO  # Exclude error messages
    ]

    # We need total user count to calculate percentage
    # For now, if there are findings, MFA coverage is incomplete
    if mfa_findings:
        # Assume each finding is a user without MFA
        users_without_mfa = len(mfa_findings)
        # Estimate 100 - (findings * 10) as rough coverage
        # In practice, we'd get actual user count from raw_data
        estimated_coverage = max(0, 100 - (users_without_mfa * 10))
    else:
        # No findings = 100% coverage
        estimated_coverage = 100.0

    kpis.append(KPI(
        name="MFA Coverage",
        value=estimated_coverage,
        target=100.0,
        unit="percent",
        description="Percentage of IAM users with MFA enabled",
    ))

    # Root MFA check
    root_findings = [
        f for f in findings
        if f.check_id == "root-account-mfa-enabled"
        and f.severity == Severity.CRITICAL
    ]

    kpis.append(KPI(
        name="Root MFA",
        value=0.0 if root_findings else 100.0,
        target=100.0,
        unit="percent",
        description="Root account MFA status (100 = enabled)",
    ))

    return kpis


def _calculate_key_rotation_kpi(findings: list[Finding]) -> list[KPI]:
    """Calculate access key rotation KPI.

    Args:
        findings: List of security findings.

    Returns:
        Key rotation KPI if applicable.
    """
    kpis = []

    # Count old key findings
    old_key_findings = [
        f for f in findings
        if f.check_id == "iam-access-key-rotated"
        and f.severity != Severity.INFO
    ]

    if old_key_findings:
        # Each finding is a key that needs rotation
        keys_needing_rotation = len(old_key_findings)
        # Estimate compliance
        estimated_compliance = max(0, 100 - (keys_needing_rotation * 10))
    else:
        estimated_compliance = 100.0

    kpis.append(KPI(
        name="Key Rotation Compliance",
        value=estimated_compliance,
        target=100.0,
        unit="percent",
        description="Percentage of access keys rotated within 90 days",
    ))

    return kpis


def _calculate_cloudtrail_kpi(findings: list[Finding]) -> list[KPI]:
    """Calculate CloudTrail coverage KPI.

    Args:
        findings: List of security findings.

    Returns:
        CloudTrail coverage KPI if applicable.
    """
    kpis = []

    # Count regions without CloudTrail
    cloudtrail_findings = [
        f for f in findings
        if f.check_id == "cloudtrail-enabled"
        and f.severity != Severity.INFO
    ]

    # Get unique regions from findings
    regions_without_ct = len({f.region for f in cloudtrail_findings})

    # Get total regions scanned from all CloudTrail findings/checks
    all_ct_findings = [f for f in findings if "cloudtrail" in f.check_id.lower()]
    all_regions = {f.region for f in all_ct_findings}
    total_regions = len(all_regions) if all_regions else 1

    if regions_without_ct > 0:
        coverage = ((total_regions - regions_without_ct) / total_regions) * 100
    else:
        coverage = 100.0

    kpis.append(KPI(
        name="CloudTrail Coverage",
        value=coverage,
        target=100.0,
        unit="percent",
        description="Percentage of regions with active CloudTrail logging",
    ))

    return kpis


def _calculate_guardduty_kpi(findings: list[Finding]) -> list[KPI]:
    """Calculate GuardDuty coverage KPI.

    Args:
        findings: List of security findings.

    Returns:
        GuardDuty coverage KPI if applicable.
    """
    kpis = []

    # Count regions without GuardDuty
    guardduty_findings = [
        f for f in findings
        if f.check_id == "guardduty-enabled"
        and f.severity != Severity.INFO
    ]

    regions_without_gd = len({f.region for f in guardduty_findings})

    # Get total regions
    all_gd_findings = [f for f in findings if "guardduty" in f.check_id.lower()]
    all_regions = {f.region for f in all_gd_findings}
    total_regions = len(all_regions) if all_regions else 1

    if regions_without_gd > 0:
        coverage = ((total_regions - regions_without_gd) / total_regions) * 100
    else:
        coverage = 100.0

    kpis.append(KPI(
        name="GuardDuty Coverage",
        value=coverage,
        target=100.0,
        unit="percent",
        description="Percentage of regions with GuardDuty enabled",
    ))

    return kpis


def _calculate_overall_score(findings: list[Finding], kpis: list[KPI]) -> float:
    """Calculate overall security score.

    The score is calculated as:
    - Start at 100
    - Deduct points based on finding severity
    - Weight by KPI compliance ratios

    Args:
        findings: List of security findings.
        kpis: Already calculated KPIs.

    Returns:
        Overall security score (0-100).
    """
    # Severity deductions
    deductions = {
        Severity.CRITICAL: 15,
        Severity.HIGH: 8,
        Severity.MEDIUM: 3,
        Severity.LOW: 1,
        Severity.INFO: 0,
    }

    # Calculate deduction from findings (capped at 80 points)
    finding_deduction = sum(
        deductions[f.severity]
        for f in findings
        if f.severity != Severity.INFO
    )
    finding_deduction = min(80, finding_deduction)

    # Base score from findings
    base_score = 100 - finding_deduction

    # Adjust based on KPI compliance (up to ±20 points)
    kpi_bonus = 0
    coverage_kpis = [k for k in kpis if k.unit == "percent" and "Coverage" in k.name]

    if coverage_kpis:
        avg_coverage = sum(k.value for k in coverage_kpis) / len(coverage_kpis)
        # Bonus/penalty based on coverage (range: -10 to +10)
        kpi_bonus = (avg_coverage - 50) / 5

    final_score = max(0, min(100, base_score + kpi_bonus))
    return round(final_score, 1)
