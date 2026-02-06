"""GuardDuty security checks for AWS accounts."""

from uuid import uuid4

from botocore.exceptions import ClientError

from cloud_seer.core.models import Finding, Severity


def check_guardduty_enabled(
    guardduty_client, account_id: str, region: str
) -> list[Finding]:
    """Check if GuardDuty is enabled in the region.

    Args:
        guardduty_client: boto3 GuardDuty client for the region.
        account_id: AWS account ID.
        region: AWS region being checked.

    Returns:
        List of findings for GuardDuty issues.
    """
    findings = []

    try:
        response = guardduty_client.list_detectors()
        detector_ids = response.get("DetectorIds", [])

        if not detector_ids:
            findings.append(Finding(
                id=str(uuid4()),
                title=f"GuardDuty not enabled in region {region}",
                severity=Severity.HIGH,
                resource_type="AWS::GuardDuty::Detector",
                resource_id=f"guardduty-{region}",
                account_id=account_id,
                region=region,
                provider="aws",
                description=(
                    f"GuardDuty is not enabled in region {region}. GuardDuty provides "
                    f"intelligent threat detection for your AWS environment, analyzing "
                    f"CloudTrail, VPC Flow Logs, and DNS logs for malicious activity."
                ),
                remediation=(
                    f"Enable GuardDuty in region {region}:\n"
                    f"aws guardduty create-detector --enable --region {region}\n\n"
                    f"Consider enabling across all regions for comprehensive coverage."
                ),
                check_id="guardduty-enabled",
                raw_data={"detectors": detector_ids, "region": region},
            ))
        else:
            # Check if detector is actually enabled
            for detector_id in detector_ids:
                try:
                    detector_response = guardduty_client.get_detector(
                        DetectorId=detector_id
                    )
                    status = detector_response.get("Status", "")

                    if status != "ENABLED":
                        findings.append(Finding(
                            id=str(uuid4()),
                            title=f"GuardDuty detector disabled in region {region}",
                            severity=Severity.HIGH,
                            resource_type="AWS::GuardDuty::Detector",
                            resource_id=detector_id,
                            account_id=account_id,
                            region=region,
                            provider="aws",
                            description=(
                                f"GuardDuty detector '{detector_id}' exists but is not enabled "
                                f"(status: {status}). Threat detection is not active."
                            ),
                            remediation=(
                                f"Enable the GuardDuty detector:\n"
                                f"aws guardduty update-detector --detector-id {detector_id} "
                                f"--enable --region {region}"
                            ),
                            check_id="guardduty-enabled",
                            raw_data={
                                "detector_id": detector_id,
                                "status": status,
                                "region": region,
                            },
                        ))

                except ClientError as e:
                    findings.append(Finding(
                        id=str(uuid4()),
                        title=f"Failed to get GuardDuty detector status in {region}",
                        severity=Severity.INFO,
                        resource_type="AWS::GuardDuty::Detector",
                        resource_id=detector_id,
                        account_id=account_id,
                        region=region,
                        provider="aws",
                        description=f"Could not get detector details: {e}",
                        remediation="Ensure the scanning role has guardduty:GetDetector permission.",
                        check_id="guardduty-enabled",
                        raw_data={"error": str(e)},
                    ))

    except ClientError as e:
        findings.append(Finding(
            id=str(uuid4()),
            title=f"Failed to check GuardDuty status in {region}",
            severity=Severity.INFO,
            resource_type="AWS::GuardDuty::Detector",
            resource_id=f"guardduty-{region}",
            account_id=account_id,
            region=region,
            provider="aws",
            description=f"Could not list GuardDuty detectors: {e}",
            remediation="Ensure the scanning role has guardduty:ListDetectors permission.",
            check_id="guardduty-enabled",
            raw_data={"error": str(e)},
        ))

    return findings


