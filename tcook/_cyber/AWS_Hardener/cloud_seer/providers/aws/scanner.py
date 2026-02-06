"""AWS security scanner implementation."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from botocore.exceptions import ClientError

from cloud_seer.core.models import AccountSummary, Finding, Severity
from cloud_seer.core.scanner import BaseScanner

from .checks.cloudtrail import run_all_cloudtrail_checks
from .checks.config import run_all_config_checks
from .checks.guardduty import run_all_guardduty_checks
from .checks.iam import run_all_iam_checks
from .session import AWSSessionManager


class AWSScanner(BaseScanner):
    """AWS security scanner that runs all security checks."""

    provider = "aws"

    # Available check categories
    CHECK_IAM = "iam"
    CHECK_CLOUDTRAIL = "cloudtrail"
    CHECK_GUARDDUTY = "guardduty"
    CHECK_CONFIG = "config"

    ALL_CHECKS = [CHECK_IAM, CHECK_CLOUDTRAIL, CHECK_GUARDDUTY, CHECK_CONFIG]

    def __init__(
        self,
        session_manager: AWSSessionManager | None = None,
        checks: list[str] | None = None,
        max_workers: int = 10,
        progress_callback: Callable[[str], None] | None = None,
    ):
        """Initialize the AWS scanner.

        Args:
            session_manager: Session manager for AWS credentials.
            checks: List of check categories to run (None = all).
            max_workers: Max threads for parallel region scanning.
            progress_callback: Optional callback for progress updates.
        """
        super().__init__(checks)
        self.session_manager = session_manager or AWSSessionManager()
        self.max_workers = max_workers
        self.progress_callback = progress_callback

    @property
    def available_checks(self) -> list[str]:
        """List of available check IDs."""
        return self.ALL_CHECKS.copy()

    def _log_progress(self, message: str) -> None:
        """Log progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(message)

    def scan(
        self,
        account_id: str | None = None,
        regions: list[str] | None = None,
        role_name: str | None = None,
    ) -> list[Finding]:
        """Run all enabled security checks for an AWS account.

        Args:
            account_id: AWS account ID to scan (None = current account).
            regions: List of regions to scan (None = all enabled regions).
            role_name: Role to assume (None = use default).

        Returns:
            List of security findings.
        """
        findings: list[Finding] = []

        # Determine account ID
        if account_id is None:
            account_id = self.session_manager.get_current_account_id()

        self._log_progress(f"Starting scan for account {account_id}")

        # Determine regions
        if regions is None:
            regions = self.session_manager.get_enabled_regions(account_id)

        self._log_progress(f"Scanning {len(regions)} regions")

        # Run global checks (IAM is global)
        if self.is_check_enabled(self.CHECK_IAM):
            self._log_progress("Running IAM checks (global)")
            iam_findings = self._run_iam_checks(account_id, role_name)
            findings.extend(iam_findings)
            self._log_progress(f"IAM checks complete: {len(iam_findings)} findings")

        # Run regional checks in parallel
        regional_findings = self._run_regional_checks(account_id, regions, role_name)
        findings.extend(regional_findings)

        self._log_progress(f"Scan complete: {len(findings)} total findings")
        return findings

    def _run_iam_checks(
        self, account_id: str, role_name: str | None
    ) -> list[Finding]:
        """Run IAM security checks.

        Args:
            account_id: AWS account ID.
            role_name: Role to assume.

        Returns:
            List of IAM findings.
        """
        try:
            iam_client = self.session_manager.get_client(
                "iam", account_id, role_name
            )
            return run_all_iam_checks(iam_client, account_id)
        except (ClientError, PermissionError) as e:
            return [Finding(
                id="iam-check-error",
                title="IAM checks failed",
                severity=Severity.INFO,
                resource_type="AWS::IAM",
                resource_id="iam",
                account_id=account_id,
                region="global",
                provider="aws",
                description=f"Could not run IAM checks: {e}",
                remediation="Ensure proper IAM permissions for the scanner role.",
                check_id="iam",
                raw_data={"error": str(e)},
            )]

    def _run_regional_checks(
        self,
        account_id: str,
        regions: list[str],
        role_name: str | None,
    ) -> list[Finding]:
        """Run regional security checks in parallel.

        Args:
            account_id: AWS account ID.
            regions: List of regions to scan.
            role_name: Role to assume.

        Returns:
            Combined list of regional findings.
        """
        findings: list[Finding] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._scan_region, account_id, region, role_name
                ): region
                for region in regions
            }

            for future in as_completed(futures):
                region = futures[future]
                try:
                    region_findings = future.result()
                    findings.extend(region_findings)
                    self._log_progress(
                        f"Region {region} complete: {len(region_findings)} findings"
                    )
                except Exception as e:
                    self._log_progress(f"Region {region} failed: {e}")
                    findings.append(Finding(
                        id=f"region-scan-error-{region}",
                        title=f"Region scan failed: {region}",
                        severity=Severity.INFO,
                        resource_type="AWS::Region",
                        resource_id=region,
                        account_id=account_id,
                        region=region,
                        provider="aws",
                        description=f"Could not scan region: {e}",
                        remediation="Check network connectivity and IAM permissions.",
                        check_id="region-scan",
                        raw_data={"error": str(e)},
                    ))

        return findings

    def _scan_region(
        self, account_id: str, region: str, role_name: str | None
    ) -> list[Finding]:
        """Scan a single region for security issues.

        Args:
            account_id: AWS account ID.
            region: AWS region to scan.
            role_name: Role to assume.

        Returns:
            List of findings for this region.
        """
        findings: list[Finding] = []

        # CloudTrail checks
        if self.is_check_enabled(self.CHECK_CLOUDTRAIL):
            try:
                cloudtrail_client = self.session_manager.get_client(
                    "cloudtrail", account_id, role_name, region
                )
                findings.extend(
                    run_all_cloudtrail_checks(cloudtrail_client, account_id, region)
                )
            except (ClientError, PermissionError) as e:
                findings.append(Finding(
                    id=f"cloudtrail-check-error-{region}",
                    title=f"CloudTrail checks failed in {region}",
                    severity=Severity.INFO,
                    resource_type="AWS::CloudTrail",
                    resource_id=f"cloudtrail-{region}",
                    account_id=account_id,
                    region=region,
                    provider="aws",
                    description=f"Could not run CloudTrail checks: {e}",
                    remediation="Ensure cloudtrail:* permissions for the scanner role.",
                    check_id="cloudtrail",
                    raw_data={"error": str(e)},
                ))

        # GuardDuty checks
        if self.is_check_enabled(self.CHECK_GUARDDUTY):
            try:
                guardduty_client = self.session_manager.get_client(
                    "guardduty", account_id, role_name, region
                )
                findings.extend(
                    run_all_guardduty_checks(guardduty_client, account_id, region)
                )
            except (ClientError, PermissionError) as e:
                findings.append(Finding(
                    id=f"guardduty-check-error-{region}",
                    title=f"GuardDuty checks failed in {region}",
                    severity=Severity.INFO,
                    resource_type="AWS::GuardDuty",
                    resource_id=f"guardduty-{region}",
                    account_id=account_id,
                    region=region,
                    provider="aws",
                    description=f"Could not run GuardDuty checks: {e}",
                    remediation="Ensure guardduty:* permissions for the scanner role.",
                    check_id="guardduty",
                    raw_data={"error": str(e)},
                ))

        # AWS Config checks
        if self.is_check_enabled(self.CHECK_CONFIG):
            try:
                config_client = self.session_manager.get_client(
                    "config", account_id, role_name, region
                )
                findings.extend(
                    run_all_config_checks(config_client, account_id, region)
                )
            except (ClientError, PermissionError) as e:
                findings.append(Finding(
                    id=f"config-check-error-{region}",
                    title=f"AWS Config checks failed in {region}",
                    severity=Severity.INFO,
                    resource_type="AWS::Config",
                    resource_id=f"config-{region}",
                    account_id=account_id,
                    region=region,
                    provider="aws",
                    description=f"Could not run Config checks: {e}",
                    remediation="Ensure config:* permissions for the scanner role.",
                    check_id="config",
                    raw_data={"error": str(e)},
                ))

        return findings

    def get_account_summary(
        self,
        account_id: str | None = None,
        role_name: str | None = None,
    ) -> AccountSummary:
        """Get summary information for an AWS account.

        Args:
            account_id: AWS account ID (None = current account).
            role_name: Role to assume.

        Returns:
            AccountSummary with metadata about the account.
        """
        if account_id is None:
            account_id = self.session_manager.get_current_account_id()

        # Try to get account alias
        account_name = account_id
        try:
            iam_client = self.session_manager.get_client("iam", account_id, role_name)
            aliases = iam_client.list_account_aliases().get("AccountAliases", [])
            if aliases:
                account_name = aliases[0]
        except ClientError:
            pass

        # Get enabled regions
        regions = self.session_manager.get_enabled_regions(account_id)

        return AccountSummary(
            account_id=account_id,
            account_name=account_name,
            provider="aws",
            regions_scanned=regions,
        )
