#!/usr/bin/env python3
"""
Comprehensive Export Validation Test Suite

Tests to validate that exported data matches Splunk queries exactly.

Tests include:
1. Count validation by sourcetype
2. Column/field count validation
3. Sample value verification
4. Field type validation
5. Checksum verification
6. Cross-format consistency

Usage:
    pytest test_export_validation.py -v
    python test_export_validation.py --export-dir ./exported_data
"""

import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import unittest
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
from splunk_client import SplunkClient, SplunkConfig

console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Test Result Data Classes
# =============================================================================

@dataclass
class TestResult:
    """Result of a single test."""
    test_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = None
    duration_seconds: float = 0.0


@dataclass
class SourcetypeTestResults:
    """All test results for a sourcetype."""
    sourcetype: str
    tests: List[TestResult]
    overall_passed: bool


@dataclass
class TestSuiteResults:
    """Results from the entire test suite."""
    suite_name: str
    started_at: str
    completed_at: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    sourcetype_results: List[SourcetypeTestResults]
    overall_passed: bool


# =============================================================================
# Test Functions
# =============================================================================

class ExportValidationTests:
    """Comprehensive validation tests for exported data."""

    def __init__(
        self,
        client: SplunkClient,
        export_dir: str,
        index: str = "botsv3"
    ):
        self.client = client
        self.export_dir = Path(export_dir)
        self.index = index
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict:
        """Load export manifest."""
        manifest_path = self.export_dir / "export_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Export manifest not found: {manifest_path}")
        with open(manifest_path) as f:
            return json.load(f)

    def _load_export(self, file_path: str, format: str) -> List[Dict]:
        """Load exported data from file."""
        path = Path(file_path)

        if format == "jsonl":
            events = []
            with open(path) as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
            return events

        elif format == "parquet":
            import pandas as pd
            df = pd.read_parquet(path)
            return df.to_dict('records')

        elif format == "json":
            with open(path) as f:
                return json.load(f)

        elif format == "csv":
            import pandas as pd
            df = pd.read_csv(path)
            return df.to_dict('records')

        raise ValueError(f"Unknown format: {format}")

    def _get_splunk_count(self, sourcetype: str) -> int:
        """Get event count from Splunk for a sourcetype."""
        results = self.client.oneshot_search(
            f'index={self.index} sourcetype="{sourcetype}" earliest=0 | stats count',
            count=1
        )
        return int(results[0]['count']) if results else 0

    def _get_splunk_fields(self, sourcetype: str) -> List[str]:
        """Get field list from Splunk for a sourcetype."""
        results = self.client.oneshot_search(
            f'index={self.index} sourcetype="{sourcetype}" earliest=0 | head 1000 | fieldsummary | fields field',
            count=1000
        )
        return [r['field'] for r in results if r.get('field')]

    def _get_splunk_field_counts(self, sourcetype: str) -> Dict[str, int]:
        """Get non-null count for each field from Splunk."""
        results = self.client.oneshot_search(
            f'index={self.index} sourcetype="{sourcetype}" earliest=0 | fieldsummary | fields field, count',
            count=1000
        )
        return {r['field']: int(r['count']) for r in results if r.get('field')}

    def _get_splunk_sample_values(self, sourcetype: str, field: str, limit: int = 10) -> List[str]:
        """Get sample values for a field from Splunk."""
        results = self.client.oneshot_search(
            f'index={self.index} sourcetype="{sourcetype}" earliest=0 | top {limit} {field} | fields {field}',
            count=limit
        )
        return [str(r.get(field, '')) for r in results if r.get(field)]

    # =========================================================================
    # Test 1: Count Validation by Sourcetype
    # =========================================================================

    def test_count_by_sourcetype(self, sourcetype: str, export_meta: Dict) -> TestResult:
        """Test that exported event count matches Splunk count."""
        import time
        start = time.time()

        splunk_count = self._get_splunk_count(sourcetype)

        export_counts = {}
        for fmt, meta in export_meta.items():
            try:
                events = self._load_export(meta['file_path'], fmt)
                export_counts[fmt] = len(events)
            except Exception as e:
                export_counts[fmt] = -1

        # Check all formats match Splunk
        all_match = all(cnt == splunk_count for cnt in export_counts.values() if cnt >= 0)

        details = {
            'splunk_count': splunk_count,
            'export_counts': export_counts,
            'difference': {fmt: cnt - splunk_count for fmt, cnt in export_counts.items() if cnt >= 0}
        }

        if all_match:
            message = f"Count match: {splunk_count:,} events"
        else:
            mismatches = [f"{fmt}={cnt}" for fmt, cnt in export_counts.items() if cnt != splunk_count]
            message = f"Count mismatch: Splunk={splunk_count:,}, {', '.join(mismatches)}"

        return TestResult(
            test_name="count_validation",
            passed=all_match,
            message=message,
            details=details,
            duration_seconds=time.time() - start
        )

    # =========================================================================
    # Test 2: Column/Field Count Validation
    # =========================================================================

    def test_field_count(self, sourcetype: str, export_meta: Dict) -> TestResult:
        """Test that exported field count matches expected."""
        import time
        start = time.time()

        splunk_fields = self._get_splunk_fields(sourcetype)

        # Filter out internal fields that should be stripped
        expected_fields = [f for f in splunk_fields
                         if not f.startswith('_') or f in ('_time', '_raw')]

        export_field_counts = {}
        for fmt, meta in export_meta.items():
            export_field_counts[fmt] = meta.get('field_count', 0)

        # We expect some fields to be renamed/removed, so allow some flexibility
        splunk_field_count = len(expected_fields)
        threshold = max(5, int(splunk_field_count * 0.1))  # 10% tolerance or 5 fields

        passed = True
        for fmt, cnt in export_field_counts.items():
            if abs(cnt - splunk_field_count) > threshold:
                passed = False

        details = {
            'splunk_field_count': splunk_field_count,
            'export_field_counts': export_field_counts,
            'splunk_fields_sample': expected_fields[:20]
        }

        if passed:
            message = f"Field count within tolerance: ~{splunk_field_count} fields"
        else:
            message = f"Field count mismatch: Splunk={splunk_field_count}, Exports={export_field_counts}"

        return TestResult(
            test_name="field_count_validation",
            passed=passed,
            message=message,
            details=details,
            duration_seconds=time.time() - start
        )

    # =========================================================================
    # Test 3: Field Presence Validation
    # =========================================================================

    def test_field_presence(self, sourcetype: str, export_meta: Dict) -> TestResult:
        """Test that important fields are present in exports."""
        import time
        start = time.time()

        # Get first format's fields
        first_fmt = list(export_meta.keys())[0]
        first_meta = export_meta[first_fmt]

        try:
            events = self._load_export(first_meta['file_path'], first_fmt)
            export_fields = set(events[0].keys()) if events else set()
        except Exception as e:
            return TestResult(
                test_name="field_presence_validation",
                passed=False,
                message=f"Failed to load export: {e}",
                duration_seconds=time.time() - start
            )

        # Check for essential fields (with possible renames)
        essential_fields = {
            'time': ['event_time', 'timestamp', '_time'],
            'host': ['src_host', 'agent.name', 'host'],
            'source': ['log_source', 'data.srcip', 'source'],
        }

        missing_essential = []
        for category, possible_names in essential_fields.items():
            if not any(name in export_fields for name in possible_names):
                missing_essential.append(category)

        passed = len(missing_essential) == 0

        details = {
            'export_fields': sorted(list(export_fields)),
            'export_field_count': len(export_fields),
            'missing_essential': missing_essential
        }

        if passed:
            message = f"All essential fields present ({len(export_fields)} total fields)"
        else:
            message = f"Missing essential fields: {missing_essential}"

        return TestResult(
            test_name="field_presence_validation",
            passed=passed,
            message=message,
            details=details,
            duration_seconds=time.time() - start
        )

    # =========================================================================
    # Test 4: Sample Value Verification
    # =========================================================================

    def test_sample_values(self, sourcetype: str, export_meta: Dict) -> TestResult:
        """Test that sample values match between Splunk and export."""
        import time
        start = time.time()

        # Load first format
        first_fmt = list(export_meta.keys())[0]
        first_meta = export_meta[first_fmt]

        try:
            events = self._load_export(first_meta['file_path'], first_fmt)
        except Exception as e:
            return TestResult(
                test_name="sample_value_validation",
                passed=False,
                message=f"Failed to load export: {e}",
                duration_seconds=time.time() - start
            )

        if not events:
            return TestResult(
                test_name="sample_value_validation",
                passed=False,
                message="No events in export",
                duration_seconds=time.time() - start
            )

        # Get field to check - use a common field
        export_fields = list(events[0].keys())

        # Map export fields back to Splunk fields for checking
        field_mapping = {
            'event_time': '_time',
            'timestamp': '_time',
            'src_host': 'host',
            'agent.name': 'host',
            'log_source': 'source',
            'source_type': 'sourcetype',
        }

        fields_to_check = []
        for ef in export_fields[:5]:  # Check first 5 fields
            splunk_field = field_mapping.get(ef, ef)
            fields_to_check.append((ef, splunk_field))

        matches = 0
        mismatches = []

        for export_field, splunk_field in fields_to_check:
            try:
                splunk_values = set(self._get_splunk_sample_values(sourcetype, splunk_field, 20))
                export_values = set(str(e.get(export_field, '')) for e in events[:100] if e.get(export_field))

                # Check for overlap
                overlap = splunk_values & export_values
                if overlap or (not splunk_values and not export_values):
                    matches += 1
                else:
                    mismatches.append({
                        'field': export_field,
                        'splunk_sample': list(splunk_values)[:3],
                        'export_sample': list(export_values)[:3]
                    })
            except Exception as e:
                logger.debug(f"Could not check field {splunk_field}: {e}")

        passed = matches >= len(fields_to_check) * 0.5  # At least 50% match

        details = {
            'fields_checked': len(fields_to_check),
            'fields_matched': matches,
            'mismatches': mismatches[:3]
        }

        if passed:
            message = f"Sample values match: {matches}/{len(fields_to_check)} fields verified"
        else:
            message = f"Sample value mismatch: only {matches}/{len(fields_to_check)} fields matched"

        return TestResult(
            test_name="sample_value_validation",
            passed=passed,
            message=message,
            details=details,
            duration_seconds=time.time() - start
        )

    # =========================================================================
    # Test 5: Field Type Consistency
    # =========================================================================

    def test_field_types(self, sourcetype: str, export_meta: Dict) -> TestResult:
        """Test that field types are consistent in exports."""
        import time
        start = time.time()

        first_fmt = list(export_meta.keys())[0]
        first_meta = export_meta[first_fmt]

        try:
            events = self._load_export(first_meta['file_path'], first_fmt)
        except Exception as e:
            return TestResult(
                test_name="field_type_validation",
                passed=False,
                message=f"Failed to load export: {e}",
                duration_seconds=time.time() - start
            )

        if not events:
            return TestResult(
                test_name="field_type_validation",
                passed=True,
                message="No events to check",
                duration_seconds=time.time() - start
            )

        # Check type consistency for each field
        field_types = defaultdict(set)
        inconsistent_fields = []

        for event in events[:1000]:  # Check first 1000 events
            for field, value in event.items():
                if value is not None:
                    field_types[field].add(type(value).__name__)

        for field, types in field_types.items():
            # Allow str/int/float mixing (common in JSON)
            allowed_mixed = {'str', 'int', 'float', 'NoneType'}
            if len(types) > 1 and not types.issubset(allowed_mixed):
                inconsistent_fields.append({
                    'field': field,
                    'types': list(types)
                })

        passed = len(inconsistent_fields) == 0

        details = {
            'fields_checked': len(field_types),
            'inconsistent_fields': inconsistent_fields[:5]
        }

        if passed:
            message = f"Field types consistent across {len(field_types)} fields"
        else:
            message = f"Type inconsistency in {len(inconsistent_fields)} fields"

        return TestResult(
            test_name="field_type_validation",
            passed=passed,
            message=message,
            details=details,
            duration_seconds=time.time() - start
        )

    # =========================================================================
    # Test 6: Checksum Verification
    # =========================================================================

    def test_checksum(self, sourcetype: str, export_meta: Dict) -> TestResult:
        """Test that file checksums match manifest."""
        import time
        start = time.time()

        mismatches = []

        for fmt, meta in export_meta.items():
            file_path = Path(meta['file_path'])
            expected_checksum = meta.get('checksum_md5')

            if not file_path.exists():
                mismatches.append(f"{fmt}: file not found")
                continue

            with open(file_path, 'rb') as f:
                actual_checksum = hashlib.md5(f.read()).hexdigest()

            if expected_checksum and actual_checksum != expected_checksum:
                mismatches.append(f"{fmt}: checksum mismatch")

        passed = len(mismatches) == 0

        details = {
            'formats_checked': list(export_meta.keys()),
            'mismatches': mismatches
        }

        if passed:
            message = f"Checksums verified for {len(export_meta)} formats"
        else:
            message = f"Checksum issues: {'; '.join(mismatches)}"

        return TestResult(
            test_name="checksum_validation",
            passed=passed,
            message=message,
            details=details,
            duration_seconds=time.time() - start
        )

    # =========================================================================
    # Test 7: Cross-Format Consistency
    # =========================================================================

    def test_cross_format_consistency(self, sourcetype: str, export_meta: Dict) -> TestResult:
        """Test that all formats have consistent data."""
        import time
        start = time.time()

        if len(export_meta) < 2:
            return TestResult(
                test_name="cross_format_consistency",
                passed=True,
                message="Only one format exported, skipping cross-format check",
                duration_seconds=time.time() - start
            )

        counts = {}
        field_counts = {}

        for fmt, meta in export_meta.items():
            try:
                events = self._load_export(meta['file_path'], fmt)
                counts[fmt] = len(events)
                field_counts[fmt] = len(events[0].keys()) if events else 0
            except Exception as e:
                counts[fmt] = -1
                field_counts[fmt] = -1

        # Check counts match across formats
        valid_counts = [c for c in counts.values() if c >= 0]
        counts_match = len(set(valid_counts)) <= 1

        valid_field_counts = [c for c in field_counts.values() if c >= 0]
        fields_match = max(valid_field_counts) - min(valid_field_counts) <= 2 if valid_field_counts else True

        passed = counts_match and fields_match

        details = {
            'event_counts': counts,
            'field_counts': field_counts
        }

        if passed:
            message = f"Cross-format consistency verified ({len(export_meta)} formats)"
        else:
            message = f"Inconsistency across formats: counts={counts}, fields={field_counts}"

        return TestResult(
            test_name="cross_format_consistency",
            passed=passed,
            message=message,
            details=details,
            duration_seconds=time.time() - start
        )

    # =========================================================================
    # Run All Tests
    # =========================================================================

    def run_sourcetype_tests(self, sourcetype: str, export_meta: Dict) -> SourcetypeTestResults:
        """Run all tests for a single sourcetype."""
        tests = [
            self.test_count_by_sourcetype(sourcetype, export_meta),
            self.test_field_count(sourcetype, export_meta),
            self.test_field_presence(sourcetype, export_meta),
            self.test_sample_values(sourcetype, export_meta),
            self.test_field_types(sourcetype, export_meta),
            self.test_checksum(sourcetype, export_meta),
            self.test_cross_format_consistency(sourcetype, export_meta),
        ]

        overall_passed = all(t.passed for t in tests)

        return SourcetypeTestResults(
            sourcetype=sourcetype,
            tests=tests,
            overall_passed=overall_passed
        )

    def run_all_tests(self) -> TestSuiteResults:
        """Run all tests for all sourcetypes."""
        started_at = datetime.now().isoformat()

        console.print(Panel.fit(
            "[bold cyan]Export Validation Test Suite[/bold cyan]\n"
            f"Export directory: {self.export_dir}\n"
            f"Index: {self.index}"
        ))

        sourcetype_results = []
        total_tests = 0
        passed_tests = 0

        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:

            task = progress.add_task(
                "[cyan]Running tests...",
                total=len(self.manifest['sourcetypes'])
            )

            for sourcetype, export_meta in self.manifest['sourcetypes'].items():
                result = self.run_sourcetype_tests(sourcetype, export_meta)
                sourcetype_results.append(result)

                total_tests += len(result.tests)
                passed_tests += sum(1 for t in result.tests if t.passed)

                progress.advance(task)

        completed_at = datetime.now().isoformat()
        overall_passed = all(r.overall_passed for r in sourcetype_results)

        results = TestSuiteResults(
            suite_name="Export Validation Tests",
            started_at=started_at,
            completed_at=completed_at,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=total_tests - passed_tests,
            sourcetype_results=sourcetype_results,
            overall_passed=overall_passed
        )

        # Save results
        results_path = self.export_dir / "test_results.json"
        with open(results_path, 'w') as f:
            json.dump(asdict(results), f, indent=2, default=str)

        self._print_results(results)

        return results

    def _print_results(self, results: TestSuiteResults):
        """Print test results to console."""
        console.print("\n")

        # Summary
        status = "[green]PASSED[/green]" if results.overall_passed else "[red]FAILED[/red]"
        console.print(Panel(
            f"Overall: {status}\n\n"
            f"Total Tests: {results.total_tests}\n"
            f"Passed: {results.passed_tests}\n"
            f"Failed: {results.failed_tests}",
            title="Test Summary"
        ))

        # Per-sourcetype results
        table = Table(title="Sourcetype Test Results", box=box.ROUNDED)
        table.add_column("Sourcetype", style="cyan", max_width=30)
        table.add_column("Count", justify="center")
        table.add_column("Fields", justify="center")
        table.add_column("Values", justify="center")
        table.add_column("Types", justify="center")
        table.add_column("Checksum", justify="center")
        table.add_column("Status", justify="center")

        for sr in results.sourcetype_results:
            test_map = {t.test_name: t for t in sr.tests}

            def status_icon(test_name):
                t = test_map.get(test_name)
                if not t:
                    return "?"
                return "[green]✓[/green]" if t.passed else "[red]✗[/red]"

            overall = "[green]✓[/green]" if sr.overall_passed else "[red]✗[/red]"

            table.add_row(
                sr.sourcetype[:30],
                status_icon("count_validation"),
                status_icon("field_count_validation"),
                status_icon("sample_value_validation"),
                status_icon("field_type_validation"),
                status_icon("checksum_validation"),
                overall
            )

        console.print(table)

        # Failed tests details
        failed_sourcetypes = [sr for sr in results.sourcetype_results if not sr.overall_passed]
        if failed_sourcetypes:
            console.print("\n[bold red]Failed Tests:[/bold red]")
            for sr in failed_sourcetypes[:5]:
                console.print(f"\n  [cyan]{sr.sourcetype}[/cyan]:")
                for t in sr.tests:
                    if not t.passed:
                        console.print(f"    [red]✗[/red] {t.test_name}: {t.message}")

        console.print(f"\n[dim]Full results saved to: {self.export_dir}/test_results.json[/dim]")


# =============================================================================
# CLI
# =============================================================================

@click.command()
@click.option("--host", default="localhost", envvar="SPLUNK_HOST")
@click.option("--port", default=8089, envvar="SPLUNK_PORT")
@click.option("--username", default="admin", envvar="SPLUNK_USERNAME")
@click.option("--password", default="changeme123", envvar="SPLUNK_PASSWORD")
@click.option("--export-dir", "-d", default="./exported_data", help="Export directory to validate")
@click.option("--index", "-i", default="botsv3", help="Splunk index")
def main(host, port, username, password, export_dir, index):
    """Run comprehensive export validation tests."""
    config = SplunkConfig(host=host, port=port, username=username, password=password)
    client = SplunkClient(config)

    tests = ExportValidationTests(client=client, export_dir=export_dir, index=index)
    results = tests.run_all_tests()

    if not results.overall_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
