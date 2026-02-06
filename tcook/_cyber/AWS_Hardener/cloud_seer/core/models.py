"""Core data models for cloud-seer security findings and reports."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(Enum):
    """Finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def weight(self) -> int:
        """Numeric weight for scoring calculations."""
        weights = {
            Severity.CRITICAL: 10,
            Severity.HIGH: 5,
            Severity.MEDIUM: 3,
            Severity.LOW: 1,
            Severity.INFO: 0,
        }
        return weights[self]

    @property
    def color(self) -> str:
        """Color for terminal/HTML output."""
        colors = {
            Severity.CRITICAL: "red",
            Severity.HIGH: "orange",
            Severity.MEDIUM: "yellow",
            Severity.LOW: "blue",
            Severity.INFO: "gray",
        }
        return colors[self]


@dataclass
class Finding:
    """A single security finding from a cloud audit."""
    id: str
    title: str
    severity: Severity
    resource_type: str
    resource_id: str
    account_id: str
    region: str
    provider: str  # aws, gcp, azure
    description: str
    remediation: str
    raw_data: dict = field(default_factory=dict)
    check_id: str = ""  # e.g., "iam-mfa-enabled"
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "account_id": self.account_id,
            "region": self.region,
            "provider": self.provider,
            "description": self.description,
            "remediation": self.remediation,
            "check_id": self.check_id,
            "timestamp": self.timestamp.isoformat(),
            "raw_data": self.raw_data,
        }


@dataclass
class KPI:
    """A key performance indicator for security posture."""
    name: str
    value: float
    target: float
    unit: str  # "percent", "count", "days"
    description: str = ""

    @property
    def is_met(self) -> bool:
        """Check if the KPI target is met."""
        if self.unit == "count":
            # For counts (like critical findings), lower is better
            return self.value <= self.target
        # For percentages, higher is better
        return self.value >= self.target

    @property
    def compliance_ratio(self) -> float:
        """Ratio of value to target (capped at 1.0 for percentages)."""
        if self.target == 0:
            return 1.0 if self.value == 0 else 0.0
        if self.unit == "count":
            # For counts, invert (0 findings = 100% compliance)
            return max(0, 1 - (self.value / max(self.target, 1)))
        return min(1.0, self.value / self.target)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "target": self.target,
            "unit": self.unit,
            "description": self.description,
            "is_met": self.is_met,
            "compliance_ratio": self.compliance_ratio,
        }


@dataclass
class AccountSummary:
    """Summary of findings for a single account."""
    account_id: str
    account_name: str
    provider: str
    regions_scanned: list[str] = field(default_factory=list)
    finding_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "provider": self.provider,
            "regions_scanned": self.regions_scanned,
            "finding_counts": self.finding_counts,
        }


@dataclass
class Report:
    """Complete audit report with findings and KPIs."""
    generated_at: datetime
    accounts: list[AccountSummary]
    findings: list[Finding]
    kpis: list[KPI]
    overall_score: float = 0.0
    scan_duration_seconds: float = 0.0

    @property
    def summary(self) -> dict[str, Any]:
        """Generate summary statistics."""
        severity_counts = {s.value: 0 for s in Severity}
        for finding in self.findings:
            severity_counts[finding.severity.value] += 1

        provider_counts: dict[str, int] = {}
        for finding in self.findings:
            provider_counts[finding.provider] = provider_counts.get(finding.provider, 0) + 1

        return {
            "total_findings": len(self.findings),
            "by_severity": severity_counts,
            "by_provider": provider_counts,
            "accounts_scanned": len(self.accounts),
            "overall_score": self.overall_score,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "scan_duration_seconds": self.scan_duration_seconds,
            "overall_score": self.overall_score,
            "summary": self.summary,
            "accounts": [a.to_dict() for a in self.accounts],
            "kpis": [k.to_dict() for k in self.kpis],
            "findings": [f.to_dict() for f in self.findings],
        }
