"""AWS session management with assume-role support."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError


@dataclass
class AWSCredentials:
    """Temporary AWS credentials from AssumeRole."""
    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: Any  # datetime


class AWSSessionManager:
    """Manages AWS sessions with support for cross-account assume-role."""

    def __init__(
        self,
        default_role_name: str = "SecurityAuditRole",
        session_name: str = "cloud-seer-audit",
    ):
        """Initialize the session manager.

        Args:
            default_role_name: Default IAM role name to assume in target accounts.
            session_name: Session name for STS AssumeRole calls.
        """
        self.default_role_name = default_role_name
        self.session_name = session_name
        self._base_session = boto3.Session()
        self._assumed_sessions: dict[str, boto3.Session] = {}

    def get_current_account_id(self) -> str:
        """Get the account ID of the current credentials."""
        sts = self._base_session.client("sts")
        return sts.get_caller_identity()["Account"]

    def get_current_identity(self) -> dict[str, str]:
        """Get full identity information for current credentials."""
        sts = self._base_session.client("sts")
        identity = sts.get_caller_identity()
        return {
            "account_id": identity["Account"],
            "arn": identity["Arn"],
            "user_id": identity["UserId"],
        }

    def assume_role(
        self,
        account_id: str,
        role_name: str | None = None,
        duration_seconds: int = 3600,
    ) -> boto3.Session:
        """Assume a role in a target account and return a session.

        Args:
            account_id: Target AWS account ID.
            role_name: IAM role name to assume (uses default if None).
            duration_seconds: Duration of the temporary credentials.

        Returns:
            boto3.Session configured with assumed role credentials.

        Raises:
            ClientError: If the role cannot be assumed.
        """
        role_name = role_name or self.default_role_name
        cache_key = f"{account_id}:{role_name}"

        if cache_key in self._assumed_sessions:
            return self._assumed_sessions[cache_key]

        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

        sts = self._base_session.client("sts")

        try:
            response = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName=self.session_name,
                DurationSeconds=duration_seconds,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "AccessDenied":
                raise PermissionError(
                    f"Cannot assume role {role_arn}. "
                    f"Ensure the role exists and trusts this account."
                ) from e
            raise

        credentials = response["Credentials"]

        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        self._assumed_sessions[cache_key] = session
        return session

    def get_session(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
    ) -> boto3.Session:
        """Get a session for the specified account.

        If account_id is None or matches the current account, returns the base session.
        Otherwise, assumes the specified role in the target account.

        Args:
            account_id: Target account ID (None = current account).
            role_name: Role to assume (None = use default).

        Returns:
            boto3.Session for the target account.
        """
        if account_id is None:
            return self._base_session

        current_account = self.get_current_account_id()
        if account_id == current_account:
            return self._base_session

        return self.assume_role(account_id, role_name)

    def get_client(
        self,
        service_name: str,
        account_id: str | None = None,
        role_name: str | None = None,
        region_name: str | None = None,
    ):
        """Get a boto3 client for a service in the specified account.

        Args:
            service_name: AWS service name (e.g., "iam", "sts").
            account_id: Target account ID (None = current account).
            role_name: Role to assume (None = use default).
            region_name: AWS region (None = default region).

        Returns:
            boto3 client for the specified service.
        """
        session = self.get_session(account_id, role_name)
        return session.client(service_name, region_name=region_name)

    @lru_cache(maxsize=1)
    def get_available_regions(self, service_name: str = "ec2") -> list[str]:
        """Get list of available AWS regions.

        Args:
            service_name: Service to check regions for.

        Returns:
            List of region names.
        """
        session = self._base_session
        return session.get_available_regions(service_name)

    def get_enabled_regions(self, account_id: str | None = None) -> list[str]:
        """Get list of regions enabled in the account.

        Args:
            account_id: Target account ID (None = current account).

        Returns:
            List of enabled region names.
        """
        ec2 = self.get_client("ec2", account_id, region_name="us-east-1")

        try:
            response = ec2.describe_regions(AllRegions=False)
            return [r["RegionName"] for r in response["Regions"]]
        except ClientError:
            # Fall back to static list if describe_regions fails
            return self.get_available_regions()

    def clear_cache(self) -> None:
        """Clear cached sessions."""
        self._assumed_sessions.clear()
        self.get_available_regions.cache_clear()
