"""CloudTrail security checks for AWS accounts."""

from uuid import uuid4

from botocore.exceptions import ClientError

from cloud_seer.core.models import Finding, Severity


def check_cloudtrail_enabled(
    cloudtrail_client, account_id: str, region: str
) -> list[Finding]:
    """Check if CloudTrail is enabled in the region.

    Args:
        cloudtrail_client: boto3 CloudTrail client for the region.
        account_id: AWS account ID.
        region: AWS region being checked.

    Returns:
        List of findings for CloudTrail issues.
    """
    findings = []

    try:
        response = cloudtrail_client.describe_trails()
        trails = response.get("trailList", [])

        # Check for multi-region trail or region-specific trail
        has_active_trail = False
        trail_details = []

        for trail in trails:
            trail_name = trail.get("Name", "")
            trail_arn = trail.get("TrailARN", "")
            is_multi_region = trail.get("IsMultiRegionTrail", False)
            home_region = trail.get("HomeRegion", "")

            # Check if this trail covers the current region
            if is_multi_region or home_region == region:
                # Verify trail is logging
                try:
                    status_response = cloudtrail_client.get_trail_status(Name=trail_arn)
                    is_logging = status_response.get("IsLogging", False)

                    if is_logging:
                        has_active_trail = True
                        trail_details.append({
                            "name": trail_name,
                            "arn": trail_arn,
                            "is_multi_region": is_multi_region,
                            "is_logging": is_logging,
                        })
                except ClientError:
                    # Can't get status, don't count as active
                    pass

        if not has_active_trail:
            findings.append(Finding(
                id=str(uuid4()),
                title=f"No active CloudTrail in region {region}",
                severity=Severity.HIGH,
                resource_type="AWS::CloudTrail::Trail",
                resource_id=f"cloudtrail-{region}",
                account_id=account_id,
                region=region,
                provider="aws",
                description=(
                    f"No active CloudTrail trail is logging API events in region {region}. "
                    f"Without CloudTrail, API activity cannot be audited for security "
                    f"incidents or compliance requirements."
                ),
                remediation=(
                    f"Enable CloudTrail in region {region}:\n"
                    f"1. Create a multi-region trail (recommended):\n"
                    f"   aws cloudtrail create-trail --name main-trail --s3-bucket-name <bucket> "
                    f"--is-multi-region-trail\n"
                    f"2. Start logging: aws cloudtrail start-logging --name main-trail"
                ),
                check_id="cloudtrail-enabled",
                raw_data={"trails": trails, "region": region},
            ))

    except ClientError as e:
        findings.append(Finding(
            id=str(uuid4()),
            title=f"Failed to check CloudTrail status in {region}",
            severity=Severity.INFO,
            resource_type="AWS::CloudTrail::Trail",
            resource_id=f"cloudtrail-{region}",
            account_id=account_id,
            region=region,
            provider="aws",
            description=f"Could not describe CloudTrail trails: {e}",
            remediation="Ensure the scanning role has cloudtrail:DescribeTrails permission.",
            check_id="cloudtrail-enabled",
            raw_data={"error": str(e)},
        ))

    return findings


def check_cloudtrail_log_validation(
    cloudtrail_client, account_id: str, region: str
) -> list[Finding]:
    """Check if CloudTrail log file validation is enabled.

    Args:
        cloudtrail_client: boto3 CloudTrail client for the region.
        account_id: AWS account ID.
        region: AWS region being checked.

    Returns:
        List of findings for trails without log validation.
    """
    findings = []

    try:
        response = cloudtrail_client.describe_trails()
        trails = response.get("trailList", [])

        for trail in trails:
            trail_name = trail.get("Name", "")
            trail_arn = trail.get("TrailARN", "")
            home_region = trail.get("HomeRegion", "")
            log_validation = trail.get("LogFileValidationEnabled", False)

            # Only check trails homed in this region
            if home_region != region:
                continue

            if not log_validation:
                findings.append(Finding(
                    id=str(uuid4()),
                    title=f"CloudTrail '{trail_name}' has log validation disabled",
                    severity=Severity.LOW,
                    resource_type="AWS::CloudTrail::Trail",
                    resource_id=trail_arn,
                    account_id=account_id,
                    region=region,
                    provider="aws",
                    description=(
                        f"The CloudTrail trail '{trail_name}' does not have log file "
                        f"validation enabled. Without validation, you cannot verify "
                        f"that log files have not been tampered with."
                    ),
                    remediation=(
                        f"Enable log file validation:\n"
                        f"aws cloudtrail update-trail --name {trail_name} "
                        f"--enable-log-file-validation"
                    ),
                    check_id="cloudtrail-log-validation",
                    raw_data={"trail": trail},
                ))

    except ClientError as e:
        findings.append(Finding(
            id=str(uuid4()),
            title=f"Failed to check CloudTrail log validation in {region}",
            severity=Severity.INFO,
            resource_type="AWS::CloudTrail::Trail",
            resource_id=f"cloudtrail-{region}",
            account_id=account_id,
            region=region,
            provider="aws",
            description=f"Could not describe CloudTrail trails: {e}",
            remediation="Ensure the scanning role has cloudtrail:DescribeTrails permission.",
            check_id="cloudtrail-log-validation",
            raw_data={"error": str(e)},
        ))

    return findings


def run_all_cloudtrail_checks(
    cloudtrail_client, account_id: str, region: str
) -> list[Finding]:
    """Run all CloudTrail security checks.

    Args:
        cloudtrail_client: boto3 CloudTrail client for the region.
        account_id: AWS account ID.
        region: AWS region being checked.

    Returns:
        Combined list of all CloudTrail findings.
    """
    findings = []
    findings.extend(check_cloudtrail_enabled(cloudtrail_client, account_id, region))
    findings.extend(check_cloudtrail_log_validation(cloudtrail_client, account_id, region))
    return findings
