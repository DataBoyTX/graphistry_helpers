"""IAM security checks for AWS accounts."""

import base64
import csv
from datetime import datetime, timezone
from io import StringIO
from typing import Any
from uuid import uuid4

from botocore.exceptions import ClientError

from cloud_seer.core.models import Finding, Severity


def check_users_without_mfa(iam_client, account_id: str) -> list[Finding]:
    """Check for IAM users without MFA enabled.

    Args:
        iam_client: boto3 IAM client.
        account_id: AWS account ID.

    Returns:
        List of findings for users without MFA.
    """
    findings = []

    try:
        # Generate and get credential report
        iam_client.generate_credential_report()

        # Wait for report (may need retries)
        import time
        for _ in range(10):
            try:
                response = iam_client.get_credential_report()
                break
            except ClientError as e:
                if e.response["Error"]["Code"] == "ReportNotPresent":
                    time.sleep(1)
                    continue
                raise
        else:
            return findings

        # Parse CSV report
        report_content = base64.b64decode(response["Content"]).decode("utf-8")
        reader = csv.DictReader(StringIO(report_content))

        for row in reader:
            username = row["user"]

            # Skip root account (handled separately)
            if username == "<root_account>":
                continue

            # Check if user has password but no MFA
            has_password = row.get("password_enabled", "false") == "true"
            has_mfa = row.get("mfa_active", "false") == "true"

            if has_password and not has_mfa:
                findings.append(Finding(
                    id=str(uuid4()),
                    title=f"IAM user '{username}' has console access without MFA",
                    severity=Severity.HIGH,
                    resource_type="AWS::IAM::User",
                    resource_id=username,
                    account_id=account_id,
                    region="global",
                    provider="aws",
                    description=(
                        f"The IAM user '{username}' has password-based console access "
                        f"but does not have Multi-Factor Authentication (MFA) enabled. "
                        f"This increases the risk of account compromise."
                    ),
                    remediation=(
                        f"Enable MFA for user '{username}' via IAM console or CLI:\n"
                        f"1. IAM → Users → {username} → Security credentials → MFA\n"
                        f"2. Or enforce via 'DenyUnlessMFA' IAM policy"
                    ),
                    check_id="iam-user-mfa-enabled",
                    raw_data={"user": username, "credential_report_row": dict(row)},
                ))

    except ClientError as e:
        # Log error but don't fail entire scan
        findings.append(Finding(
            id=str(uuid4()),
            title="Failed to check IAM MFA status",
            severity=Severity.INFO,
            resource_type="AWS::IAM::CredentialReport",
            resource_id="credential-report",
            account_id=account_id,
            region="global",
            provider="aws",
            description=f"Could not generate credential report: {e}",
            remediation="Ensure the scanning role has iam:GenerateCredentialReport permission.",
            check_id="iam-user-mfa-enabled",
            raw_data={"error": str(e)},
        ))

    return findings


def check_root_account_mfa(iam_client, account_id: str) -> list[Finding]:
    """Check if root account has MFA enabled.

    Args:
        iam_client: boto3 IAM client.
        account_id: AWS account ID.

    Returns:
        List of findings if root MFA is not enabled.
    """
    findings = []

    try:
        response = iam_client.get_account_summary()
        summary = response["SummaryMap"]

        if summary.get("AccountMFAEnabled", 0) == 0:
            findings.append(Finding(
                id=str(uuid4()),
                title="Root account does not have MFA enabled",
                severity=Severity.CRITICAL,
                resource_type="AWS::IAM::RootAccount",
                resource_id="root",
                account_id=account_id,
                region="global",
                provider="aws",
                description=(
                    "The root account for this AWS account does not have MFA enabled. "
                    "The root account has unrestricted access to all resources and "
                    "should always be protected with MFA."
                ),
                remediation=(
                    "Enable MFA on the root account immediately:\n"
                    "1. Sign in as root user\n"
                    "2. Go to IAM → Dashboard → Security Status\n"
                    "3. Activate MFA on your root account\n"
                    "4. Use a hardware MFA device for maximum security"
                ),
                check_id="root-account-mfa-enabled",
                raw_data={"account_summary": summary},
            ))

    except ClientError as e:
        findings.append(Finding(
            id=str(uuid4()),
            title="Failed to check root account MFA status",
            severity=Severity.INFO,
            resource_type="AWS::IAM::RootAccount",
            resource_id="root",
            account_id=account_id,
            region="global",
            provider="aws",
            description=f"Could not retrieve account summary: {e}",
            remediation="Ensure the scanning role has iam:GetAccountSummary permission.",
            check_id="root-account-mfa-enabled",
            raw_data={"error": str(e)},
        ))

    return findings


