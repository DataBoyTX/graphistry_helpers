#!/usr/bin/env python3
"""
Splunk BOTSv3 Data Extraction Tool
Extracts all data from BOTSv3 index by sourcetype for Databricks loading.

Features:
- Extracts data by sourcetype to separate files
- Strips Splunk internal metadata fields
- Supports JSON and Parquet output formats
- Generates manifest with counts and schema info
- Validates extraction completeness
"""

import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import click
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path for splunk_client import
sys.path.insert(0, str(Path(__file__).parent))
from splunk_client import SplunkClient, SplunkConfig

console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Splunk internal fields to strip (not useful for Databricks analysis)
SPLUNK_INTERNAL_FIELDS = {
    # Index metadata
    '_bkt', '_cd', '_si', '_indextime', '_subsecond', '_serial',
    # Search metadata  
    '_kv', '_raw',  # _raw is kept optionally
    'splunk_server', 'splunk_server_group',
    # Parsing metadata
    'punct', 'linecount', 'timeendpos', 'timestartpos',
    # Event breaking
    '_eventtype_color', '_decoration',
    # Internal routing
    'index', 'splunk_source', 'tag', 'tag::eventtype',
    # Acceleration
    '_mkv_child', '_timediff',
}

# Fields to always keep (even if they start with underscore)
FIELDS_TO_KEEP = {
    '_time',  # Rename to 'timestamp' or 'event_time'
    '_raw',   # Optional - contains original log line
}

# Fields to rename for Databricks compatibility
FIELD_RENAMES = {
    '_time': 'event_time',
    'host': 'src_host',
    'source': 'log_source', 
    'sourcetype': 'source_type',
}


@dataclass
class SourcetypeMetadata:
    """Metadata for an extracted sourcetype."""
    sourcetype: str
    event_count: int
    extracted_count: int
    fields: List[str]
    file_path: str
    file_size_bytes: int
    checksum_md5: str
    extraction_time_seconds: float
    status: str  # 'success', 'partial', 'failed'
    error_message: Optional[str] = None


@dataclass 
class ExtractionManifest:
    """Manifest for the entire extraction."""
    extraction_id: str
    extraction_timestamp: str
    splunk_host: str
    index: str
    total_sourcetypes: int
    total_events_expected: int
    total_events_extracted: int
    output_format: str
    output_directory: str
    sourcetypes: List[SourcetypeMetadata]
    validation_passed: bool
    extraction_duration_seconds: float


