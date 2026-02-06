"""AWS Config security checks for AWS accounts."""

from uuid import uuid4

from botocore.exceptions import ClientError

from cloud_seer.core.models import Finding, Severity


# Security-relevant AWS Config managed rules
SECURITY_RULES = {
    "iam-user-mfa-enabled": {
        "description": "Checks whether MFA is enabled for all IAM users",
        "severity": Severity.HIGH,
    },
    "iam-root-access-key-check": {
        "description": "Checks whether the root user access key is available",
        "severity": Severity.CRITICAL,
    },
    "root-account-mfa-enabled": {
        "description": "Checks whether MFA is enabled for the root account",
        "severity": Severity.CRITICAL,
    },
    "access-keys-rotated": {
        "description": "Checks whether active access keys are rotated within 90 days",
        "severity": Severity.MEDIUM,
    },
    "cloudtrail-enabled": {
        "description": "Checks whether CloudTrail is enabled",
        "severity": Severity.HIGH,
    },
    "cloud-trail-cloud-watch-logs-enabled": {
        "description": "Checks whether CloudTrail logs are sent to CloudWatch",
        "severity": Severity.MEDIUM,
    },
    "cloud-trail-encryption-enabled": {
        "description": "Checks whether CloudTrail is configured to use SSE-KMS",
        "severity": Severity.MEDIUM,
    },
    "guardduty-enabled-centralized": {
        "description": "Checks whether GuardDuty is enabled",
        "severity": Severity.HIGH,
    },
    "s3-bucket-public-read-prohibited": {
        "description": "Checks that S3 buckets do not allow public read access",
        "severity": Severity.HIGH,
    },
    "s3-bucket-public-write-prohibited": {
        "description": "Checks that S3 buckets do not allow public write access",
        "severity": Severity.CRITICAL,
    },
    "s3-bucket-ssl-requests-only": {
        "description": "Checks whether S3 bucket policy requires SSL",
        "severity": Severity.MEDIUM,
    },
    "encrypted-volumes": {
        "description": "Checks whether EBS volumes are encrypted",
        "severity": Severity.MEDIUM,
    },
    "rds-instance-public-access-check": {
        "description": "Checks whether RDS instances are publicly accessible",
        "severity": Severity.HIGH,
    },
    "rds-storage-encrypted": {
        "description": "Checks whether RDS instances have storage encryption enabled",
        "severity": Severity.MEDIUM,
    },
    "restricted-ssh": {
        "description": "Checks whether security groups allow unrestricted SSH",
        "severity": Severity.HIGH,
    },
    "vpc-flow-logs-enabled": {
        "description": "Checks whether VPC flow logs are enabled",
        "severity": Severity.MEDIUM,
    },
}


def check_config_recorder_enabled(
    config_client, account_id: str, region: str
) -> list[Finding]:
    """Check if AWS Config recorder is enabled.

    Args:
        config_client: boto3 Config client for the region.
        account_id: AWS account ID.
        region: AWS region being checked.

    Returns:
        List of findings for Config recorder issues.
    """
    findings = []

    try:
        response = config_client.describe_configuration_recorders()
        recorders = response.get("ConfigurationRecorders", [])

        if not recorders:
            findings.append(Finding(
                id=str(uuid4()),
                title=f"AWS Config not enabled in region {region}",
                severity=Severity.MEDIUM,
                resource_type="AWS::Config::ConfigurationRecorder",
                resource_id=f"config-{region}",
                account_id=account_id,
                region=region,
                provider="aws",
                description=(
                    f"AWS Config is not enabled in region {region}. Config provides "
                    f"resource inventory, configuration history, and compliance monitoring."
                ),
                remediation=(
                    f"Enable AWS Config in region {region}:\n"
                    f"1. Create a configuration recorder\n"
                    f"2. Create a delivery channel with S3 bucket\n"
                    f"3. Start the recorder"
                ),
                check_id="config-recorder-enabled",
                raw_data={"recorders": recorders, "region": region},
            ))
        else:
            # Check if recorder is running
            status_response = config_client.describe_configuration_recorder_status()
            statuses = status_response.get("ConfigurationRecordersStatus", [])

            for status in statuses:
                recorder_name = status.get("name", "")
                is_recording = status.get("recording", False)

                if not is_recording:
                    findings.append(Finding(
                        id=str(uuid4()),
                        title=f"AWS Config recorder stopped in region {region}",
                        severity=Severity.MEDIUM,
                        resource_type="AWS::Config::ConfigurationRecorder",
                        resource_id=recorder_name,
                        account_id=account_id,
                        region=region,
                        provider="aws",
                        description=(
                            f"The AWS Config recorder '{recorder_name}' exists but is not "
                            f"recording. Configuration changes are not being tracked."
                        ),
                        remediation=(
                            f"Start the AWS Config recorder:\n"
                            f"aws configservice start-configuration-recorder "
                            f"--configuration-recorder-name {recorder_name} --region {region}"
                        ),
                        check_id="config-recorder-enabled",
                        raw_data={"recorder_name": recorder_name, "status": status},
                    ))

    except ClientError as e:
        findings.append(Finding(
            id=str(uuid4()),
            title=f"Failed to check AWS Config status in {region}",
            severity=Severity.INFO,
            resource_type="AWS::Config::ConfigurationRecorder",
            resource_id=f"config-{region}",
            account_id=account_id,
            region=region,
            provider="aws",
            description=f"Could not describe configuration recorders: {e}",
            remediation="Ensure the scanning role has config:DescribeConfigurationRecorders permission.",
            check_id="config-recorder-enabled",
            raw_data={"error": str(e)},
        ))

    return findings