def check_access_key_age(iam_client, account_id: str, max_age_days: int = 90) -> list[Finding]:
    """Check for IAM access keys older than threshold.

    Args:
        iam_client: boto3 IAM client.
        account_id: AWS account ID.
        max_age_days: Maximum allowed age for access keys.

    Returns:
        List of findings for old access keys.
    """
    findings = []
    now = datetime.now(timezone.utc)

    try:
        # List all users
        paginator = iam_client.get_paginator("list_users")

        for page in paginator.paginate():
            for user in page["Users"]:
                username = user["UserName"]

                # List access keys for this user
                keys_response = iam_client.list_access_keys(UserName=username)

                for key in keys_response.get("AccessKeyMetadata", []):
                    key_id = key["AccessKeyId"]
                    created = key["CreateDate"]
                    status = key["Status"]

                    if status != "Active":
                        continue

                    age_days = (now - created).days

                    if age_days > max_age_days:
                        findings.append(Finding(
                            id=str(uuid4()),
                            title=f"Access key for '{username}' is {age_days} days old",
                            severity=Severity.MEDIUM,
                            resource_type="AWS::IAM::AccessKey",
                            resource_id=key_id,
                            account_id=account_id,
                            region="global",
                            provider="aws",
                            description=(
                                f"The access key '{key_id}' for user '{username}' was created "
                                f"{age_days} days ago (threshold: {max_age_days} days). "
                                f"Long-lived credentials increase the blast radius of compromise."
                            ),
                            remediation=(
                                f"Rotate the access key for user '{username}':\n"
                                f"1. Create new key: aws iam create-access-key --user-name {username}\n"
                                f"2. Update applications using the key\n"
                                f"3. Deactivate old key: aws iam update-access-key --access-key-id {key_id} --status Inactive\n"
                                f"4. Delete old key after verification: aws iam delete-access-key --access-key-id {key_id}"
                            ),
                            check_id="iam-access-key-rotated",
                            raw_data={
                                "user": username,
                                "key_id": key_id,
                                "created": created.isoformat(),
                                "age_days": age_days,
                            },
                        ))

    except ClientError as e:
        findings.append(Finding(
            id=str(uuid4()),
            title="Failed to check access key age",
            severity=Severity.INFO,
            resource_type="AWS::IAM::AccessKey",
            resource_id="all-keys",
            account_id=account_id,
            region="global",
            provider="aws",
            description=f"Could not list access keys: {e}",
            remediation="Ensure the scanning role has iam:ListUsers and iam:ListAccessKeys permissions.",
            check_id="iam-access-key-rotated",
            raw_data={"error": str(e)},
        ))

    return findings


