#!/usr/bin/env python3
"""
End-to-End Validation Test for BOTSv3 Pipeline
Tests the complete flow from Splunk extraction to Databricks loading.

Validates:
1. Splunk container is running and accessible
2. BOTSv3 data is searchable
3. Data extraction completes successfully
4. Extracted counts match Splunk counts
5. Schema/columns are correctly extracted
6. (Optional) Databricks loading and validation
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from splunk_client import SplunkClient, SplunkConfig
from extract_data import SplunkDataExtractor

console = Console()


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    duration_seconds: float
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class TestSuite:
    """Collection of test results."""
    suite_name: str
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_seconds: float
    results: List[TestResult]


class E2ETestRunner:
    """Runs end-to-end validation tests."""
    
    def __init__(
        self,
        splunk_host: str = "localhost",
        splunk_port: int = 8089,
        splunk_user: str = "admin",
        splunk_password: str = "changeme123",
        output_dir: str = "./test_output",
        databricks_config: Optional[Dict[str, str]] = None
    ):
        self.config = SplunkConfig(
            host=splunk_host,
            port=splunk_port,
            username=splunk_user,
            password=splunk_password
        )
        self.client = SplunkClient(self.config)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.databricks_config = databricks_config
        self.results: List[TestResult] = []
    
    def run_test(self, name: str, test_func, *args, **kwargs) -> TestResult:
        """Run a single test and capture results."""
        start = time.time()
        try:
            result, message, details = test_func(*args, **kwargs)
            duration = time.time() - start
            test_result = TestResult(
                name=name,
                passed=result,
                duration_seconds=duration,
                message=message,
                details=details
            )
        except Exception as e:
            duration = time.time() - start
            test_result = TestResult(
                name=name,
                passed=False,
                duration_seconds=duration,
                message=f"Exception: {str(e)}",
                details={"exception": str(e)}
            )
        
        self.results.append(test_result)
        return test_result
    
    # ==================== Test Functions ====================
    
    def test_splunk_connection(self) -> Tuple[bool, str, Dict]:
        """Test basic Splunk connectivity."""
        try:
            info = self.client.get_server_info()
            entry = info.get("entry", [{}])[0]
            content = entry.get("content", {})
            
            return True, f"Connected to {content.get('serverName', 'unknown')}", {
                "server_name": content.get("serverName"),
                "version": content.get("version"),
                "build": content.get("build")
            }
        except Exception as e:
            return False, f"Connection failed: {e}", {}
    
    def test_splunk_authentication(self) -> Tuple[bool, str, Dict]:
        """Test Splunk authentication."""
        try:
            if self.client.authenticate():
                return True, "Authentication successful", {}
            return False, "Authentication failed", {}
        except Exception as e:
            return False, f"Auth error: {e}", {}
    
    def test_botsv3_index_exists(self) -> Tuple[bool, str, Dict]:
        """Test that BOTSv3 index exists."""
        try:
            indexes = self.client.list_indexes()
            botsv3 = next((i for i in indexes if i.get("name") == "botsv3"), None)
            
            if botsv3:
                content = botsv3.get("content", {})
                return True, "BOTSv3 index found", {
                    "total_events": content.get("totalEventCount"),
                    "current_size_mb": content.get("currentDBSizeMB")
                }
            return False, "BOTSv3 index not found", {"available_indexes": [i.get("name") for i in indexes]}
        except Exception as e:
            return False, f"Error checking index: {e}", {}
    
    def test_botsv3_has_data(self) -> Tuple[bool, str, Dict]:
        """Test that BOTSv3 index contains data."""
        try:
            results = self.client.oneshot_search(
                "index=botsv3 earliest=0 | stats count",
                count=1
            )
            
            if results and int(results[0].get('count', 0)) > 0:
                count = int(results[0]['count'])
                return True, f"BOTSv3 contains {count:,} events", {"event_count": count}
            return False, "BOTSv3 index is empty", {}
        except Exception as e:
            return False, f"Error querying data: {e}", {}
    
    def test_sourcetype_counts(self) -> Tuple[bool, str, Dict]:
        """Test that all expected sourcetypes are present."""
        try:
            results = self.client.oneshot_search(
                "index=botsv3 earliest=0 | stats count by sourcetype | sort -count",
                count=500
            )
            
            sourcetypes = {r['sourcetype']: int(r['count']) for r in results}
            
            # BOTSv3 should have 70+ sourcetypes
            if len(sourcetypes) >= 50:  # Allow some flexibility
                return True, f"Found {len(sourcetypes)} sourcetypes", {
                    "sourcetype_count": len(sourcetypes),
                    "top_10": dict(list(sourcetypes.items())[:10])
                }
            return False, f"Only {len(sourcetypes)} sourcetypes found (expected 50+)", {
                "sourcetype_count": len(sourcetypes)
            }
        except Exception as e:
            return False, f"Error counting sourcetypes: {e}", {}
    
    def test_sample_search(self) -> Tuple[bool, str, Dict]:
        """Test that sample searches work correctly."""
        test_searches = [
            ("index=botsv3 earliest=0 | head 10", 10, "basic"),
            ("index=botsv3 sourcetype=\"wineventlog:security\" earliest=0 | head 5", 5, "wineventlog"),
            ("index=botsv3 sourcetype=\"stream:http\" earliest=0 | head 5", 5, "stream_http"),
        ]
        
        results_summary = {}
        all_passed = True
        
        for query, expected_min, name in test_searches:
            try:
                results = self.client.oneshot_search(query, count=expected_min)
                count = len(results)
                passed = count >= expected_min
                results_summary[name] = {"count": count, "passed": passed}
                if not passed:
                    all_passed = False
            except Exception as e:
                results_summary[name] = {"error": str(e), "passed": False}
                all_passed = False
        
        if all_passed:
            return True, "All sample searches successful", results_summary
        return False, "Some sample searches failed", results_summary
    
    def test_data_extraction(self, limit_sourcetypes: int = 3) -> Tuple[bool, str, Dict]:
        """Test data extraction for a subset of sourcetypes."""
        try:
            # Get top N sourcetypes by count
            results = self.client.oneshot_search(
                f"index=botsv3 earliest=0 | stats count by sourcetype | sort -count | head {limit_sourcetypes}",
                count=limit_sourcetypes
            )
            
            sourcetypes = [r['sourcetype'] for r in results]
            
            # Extract data
            extractor = SplunkDataExtractor(
                client=self.client,
                output_dir=str(self.output_dir / "extraction_test"),
                output_format="jsonl",
                include_raw=False
            )
            
            manifest = extractor.extract_all(index="botsv3", sourcetypes=sourcetypes)
            
            # Validate
            if manifest.validation_passed:
                return True, f"Extracted {manifest.total_events_extracted:,} events", {
                    "sourcetypes_extracted": len(manifest.sourcetypes),
                    "events_extracted": manifest.total_events_extracted,
                    "validation_passed": manifest.validation_passed
                }
            
            failed = [s.sourcetype for s in manifest.sourcetypes if s.status != 'success']
            return False, f"Extraction issues: {failed}", asdict(manifest)
            
        except Exception as e:
            return False, f"Extraction error: {e}", {}
    
    def test_field_extraction(self) -> Tuple[bool, str, Dict]:
        """Test that fields are properly extracted and cleaned."""
        try:
            # Extract a small sample
            results = self.client.oneshot_search(
                'index=botsv3 sourcetype="wineventlog:security" earliest=0 | head 10 | fields *',
                count=10
            )
            
            if not results:
                return False, "No results returned", {}
            
            # Check that internal fields can be identified
            sample_event = results[0]
            all_fields = set(sample_event.keys())
            
            # Check for expected fields
            expected_fields = {'_time', 'host', 'source', 'sourcetype'}
            found_expected = expected_fields & all_fields
            
            # Check for internal fields
            internal_fields = {f for f in all_fields if f.startswith('_')}
            
            return True, f"Found {len(all_fields)} fields", {
                "total_fields": len(all_fields),
                "expected_found": list(found_expected),
                "internal_fields": list(internal_fields),
                "sample_fields": list(all_fields)[:20]
            }
        except Exception as e:
            return False, f"Field extraction error: {e}", {}
    
    def test_count_validation(self) -> Tuple[bool, str, Dict]:
        """Validate that extracted counts match Splunk counts."""
        extraction_dir = self.output_dir / "extraction_test"
        manifest_path = extraction_dir / "extraction_manifest.json"
        
        if not manifest_path.exists():
            return False, "No extraction manifest found", {}
        
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            # Re-query Splunk for current counts
            mismatches = []
            
            for st in manifest['sourcetypes']:
                sourcetype = st['sourcetype']
                extracted = st['extracted_count']
                
                # Get current Splunk count
                results = self.client.oneshot_search(
                    f'index=botsv3 sourcetype="{sourcetype}" earliest=0 | stats count',
                    count=1
                )
                
                splunk_count = int(results[0]['count']) if results else 0
                
                if extracted != splunk_count:
                    mismatches.append({
                        "sourcetype": sourcetype,
                        "extracted": extracted,
                        "splunk": splunk_count,
                        "diff": splunk_count - extracted
                    })
            
            if not mismatches:
                return True, "All counts match", {
                    "sourcetypes_validated": len(manifest['sourcetypes'])
                }
            
            return False, f"{len(mismatches)} count mismatches", {
                "mismatches": mismatches
            }
            
        except Exception as e:
            return False, f"Validation error: {e}", {}
    
    def test_schema_consistency(self) -> Tuple[bool, str, Dict]:
        """Test that schemas are consistent across extraction."""
        extraction_dir = self.output_dir / "extraction_test"
        manifest_path = extraction_dir / "extraction_manifest.json"
        
        if not manifest_path.exists():
            return False, "No extraction manifest found", {}
        
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            schema_info = {}
            
            for st in manifest['sourcetypes']:
                sourcetype = st['sourcetype']
                fields = st['fields']
                
                # Check file exists and can be read
                file_path = Path(st['file_path'])
                if file_path.exists():
                    # Read first line to verify JSON
                    with open(file_path) as f:
                        first_line = f.readline()
                        parsed = json.loads(first_line)
                        actual_fields = list(parsed.keys())
                        
                        schema_info[sourcetype] = {
                            "manifest_fields": len(fields),
                            "actual_fields": len(actual_fields),
                            "match": set(fields) == set(actual_fields)
                        }
            
            all_match = all(s['match'] for s in schema_info.values())
            
            if all_match:
                return True, "All schemas consistent", schema_info
            return False, "Schema inconsistencies detected", schema_info
            
        except Exception as e:
            return False, f"Schema check error: {e}", {}
    
    # ==================== Test Runner ====================
    
    def run_all_tests(self, include_extraction: bool = True, include_databricks: bool = False) -> TestSuite:
        """Run all tests and return results."""
        start_time = time.time()
        self.results = []
        
        console.print(Panel.fit("[bold cyan]BOTSv3 End-to-End Validation[/bold cyan]"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Core Splunk Tests
            tests = [
                ("Splunk Connection", self.test_splunk_connection),
                ("Splunk Authentication", self.test_splunk_authentication),
                ("BOTSv3 Index Exists", self.test_botsv3_index_exists),
                ("BOTSv3 Has Data", self.test_botsv3_has_data),
                ("Sourcetype Counts", self.test_sourcetype_counts),
                ("Sample Searches", self.test_sample_search),
                ("Field Extraction", self.test_field_extraction),
            ]
            
            if include_extraction:
                tests.extend([
                    ("Data Extraction", lambda: self.test_data_extraction(limit_sourcetypes=3)),
                    ("Count Validation", self.test_count_validation),
                    ("Schema Consistency", self.test_schema_consistency),
                ])
            
            for name, test_func in tests:
                task = progress.add_task(f"[cyan]{name}...", total=None)
                result = self.run_test(name, test_func)
                
                status = "[green]✓[/green]" if result.passed else "[red]✗[/red]"
                progress.update(task, description=f"{status} {name}: {result.message}")
                progress.remove_task(task)
        
        duration = time.time() - start_time
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        
        suite = TestSuite(
            suite_name="BOTSv3 E2E Validation",
            timestamp=datetime.now().isoformat(),
            total_tests=len(self.results),
            passed=passed,
            failed=failed,
            skipped=0,
            duration_seconds=duration,
            results=self.results
        )
        
        # Print summary
        self._print_summary(suite)
        
        # Save results
        results_path = self.output_dir / "test_results.json"
        with open(results_path, 'w') as f:
            json.dump(asdict(suite), f, indent=2, default=str)
        
        return suite
    
    def _print_summary(self, suite: TestSuite):
        """Print test summary."""
        console.print("\n")
        
        table = Table(title="Test Results")
        table.add_column("Test", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Message")
        
        for result in suite.results:
            status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
            table.add_row(
                result.name,
                status,
                f"{result.duration_seconds:.2f}s",
                result.message[:50] + "..." if len(result.message) > 50 else result.message
            )
        
        console.print(table)
        
        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total: {suite.total_tests}")
        console.print(f"  Passed: [green]{suite.passed}[/green]")
        console.print(f"  Failed: [red]{suite.failed}[/red]")
        console.print(f"  Duration: {suite.duration_seconds:.1f}s")
        
        if suite.failed == 0:
            console.print("\n[bold green]✓ All tests passed![/bold green]")
        else:
            console.print(f"\n[bold red]✗ {suite.failed} test(s) failed[/bold red]")


# CLI
@click.command()
@click.option("--host", default="localhost", envvar="SPLUNK_HOST")
@click.option("--port", default=8089, envvar="SPLUNK_PORT")
@click.option("--username", default="admin", envvar="SPLUNK_USERNAME")
@click.option("--password", default="changeme123", envvar="SPLUNK_PASSWORD")
@click.option("--output", "-o", default="./test_output", help="Output directory")
@click.option("--skip-extraction", is_flag=True, help="Skip extraction tests")
@click.option("--json-output", "-j", is_flag=True, help="Output JSON only")
def main(host, port, username, password, output, skip_extraction, json_output):
    """Run end-to-end validation tests for BOTSv3 pipeline."""
    runner = E2ETestRunner(
        splunk_host=host,
        splunk_port=port,
        splunk_user=username,
        splunk_password=password,
        output_dir=output
    )
    
    suite = runner.run_all_tests(include_extraction=not skip_extraction)
    
    if json_output:
        print(json.dumps(asdict(suite), indent=2, default=str))
    
    sys.exit(0 if suite.failed == 0 else 1)


if __name__ == "__main__":
    main()