def check_config_rules_compliance(
    config_client, account_id: str, region: str
) -> list[Finding]:
    """Check AWS Config rules for non-compliant resources.

    Args:
        config_client: boto3 Config client for the region.
        account_id: AWS account ID.
        region: AWS region being checked.

    Returns:
        List of findings for non-compliant Config rules.
    """
    findings = []

    try:
        # Get compliance summary by rule
        response = config_client.describe_compliance_by_config_rule()
        compliance_results = response.get("ComplianceByConfigRules", [])

        for result in compliance_results:
            rule_name = result.get("ConfigRuleName", "")
            compliance = result.get("Compliance", {})
            compliance_type = compliance.get("ComplianceType", "")

            # Only report non-compliant rules
            if compliance_type != "NON_COMPLIANT":
                continue

            # Look up severity from our known rules
            rule_info = SECURITY_RULES.get(rule_name, {})
            severity = rule_info.get("severity", Severity.MEDIUM)
            description = rule_info.get(
                "description",
                f"AWS Config rule '{rule_name}' has non-compliant resources"
            )

            # Get non-compliant resource count
            try:
                details_response = config_client.get_compliance_details_by_config_rule(
                    ConfigRuleName=rule_name,
                    ComplianceTypes=["NON_COMPLIANT"],
                    Limit=10,
                )
                eval_results = details_response.get("EvaluationResults", [])
                non_compliant_count = len(eval_results)

                # Get sample resource IDs
                sample_resources = [
                    r.get("EvaluationResultIdentifier", {})
                    .get("EvaluationResultQualifier", {})
                    .get("ResourceId", "")
                    for r in eval_results[:5]
                ]
            except ClientError:
                non_compliant_count = 1
                sample_resources = []

            findings.append(Finding(
                id=str(uuid4()),
                title=f"Config rule '{rule_name}' non-compliant ({non_compliant_count} resources)",
                severity=severity,
                resource_type="AWS::Config::ConfigRule",
                resource_id=rule_name,
                account_id=account_id,
                region=region,
                provider="aws",
                description=(
                    f"{description}\n\n"
                    f"Non-compliant resources: {non_compliant_count}\n"
                    f"Sample resources: {', '.join(sample_resources) or 'N/A'}"
                ),
                remediation=(
                    f"Review and remediate non-compliant resources:\n"
                    f"1. View in AWS Config console → Rules → {rule_name}\n"
                    f"2. Review each non-compliant resource\n"
                    f"3. Apply remediation based on rule requirements"
                ),
                check_id="config-rule-compliance",
                raw_data={
                    "rule_name": rule_name,
                    "compliance_type": compliance_type,
                    "non_compliant_count": non_compliant_count,
                    "sample_resources": sample_resources,
                },
            ))

    except ClientError as e:
        # Config might not be enabled
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "NoSuchConfigurationRecorderException":
            # Already reported by check_config_recorder_enabled
            pass
        else:
            findings.append(Finding(
                id=str(uuid4()),
                title=f"Failed to check AWS Config rules in {region}",
                severity=Severity.INFO,
                resource_type="AWS::Config::ConfigRule",
                resource_id=f"config-rules-{region}",
                account_id=account_id,
                region=region,
                provider="aws",
                description=f"Could not describe compliance: {e}",
                remediation="Ensure the scanning role has config:DescribeComplianceByConfigRule permission.",
                check_id="config-rule-compliance",
                raw_data={"error": str(e)},
            ))

    return findings


def run_all_config_checks(
    config_client, account_id: str, region: str
) -> list[Finding]:
    """Run all AWS Config security checks.

    Args:
        config_client: boto3 Config client for the region.
        account_id: AWS account ID.
        region: AWS region being checked.

    Returns:
        Combined list of all AWS Config findings.
    """
    findings = []
    findings.extend(check_config_recorder_enabled(config_client, account_id, region))
    findings.extend(check_config_rules_compliance(config_client, account_id, region))
    return findings