class SplunkDataExtractor:
    """Extracts data from Splunk for Databricks loading."""
    
    def __init__(
        self, 
        client: SplunkClient,
        output_dir: str = "./extracted_data",
        output_format: str = "json",  # json, jsonl, parquet
        include_raw: bool = False,
        batch_size: int = 50000,
        strip_internal: bool = True,
        rename_fields: bool = True
    ):
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_format = output_format
        self.include_raw = include_raw
        self.batch_size = batch_size
        self.strip_internal = strip_internal
        self.rename_fields = rename_fields
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def get_sourcetype_counts(self, index: str = "botsv3") -> Dict[str, int]:
        """Get event counts for all sourcetypes in an index."""
        results = self.client.oneshot_search(
            f"index={index} earliest=0 | stats count by sourcetype | sort -count",
            count=1000
        )
        return {r['sourcetype']: int(r['count']) for r in results if r.get('sourcetype')}
    
    def get_sourcetype_fields(self, index: str, sourcetype: str, sample_size: int = 1000) -> List[str]:
        """Get all fields present in a sourcetype."""
        results = self.client.oneshot_search(
            f'index={index} sourcetype="{sourcetype}" earliest=0 | head {sample_size} | fieldsummary | fields field',
            count=1000
        )
        return [r['field'] for r in results if r.get('field')]
    
    def clean_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Clean an event by removing Splunk internal fields and renaming."""
        cleaned = {}
        
        for key, value in event.items():
            # Skip internal fields
            if self.strip_internal and key in SPLUNK_INTERNAL_FIELDS:
                continue
            
            # Skip _raw unless explicitly included
            if key == '_raw' and not self.include_raw:
                continue
                
            # Skip fields starting with underscore (except whitelist)
            if key.startswith('_') and key not in FIELDS_TO_KEEP:
                if self.strip_internal:
                    continue
            
            # Rename fields if enabled
            if self.rename_fields and key in FIELD_RENAMES:
                key = FIELD_RENAMES[key]
            
            # Handle multi-value fields (Splunk returns as lists sometimes)
            if isinstance(value, list) and len(value) == 1:
                value = value[0]
            
            cleaned[key] = value
        
        return cleaned
    
    def extract_sourcetype(
        self, 
        index: str, 
        sourcetype: str, 
        expected_count: int,
        progress: Optional[Progress] = None,
        task_id: Optional[TaskID] = None
    ) -> SourcetypeMetadata:
        """Extract all events for a single sourcetype."""
        start_time = time.time()
        events = []
        offset = 0
        errors = []
        
        # Sanitize sourcetype for filename
        safe_name = sourcetype.replace(':', '_').replace('/', '_').replace('\\', '_')
        
        try:
            while True:
                # Search for batch of events
                query = f'index={index} sourcetype="{sourcetype}" earliest=0 | fields *'
                
                batch = self.client.oneshot_search(
                    query,
                    count=self.batch_size,
                    earliest_time="0"
                )
                
                if not batch:
                    break
                
                # Clean events
                for event in batch:
                    cleaned = self.clean_event(event)
                    events.append(cleaned)
                
                if progress and task_id:
                    progress.update(task_id, completed=len(events))
                
                # Check if we got all events
                if len(batch) < self.batch_size:
                    break
                    
                offset += self.batch_size
                
                # Safety limit
                if offset > 10000000:
                    errors.append("Hit 10M event safety limit")
                    break
                    
        except Exception as e:
            errors.append(str(e))
            logger.error(f"Error extracting {sourcetype}: {e}")
        
        # Write to file
        if self.output_format == "jsonl":
            file_path = self.output_dir / f"{safe_name}.jsonl"
            with open(file_path, 'w') as f:
                for event in events:
                    f.write(json.dumps(event) + '\n')
        elif self.output_format == "parquet":
            try:
                import pandas as pd
                file_path = self.output_dir / f"{safe_name}.parquet"
                df = pd.DataFrame(events)
                df.to_parquet(file_path, index=False, compression='snappy')
            except ImportError:
                # Fallback to JSON if pandas not available
                file_path = self.output_dir / f"{safe_name}.json"
                with open(file_path, 'w') as f:
                    json.dump(events, f)
        else:  # json
            file_path = self.output_dir / f"{safe_name}.json"
            with open(file_path, 'w') as f:
                json.dump(events, f, indent=2)
        
        # Calculate checksum
        with open(file_path, 'rb') as f:
            checksum = hashlib.md5(f.read()).hexdigest()
        
        # Get field list from extracted data
        fields = set()
        for event in events[:100]:  # Sample first 100
            fields.update(event.keys())
        
        extraction_time = time.time() - start_time
        
        # Determine status
        if errors:
            status = 'failed' if not events else 'partial'
        elif len(events) == expected_count:
            status = 'success'
        elif len(events) > 0:
            status = 'partial'  # Got some but not all
        else:
            status = 'failed'
        
        return SourcetypeMetadata(
            sourcetype=sourcetype,
            event_count=expected_count,
            extracted_count=len(events),
            fields=sorted(list(fields)),
            file_path=str(file_path),
            file_size_bytes=file_path.stat().st_size,
            checksum_md5=checksum,
            extraction_time_seconds=extraction_time,
            status=status,
            error_message='; '.join(errors) if errors else None
        )
    
    def extract_all(
        self, 
        index: str = "botsv3",
        sourcetypes: Optional[List[str]] = None,
        parallel: int = 1
    ) -> ExtractionManifest:
        """Extract all sourcetypes from an index."""
        start_time = time.time()
        extraction_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        console.print(Panel.fit(f"[bold cyan]Splunk Data Extraction[/bold cyan]\nIndex: {index}"))
        
        # Get sourcetype counts
        console.print("\n[bold]Fetching sourcetype counts...[/bold]")
        sourcetype_counts = self.get_sourcetype_counts(index)
        
        if sourcetypes:
            # Filter to requested sourcetypes
            sourcetype_counts = {k: v for k, v in sourcetype_counts.items() if k in sourcetypes}
        
        total_events = sum(sourcetype_counts.values())
        console.print(f"Found {len(sourcetype_counts)} sourcetypes with {total_events:,} total events\n")
        
        # Extract each sourcetype
        results: List[SourcetypeMetadata] = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            overall_task = progress.add_task(
                "[cyan]Overall progress...", 
                total=len(sourcetype_counts)
            )
            
            for sourcetype, count in sourcetype_counts.items():
                task = progress.add_task(
                    f"[green]Extracting {sourcetype}...",
                    total=count
                )
                
                metadata = self.extract_sourcetype(
                    index=index,
                    sourcetype=sourcetype,
                    expected_count=count,
                    progress=progress,
                    task_id=task
                )
                results.append(metadata)
                
                progress.update(overall_task, advance=1)
                progress.remove_task(task)
        
        # Create manifest
        extraction_time = time.time() - start_time
        total_extracted = sum(r.extracted_count for r in results)
        validation_passed = total_extracted == total_events
        
        manifest = ExtractionManifest(
            extraction_id=extraction_id,
            extraction_timestamp=datetime.now().isoformat(),
            splunk_host=self.client.config.host,
            index=index,
            total_sourcetypes=len(results),
            total_events_expected=total_events,
            total_events_extracted=total_extracted,
            output_format=self.output_format,
            output_directory=str(self.output_dir),
            sourcetypes=results,
            validation_passed=validation_passed,
            extraction_duration_seconds=extraction_time
        )
        
        # Write manifest
        manifest_path = self.output_dir / "extraction_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(asdict(manifest), f, indent=2)
        
        # Print summary
        self._print_summary(manifest)
        
        return manifest
    
    def _print_summary(self, manifest: ExtractionManifest):
        """Print extraction summary."""
        console.print("\n")
        
        # Summary table
        table = Table(title="Extraction Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Extraction ID", manifest.extraction_id)
        table.add_row("Total Sourcetypes", str(manifest.total_sourcetypes))
        table.add_row("Events Expected", f"{manifest.total_events_expected:,}")
        table.add_row("Events Extracted", f"{manifest.total_events_extracted:,}")
        table.add_row("Output Format", manifest.output_format)
        table.add_row("Duration", f"{manifest.extraction_duration_seconds:.1f}s")
        table.add_row("Validation", "[green]PASSED[/green]" if manifest.validation_passed else "[red]FAILED[/red]")
        
        console.print(table)
        
        # Sourcetype details
        if any(s.status != 'success' for s in manifest.sourcetypes):
            console.print("\n[bold yellow]Issues Detected:[/bold yellow]")
            for st in manifest.sourcetypes:
                if st.status != 'success':
                    console.print(f"  • {st.sourcetype}: {st.status} ({st.extracted_count}/{st.event_count})")
                    if st.error_message:
                        console.print(f"    Error: {st.error_message}")
        
        console.print(f"\n[dim]Manifest saved to: {manifest.output_directory}/extraction_manifest.json[/dim]")


# CLI Commands
@click.group()
@click.option("--host", default="localhost", envvar="SPLUNK_HOST")
@click.option("--port", default=8089, envvar="SPLUNK_PORT")
@click.option("--username", default="admin", envvar="SPLUNK_USERNAME")
@click.option("--password", default="changeme123", envvar="SPLUNK_PASSWORD")
@click.pass_context
def cli(ctx, host, port, username, password):
    """Splunk BOTSv3 Data Extraction Tool."""
    ctx.ensure_object(dict)
    config = SplunkConfig(host=host, port=port, username=username, password=password)
    ctx.obj["client"] = SplunkClient(config)


@cli.command()
@click.option("--index", "-i", default="botsv3", help="Index to extract from")
@click.option("--output", "-o", default="./extracted_data", help="Output directory")
@click.option("--format", "-f", "output_format", type=click.Choice(["json", "jsonl", "parquet"]), default="jsonl")
@click.option("--include-raw", is_flag=True, help="Include _raw field (original log line)")
@click.option("--keep-internal", is_flag=True, help="Keep Splunk internal fields")
@click.option("--no-rename", is_flag=True, help="Don't rename fields for Databricks")
@click.option("--sourcetype", "-s", multiple=True, help="Specific sourcetype(s) to extract")
@click.pass_context
def extract(ctx, index, output, output_format, include_raw, keep_internal, no_rename, sourcetype):
    """Extract all data from Splunk index."""
    client = ctx.obj["client"]
    
    extractor = SplunkDataExtractor(
        client=client,
        output_dir=output,
        output_format=output_format,
        include_raw=include_raw,
        strip_internal=not keep_internal,
        rename_fields=not no_rename
    )
    
    sourcetypes = list(sourcetype) if sourcetype else None
    manifest = extractor.extract_all(index=index, sourcetypes=sourcetypes)
    
    if not manifest.validation_passed:
        sys.exit(1)


@cli.command()
@click.option("--index", "-i", default="botsv3", help="Index to analyze")
@click.pass_context
def analyze(ctx, index):
    """Analyze sourcetypes and fields in an index."""
    client = ctx.obj["client"]
    
    console.print(f"\n[bold]Analyzing index: {index}[/bold]\n")
    
    # Get sourcetype counts
    with console.status("Fetching sourcetype statistics..."):
        results = client.oneshot_search(
            f"index={index} earliest=0 | stats count by sourcetype | sort -count",
            count=1000
        )
    
    table = Table(title=f"Sourcetypes in {index}")
    table.add_column("Sourcetype", style="cyan")
    table.add_column("Event Count", style="green", justify="right")
    table.add_column("Percentage", style="yellow", justify="right")
    
    total = sum(int(r['count']) for r in results)
    
    for r in results:
        count = int(r['count'])
        pct = (count / total * 100) if total > 0 else 0
        table.add_row(r['sourcetype'], f"{count:,}", f"{pct:.1f}%")
    
    console.print(table)
    console.print(f"\n[bold]Total Events:[/bold] {total:,}")
    console.print(f"[bold]Total Sourcetypes:[/bold] {len(results)}")


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.pass_context
def validate(ctx, manifest_path):
    """Validate extraction against Splunk counts."""
    client = ctx.obj["client"]
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    console.print(f"\n[bold]Validating extraction: {manifest['extraction_id']}[/bold]\n")
    
    # Get current counts from Splunk
    with console.status("Fetching current Splunk counts..."):
        current_counts = {}
        results = client.oneshot_search(
            f"index={manifest['index']} earliest=0 | stats count by sourcetype",
            count=1000
        )
        current_counts = {r['sourcetype']: int(r['count']) for r in results}
    
    # Compare
    table = Table(title="Validation Results")
    table.add_column("Sourcetype", style="cyan")
    table.add_column("Splunk Count", justify="right")
    table.add_column("Extracted Count", justify="right")
    table.add_column("Match", justify="center")
    
    all_match = True
    for st in manifest['sourcetypes']:
        splunk_count = current_counts.get(st['sourcetype'], 0)
        extracted_count = st['extracted_count']
        match = splunk_count == extracted_count
        
        if not match:
            all_match = False
        
        table.add_row(
            st['sourcetype'],
            f"{splunk_count:,}",
            f"{extracted_count:,}",
            "[green]✓[/green]" if match else "[red]✗[/red]"
        )
    
    console.print(table)
    
    if all_match:
        console.print("\n[bold green]✓ All counts match![/bold green]")
    else:
        console.print("\n[bold red]✗ Count mismatches detected![/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
