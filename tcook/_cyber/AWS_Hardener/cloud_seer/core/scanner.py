"""Abstract scanner protocol for cloud providers."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from .models import Finding, AccountSummary


@runtime_checkable
class CloudScanner(Protocol):
    """Protocol for cloud provider scanners."""

    provider: str

    def scan(self, account_id: str, regions: list[str] | None = None) -> list[Finding]:
        """Run all security checks for an account."""
        ...

    def get_account_summary(self, account_id: str) -> AccountSummary:
        """Get summary information for an account."""
        ...


class BaseScanner(ABC):
    """Base class for cloud provider scanners with common functionality."""

    provider: str = "unknown"

    def __init__(self, checks: list[str] | None = None):
        """Initialize scanner with optional check filter.

        Args:
            checks: List of check IDs to run. If None, run all checks.
        """
        self.enabled_checks = checks
        self._findings: list[Finding] = []

    @abstractmethod
    def scan(self, account_id: str, regions: list[str] | None = None) -> list[Finding]:
        """Run all enabled security checks for an account.

        Args:
            account_id: The cloud account ID to scan.
            regions: Optional list of regions to scan. If None, scan all regions.

        Returns:
            List of security findings.
        """
        pass

    @abstractmethod
    def get_account_summary(self, account_id: str) -> AccountSummary:
        """Get summary information for an account.

        Args:
            account_id: The cloud account ID.

        Returns:
            AccountSummary with metadata about the account.
        """
        pass

    def is_check_enabled(self, check_id: str) -> bool:
        """Check if a specific check is enabled.

        Args:
            check_id: The check identifier (e.g., "iam", "cloudtrail").

        Returns:
            True if the check should run.
        """
        if self.enabled_checks is None:
            return True
        return check_id in self.enabled_checks

    @property
    def available_checks(self) -> list[str]:
        """List of available check IDs for this scanner."""
        return []
