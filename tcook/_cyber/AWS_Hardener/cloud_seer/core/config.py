"""Configuration management for multi-account scanning."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AccountConfig:
    """Configuration for a single cloud account."""
    id: str
    name: str
    provider: str = "aws"
    role_name: str | None = None  # Override default role
    regions: list[str] | None = None  # Override default regions
    enabled: bool = True


@dataclass
class OrganizationsConfig:
    """Configuration for AWS Organizations auto-discovery."""
    enabled: bool = False
    exclude_ous: list[str] = field(default_factory=list)
    exclude_accounts: list[str] = field(default_factory=list)


@dataclass
class CloudSeerConfig:
    """Main configuration for cloud-seer."""
    # Default role to assume in target accounts
    default_role_name: str = "SecurityAuditRole"

    # Default regions to scan (None = all available)
    default_regions: list[str] | None = None

    # Explicitly configured accounts
    accounts: list[AccountConfig] = field(default_factory=list)

    # AWS Organizations auto-discovery
    organizations: OrganizationsConfig = field(default_factory=OrganizationsConfig)

    # Output settings
    output_dir: str = "./reports"
    output_formats: list[str] = field(default_factory=lambda: ["terminal"])

    @classmethod
    def from_file(cls, path: str | Path) -> "CloudSeerConfig":
        """Load configuration from a YAML file.

        Args:
            path: Path to the configuration file.

        Returns:
            Parsed CloudSeerConfig instance.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CloudSeerConfig":
        """Create config from dictionary.

        Args:
            data: Configuration dictionary.

        Returns:
            CloudSeerConfig instance.
        """
        defaults = data.get("defaults", {})

        # Parse accounts
        accounts = []
        for acc in data.get("accounts", []):
            accounts.append(AccountConfig(
                id=acc["id"],
                name=acc.get("name", acc["id"]),
                provider=acc.get("provider", "aws"),
                role_name=acc.get("role_name"),
                regions=acc.get("regions"),
                enabled=acc.get("enabled", True),
            ))

        # Parse organizations config
        org_data = data.get("organizations", {})
        organizations = OrganizationsConfig(
            enabled=org_data.get("enabled", False),
            exclude_ous=org_data.get("exclude_ous", []),
            exclude_accounts=org_data.get("exclude_accounts", []),
        )

        return cls(
            default_role_name=defaults.get("role_name", "SecurityAuditRole"),
            default_regions=defaults.get("regions"),
            accounts=accounts,
            organizations=organizations,
            output_dir=data.get("output_dir", "./reports"),
            output_formats=data.get("output_formats", ["terminal"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for YAML serialization."""
        return {
            "defaults": {
                "role_name": self.default_role_name,
                "regions": self.default_regions,
            },
            "accounts": [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "provider": acc.provider,
                    "role_name": acc.role_name,
                    "regions": acc.regions,
                    "enabled": acc.enabled,
                }
                for acc in self.accounts
            ],
            "organizations": {
                "enabled": self.organizations.enabled,
                "exclude_ous": self.organizations.exclude_ous,
                "exclude_accounts": self.organizations.exclude_accounts,
            },
            "output_dir": self.output_dir,
            "output_formats": self.output_formats,
        }

    def save(self, path: str | Path) -> None:
        """Save configuration to a YAML file.

        Args:
            path: Path to save the configuration file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)


def generate_sample_config() -> str:
    """Generate a sample configuration file content."""
    return '''# cloud-seer configuration file
# See: https://github.com/example/cloud-seer for documentation

defaults:
  # IAM role to assume in each target account
  role_name: SecurityAuditRole

  # Regions to scan (null = all available regions)
  regions: null
  # regions:
  #   - us-east-1
  #   - us-west-2
  #   - eu-west-1

# Explicitly configured accounts
accounts:
  - id: "111111111111"
    name: "Production"
    # role_name: CustomAuditRole  # Override default role

  - id: "222222222222"
    name: "Development"

  - id: "333333333333"
    name: "Staging"
    enabled: false  # Skip this account

# AWS Organizations auto-discovery (alternative to explicit accounts)
organizations:
  enabled: false
  exclude_ous:
    - "ou-xxxx-sandbox"
  exclude_accounts:
    - "444444444444"  # Legacy account

# Output settings
output_dir: ./reports
output_formats:
  - terminal
  - json
  - html
'''