def check_unused_access_keys(iam_client, account_id: str, unused_days: int = 90) -> list[Finding]:
    """Check for access keys not used within threshold.

    Args:
        iam_client: boto3 IAM client.
        account_id: AWS account ID.
        unused_days: Days without use to flag as unused.

    Returns:
        List of findings for unused access keys.
    """
    findings = []
    now = datetime.now(timezone.utc)

    try:
        paginator = iam_client.get_paginator("list_users")

        for page in paginator.paginate():
            for user in page["Users"]:
                username = user["UserName"]

                keys_response = iam_client.list_access_keys(UserName=username)

                for key in keys_response.get("AccessKeyMetadata", []):
                    key_id = key["AccessKeyId"]
                    status = key["Status"]

                    if status != "Active":
                        continue

                    # Get last used info
                    last_used_response = iam_client.get_access_key_last_used(
                        AccessKeyId=key_id
                    )
                    last_used_info = last_used_response.get("AccessKeyLastUsed", {})
                    last_used_date = last_used_info.get("LastUsedDate")

                    if last_used_date is None:
                        # Never used
                        days_unused = (now - key["CreateDate"]).days
                        description = f"Access key '{key_id}' for user '{username}' has never been used"
                    else:
                        days_unused = (now - last_used_date).days
                        description = (
                            f"Access key '{key_id}' for user '{username}' has not been used "
                            f"for {days_unused} days"
                        )

                    if days_unused > unused_days:
                        findings.append(Finding(
                            id=str(uuid4()),
                            title=f"Unused access key for '{username}' ({days_unused} days)",
                            severity=Severity.MEDIUM,
                            resource_type="AWS::IAM::AccessKey",
                            resource_id=key_id,
                            account_id=account_id,
                            region="global",
                            provider="aws",
                            description=(
                                f"{description}. Unused keys should be deactivated or deleted "
                                f"to reduce attack surface."
                            ),
                            remediation=(
                                f"Remove the unused access key:\n"
                                f"1. Verify the key is truly unused\n"
                                f"2. Deactivate: aws iam update-access-key --user-name {username} "
                                f"--access-key-id {key_id} --status Inactive\n"
                                f"3. After verification period, delete: "
                                f"aws iam delete-access-key --user-name {username} --access-key-id {key_id}"
                            ),
                            check_id="iam-access-key-unused",
                            raw_data={
                                "user": username,
                                "key_id": key_id,
                                "days_unused": days_unused,
                                "last_used": last_used_date.isoformat() if last_used_date else None,
                            },
                        ))

    except ClientError as e:
        findings.append(Finding(
            id=str(uuid4()),
            title="Failed to check access key usage",
            severity=Severity.INFO,
            resource_type="AWS::IAM::AccessKey",
            resource_id="all-keys",
            account_id=account_id,
            region="global",
            provider="aws",
            description=f"Could not check access key last used: {e}",
            remediation="Ensure the scanning role has iam:GetAccessKeyLastUsed permission.",
            check_id="iam-access-key-unused",
            raw_data={"error": str(e)},
        ))

    return findings


def check_recently_created_users(
    iam_client, account_id: str, days_threshold: int = 7
) -> list[Finding]:
    """Check for IAM users created recently (potential backdoor).

    Args:
        iam_client: boto3 IAM client.
        account_id: AWS account ID.
        days_threshold: Days to consider as "recent".

    Returns:
        List of findings for recently created users.
    """
    findings = []
    now = datetime.now(timezone.utc)

    try:
        paginator = iam_client.get_paginator("list_users")

        for page in paginator.paginate():
            for user in page["Users"]:
                username = user["UserName"]
                created = user["CreateDate"]
                age_days = (now - created).days

                if age_days <= days_threshold:
                    findings.append(Finding(
                        id=str(uuid4()),
                        title=f"IAM user '{username}' created {age_days} days ago",
                        severity=Severity.INFO,
                        resource_type="AWS::IAM::User",
                        resource_id=username,
                        account_id=account_id,
                        region="global",
                        provider="aws",
                        description=(
                            f"The IAM user '{username}' was created {age_days} days ago "
                            f"on {created.strftime('%Y-%m-%d %H:%M:%S UTC')}. "
                            f"Verify this user creation was authorized."
                        ),
                        remediation=(
                            f"Review user '{username}' creation:\n"
                            f"1. Check CloudTrail for CreateUser event\n"
                            f"2. Verify the creator's identity and authorization\n"
                            f"3. If unauthorized, delete user and investigate"
                        ),
                        check_id="iam-user-recent-creation",
                        raw_data={
                            "user": username,
                            "created": created.isoformat(),
                            "age_days": age_days,
                        },
                    ))

    except ClientError as e:
        findings.append(Finding(
            id=str(uuid4()),
            title="Failed to check recently created users",
            severity=Severity.INFO,
            resource_type="AWS::IAM::User",
            resource_id="all-users",
            account_id=account_id,
            region="global",
            provider="aws",
            description=f"Could not list users: {e}",
            remediation="Ensure the scanning role has iam:ListUsers permission.",
            check_id="iam-user-recent-creation",
            raw_data={"error": str(e)},
        ))

    return findings


def run_all_iam_checks(iam_client, account_id: str) -> list[Finding]:
    """Run all IAM security checks.

    Args:
        iam_client: boto3 IAM client.
        account_id: AWS account ID.

    Returns:
        Combined list of all IAM findings.
    """
    findings = []
    findings.extend(check_root_account_mfa(iam_client, account_id))
    findings.extend(check_users_without_mfa(iam_client, account_id))
    findings.extend(check_access_key_age(iam_client, account_id))
    findings.extend(check_unused_access_keys(iam_client, account_id))
    findings.extend(check_recently_created_users(iam_client, account_id))
    return findings