def check_guardduty_findings(
    guardduty_client, account_id: str, region: str, severity_threshold: float = 7.0
) -> list[Finding]:
    """Check for high-severity GuardDuty findings.

    Args:
        guardduty_client: boto3 GuardDuty client for the region.
        account_id: AWS account ID.
        region: AWS region being checked.
        severity_threshold: Minimum severity to report (0-10 scale).

    Returns:
        List of findings for unresolved high-severity GuardDuty findings.
    """
    findings = []

    try:
        response = guardduty_client.list_detectors()
        detector_ids = response.get("DetectorIds", [])

        for detector_id in detector_ids:
            # Get high-severity findings
            try:
                findings_response = guardduty_client.list_findings(
                    DetectorId=detector_id,
                    FindingCriteria={
                        "Criterion": {
                            "severity": {
                                "Gte": int(severity_threshold),
                            },
                            "service.archived": {
                                "Eq": ["false"],
                            },
                        }
                    },
                    MaxResults=50,
                )

                finding_ids = findings_response.get("FindingIds", [])

                if finding_ids:
                    # Get finding details
                    details_response = guardduty_client.get_findings(
                        DetectorId=detector_id,
                        FindingIds=finding_ids,
                    )

                    gd_findings = details_response.get("Findings", [])

                    for gd_finding in gd_findings:
                        gd_id = gd_finding.get("Id", "")
                        gd_type = gd_finding.get("Type", "")
                        gd_severity = gd_finding.get("Severity", 0)
                        gd_title = gd_finding.get("Title", "Unknown finding")
                        gd_description = gd_finding.get("Description", "")

                        # Map GuardDuty severity (0-10) to our severity
                        if gd_severity >= 8:
                            severity = Severity.CRITICAL
                        elif gd_severity >= 7:
                            severity = Severity.HIGH
                        else:
                            severity = Severity.MEDIUM

                        findings.append(Finding(
                            id=str(uuid4()),
                            title=f"GuardDuty: {gd_title}",
                            severity=severity,
                            resource_type="AWS::GuardDuty::Finding",
                            resource_id=gd_id,
                            account_id=account_id,
                            region=region,
                            provider="aws",
                            description=(
                                f"GuardDuty finding type: {gd_type}\n"
                                f"Severity: {gd_severity}/10\n\n"
                                f"{gd_description}"
                            ),
                            remediation=(
                                f"Investigate this GuardDuty finding:\n"
                                f"1. Review in GuardDuty console: {region}\n"
                                f"2. Analyze the affected resources\n"
                                f"3. Take remediation action based on finding type\n"
                                f"4. Archive finding after resolution"
                            ),
                            check_id="guardduty-high-severity-finding",
                            raw_data=gd_finding,
                        ))

            except ClientError as e:
                findings.append(Finding(
                    id=str(uuid4()),
                    title=f"Failed to list GuardDuty findings in {region}",
                    severity=Severity.INFO,
                    resource_type="AWS::GuardDuty::Detector",
                    resource_id=detector_id,
                    account_id=account_id,
                    region=region,
                    provider="aws",
                    description=f"Could not list findings: {e}",
                    remediation="Ensure the scanning role has guardduty:ListFindings permission.",
                    check_id="guardduty-high-severity-finding",
                    raw_data={"error": str(e)},
                ))

    except ClientError:
        # No detectors - already reported by check_guardduty_enabled
        pass

    return findings


def run_all_guardduty_checks(
    guardduty_client, account_id: str, region: str
) -> list[Finding]:
    """Run all GuardDuty security checks.

    Args:
        guardduty_client: boto3 GuardDuty client for the region.
        account_id: AWS account ID.
        region: AWS region being checked.

    Returns:
        Combined list of all GuardDuty findings.
    """
    findings = []
    findings.extend(check_guardduty_enabled(guardduty_client, account_id, region))
    findings.extend(check_guardduty_findings(guardduty_client, account_id, region))
    return findings
