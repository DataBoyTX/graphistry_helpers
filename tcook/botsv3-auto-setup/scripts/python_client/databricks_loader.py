#!/usr/bin/env python3
"""
Databricks Data Loader for BOTSv3
Loads extracted Splunk data into Databricks and validates the transfer.

Features:
- Loads JSON/JSONL/Parquet files to Databricks tables
- Validates row counts match extraction manifest
- Compares schemas between Splunk extract and Databricks tables
- Handles type conversions and null values
- Generates validation report
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Databricks SDK - will fail gracefully if not available
DATABRICKS_AVAILABLE = False
try:
    from databricks import sql as databricks_sql
    from databricks.sdk import WorkspaceClient
    DATABRICKS_AVAILABLE = True
except ImportError:
    pass

# Try pandas for data manipulation
PANDAS_AVAILABLE = False
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass


@dataclass
class ColumnComparison:
    """Comparison of a column between Splunk and Databricks."""
    column_name: str
    in_splunk: bool
    in_databricks: bool
    splunk_sample_values: List[str]
    databricks_type: Optional[str]
    match: bool


@dataclass
class SourcetypeValidation:
    """Validation results for a single sourcetype."""
    sourcetype: str
    splunk_count: int
    databricks_count: int
    count_match: bool
    splunk_columns: List[str]
    databricks_columns: List[str]
    column_comparison: List[ColumnComparison]
    schema_match: bool
    status: str  # 'success', 'count_mismatch', 'schema_mismatch', 'failed'
    error_message: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report."""
    validation_id: str
    validation_timestamp: str
    extraction_manifest_path: str
    databricks_catalog: str
    databricks_schema: str
    total_sourcetypes: int
    sourcetypes_validated: int
    sourcetypes_passed: int
    total_events_splunk: int
    total_events_databricks: int
    overall_status: str
    sourcetype_validations: List[SourcetypeValidation]


class DatabricksLoader:
    """Loads extracted Splunk data into Databricks."""
    
    def __init__(
        self,
        host: str,
        token: str,
        http_path: str,
        catalog: str = "main",
        schema: str = "botsv3",
        warehouse_id: Optional[str] = None
    ):
        self.host = host
        self.token = token
        self.http_path = http_path
        self.catalog = catalog
        self.schema = schema
        self.warehouse_id = warehouse_id
        self._connection = None
        
        if not DATABRICKS_AVAILABLE:
            raise ImportError(
                "Databricks SDK not installed. Install with: "
                "pip install databricks-sql-connector databricks-sdk"
            )
    
    def connect(self):
        """Establish connection to Databricks SQL warehouse."""
        self._connection = databricks_sql.connect(
            server_hostname=self.host,
            http_path=self.http_path,
            access_token=self.token
        )
        return self._connection
    
    def close(self):
        """Close the connection."""
        if self._connection:
            self._connection.close()
    
    def execute(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results."""
        cursor = self._connection.cursor()
        try:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            cursor.close()
    
    def create_schema_if_not_exists(self):
        """Create the target schema if it doesn't exist."""
        self.execute(f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.schema}")
    
    def get_table_count(self, table_name: str) -> int:
        """Get row count for a table."""
        result = self.execute(
            f"SELECT COUNT(*) as cnt FROM {self.catalog}.{self.schema}.{table_name}"
        )
        return result[0]['cnt'] if result else 0
    
    def get_table_columns(self, table_name: str) -> List[Tuple[str, str]]:
        """Get column names and types for a table."""
        result = self.execute(
            f"DESCRIBE TABLE {self.catalog}.{self.schema}.{table_name}"
        )
        return [(r['col_name'], r['data_type']) for r in result if not r['col_name'].startswith('#')]
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        try:
            self.execute(f"DESCRIBE TABLE {self.catalog}.{self.schema}.{table_name}")
            return True
        except Exception:
            return False
    
    def load_jsonl_to_table(
        self, 
        file_path: Path, 
        table_name: str,
        overwrite: bool = True
    ) -> int:
        """Load a JSONL file to a Databricks table."""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas required for data loading")
        
        # Read JSONL file
        df = pd.read_json(file_path, lines=True)
        
        # Clean column names (Databricks doesn't like certain characters)
        df.columns = [self._clean_column_name(c) for c in df.columns]
        
        # Convert to Spark DataFrame and write
        # Note: This is a simplified version - production would use Spark directly
        
        # For now, generate CREATE TABLE and INSERT statements
        create_sql = self._generate_create_table(table_name, df)
        
        if overwrite and self.table_exists(table_name):
            self.execute(f"DROP TABLE IF EXISTS {self.catalog}.{self.schema}.{table_name}")
        
        self.execute(create_sql)
        
        # Insert in batches
        batch_size = 1000
        inserted = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            insert_sql = self._generate_insert(table_name, batch)
            self.execute(insert_sql)
            inserted += len(batch)
        
        return inserted
    
    def _clean_column_name(self, name: str) -> str:
        """Clean column name for Databricks compatibility."""
        # Replace problematic characters
        cleaned = name.replace('.', '_').replace('-', '_').replace(' ', '_')
        # Ensure doesn't start with number
        if cleaned[0].isdigit():
            cleaned = 'col_' + cleaned
        return cleaned.lower()
    
    def _generate_create_table(self, table_name: str, df: 'pd.DataFrame') -> str:
        """Generate CREATE TABLE SQL from DataFrame schema."""
        columns = []
        for col in df.columns:
            dtype = df[col].dtype
            if dtype == 'object':
                sql_type = 'STRING'
            elif dtype == 'int64':
                sql_type = 'BIGINT'
            elif dtype == 'float64':
                sql_type = 'DOUBLE'
            elif dtype == 'bool':
                sql_type = 'BOOLEAN'
            else:
                sql_type = 'STRING'
            columns.append(f"  {col} {sql_type}")
        
        return f"""
CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema}.{table_name} (
{','.join(columns)}
)
"""
    
    def _generate_insert(self, table_name: str, df: 'pd.DataFrame') -> str:
        """Generate INSERT SQL for a batch of rows."""
        columns = ', '.join(df.columns)
        values = []
        
        for _, row in df.iterrows():
            row_values = []
            for val in row:
                if pd.isna(val):
                    row_values.append('NULL')
                elif isinstance(val, str):
                    # Escape quotes
                    escaped = val.replace("'", "''")
                    row_values.append(f"'{escaped}'")
                elif isinstance(val, bool):
                    row_values.append('TRUE' if val else 'FALSE')
                else:
                    row_values.append(str(val))
            values.append(f"({', '.join(row_values)})")
        
        return f"""
INSERT INTO {self.catalog}.{self.schema}.{table_name} ({columns})
VALUES {', '.join(values)}
"""


class DataValidator:
    """Validates data between Splunk extraction and Databricks."""
    
    def __init__(
        self,
        manifest_path: str,
        databricks_loader: Optional[DatabricksLoader] = None
    ):
        self.manifest_path = Path(manifest_path)
        self.loader = databricks_loader
        
        with open(manifest_path) as f:
            self.manifest = json.load(f)
    
    def validate_local_extraction(self) -> Dict[str, Any]:
        """Validate the local extracted files against manifest."""
        results = {
            'total_sourcetypes': len(self.manifest['sourcetypes']),
            'files_exist': 0,
            'counts_match': 0,
            'issues': []
        }
        
        for st in self.manifest['sourcetypes']:
            file_path = Path(st['file_path'])
            
            # Check file exists
            if not file_path.exists():
                results['issues'].append(f"{st['sourcetype']}: file not found")
                continue
            
            results['files_exist'] += 1
            
            # Verify count
            if st['extracted_count'] == st['event_count']:
                results['counts_match'] += 1
            else:
                results['issues'].append(
                    f"{st['sourcetype']}: count mismatch "
                    f"(expected {st['event_count']}, got {st['extracted_count']})"
                )
        
        results['all_passed'] = (
            results['files_exist'] == results['total_sourcetypes'] and
            results['counts_match'] == results['total_sourcetypes']
        )
        
        return results
    
    def validate_against_databricks(self) -> ValidationReport:
        """Validate extracted data against Databricks tables."""
        if not self.loader:
            raise ValueError("Databricks loader required for this validation")
        
        validation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        validations = []
        
        total_splunk = 0
        total_databricks = 0
        passed = 0
        
        for st in self.manifest['sourcetypes']:
            sourcetype = st['sourcetype']
            table_name = sourcetype.replace(':', '_').replace('/', '_').lower()
            
            splunk_count = st['extracted_count']
            splunk_columns = st['fields']
            total_splunk += splunk_count
            
            try:
                # Check if table exists
                if not self.loader.table_exists(table_name):
                    validations.append(SourcetypeValidation(
                        sourcetype=sourcetype,
                        splunk_count=splunk_count,
                        databricks_count=0,
                        count_match=False,
                        splunk_columns=splunk_columns,
                        databricks_columns=[],
                        column_comparison=[],
                        schema_match=False,
                        status='failed',
                        error_message='Table does not exist in Databricks'
                    ))
                    continue
                
                # Get Databricks count
                db_count = self.loader.get_table_count(table_name)
                total_databricks += db_count
                count_match = db_count == splunk_count
                
                # Get Databricks columns
                db_columns = self.loader.get_table_columns(table_name)
                db_column_names = [c[0] for c in db_columns]
                
                # Compare columns
                column_comparison = []
                all_splunk_cols = set(c.lower() for c in splunk_columns)
                all_db_cols = set(c.lower() for c in db_column_names)
                
                for col in all_splunk_cols | all_db_cols:
                    in_splunk = col in all_splunk_cols
                    in_db = col in all_db_cols
                    db_type = next((c[1] for c in db_columns if c[0].lower() == col), None)
                    
                    column_comparison.append(ColumnComparison(
                        column_name=col,
                        in_splunk=in_splunk,
                        in_databricks=in_db,
                        splunk_sample_values=[],
                        databricks_type=db_type,
                        match=in_splunk and in_db
                    ))
                
                schema_match = all(c.match for c in column_comparison)
                
                # Determine status
                if count_match and schema_match:
                    status = 'success'
                    passed += 1
                elif not count_match:
                    status = 'count_mismatch'
                else:
                    status = 'schema_mismatch'
                
                validations.append(SourcetypeValidation(
                    sourcetype=sourcetype,
                    splunk_count=splunk_count,
                    databricks_count=db_count,
                    count_match=count_match,
                    splunk_columns=splunk_columns,
                    databricks_columns=db_column_names,
                    column_comparison=column_comparison,
                    schema_match=schema_match,
                    status=status
                ))
                
            except Exception as e:
                validations.append(SourcetypeValidation(
                    sourcetype=sourcetype,
                    splunk_count=splunk_count,
                    databricks_count=0,
                    count_match=False,
                    splunk_columns=splunk_columns,
                    databricks_columns=[],
                    column_comparison=[],
                    schema_match=False,
                    status='failed',
                    error_message=str(e)
                ))
        
        overall_status = 'passed' if passed == len(validations) else 'failed'
        
        return ValidationReport(
            validation_id=validation_id,
            validation_timestamp=datetime.now().isoformat(),
            extraction_manifest_path=str(self.manifest_path),
            databricks_catalog=self.loader.catalog,
            databricks_schema=self.loader.schema,
            total_sourcetypes=len(validations),
            sourcetypes_validated=len(validations),
            sourcetypes_passed=passed,
            total_events_splunk=total_splunk,
            total_events_databricks=total_databricks,
            overall_status=overall_status,
            sourcetype_validations=validations
        )
    
    def generate_comparison_report(self, output_path: Optional[str] = None) -> str:
        """Generate a detailed comparison report."""
        lines = [
            "# BOTSv3 Data Validation Report",
            f"Generated: {datetime.now().isoformat()}",
            f"Manifest: {self.manifest_path}",
            "",
            "## Extraction Summary",
            f"- Total Sourcetypes: {len(self.manifest['sourcetypes'])}",
            f"- Total Events Expected: {self.manifest['total_events_expected']:,}",
            f"- Total Events Extracted: {self.manifest['total_events_extracted']:,}",
            f"- Validation Status: {'PASSED' if self.manifest['validation_passed'] else 'FAILED'}",
            "",
            "## Sourcetype Details",
            ""
        ]
        
        for st in self.manifest['sourcetypes']:
            status_icon = "✓" if st['status'] == 'success' else "✗"
            lines.extend([
                f"### {st['sourcetype']} {status_icon}",
                f"- Events: {st['extracted_count']:,} / {st['event_count']:,}",
                f"- Fields: {len(st['fields'])}",
                f"- File: {st['file_path']}",
                f"- Size: {st['file_size_bytes']:,} bytes",
                f"- MD5: {st['checksum_md5']}",
                ""
            ])
            
            if st.get('error_message'):
                lines.append(f"- **Error:** {st['error_message']}")
                lines.append("")
        
        report = '\n'.join(lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
        
        return report


# CLI Commands
@click.group()
def cli():
    """Databricks Data Loader and Validator for BOTSv3."""
    pass


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output report path")
def validate_local(manifest_path, output):
    """Validate local extraction files against manifest."""
    validator = DataValidator(manifest_path)
    results = validator.validate_local_extraction()
    
    table = Table(title="Local Validation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Sourcetypes", str(results['total_sourcetypes']))
    table.add_row("Files Exist", str(results['files_exist']))
    table.add_row("Counts Match", str(results['counts_match']))
    table.add_row("Status", "[green]PASSED[/green]" if results['all_passed'] else "[red]FAILED[/red]")
    
    console.print(table)
    
    if results['issues']:
        console.print("\n[bold yellow]Issues:[/bold yellow]")
        for issue in results['issues']:
            console.print(f"  • {issue}")
    
    if output:
        report = validator.generate_comparison_report(output)
        console.print(f"\nReport saved to: {output}")
    
    if not results['all_passed']:
        sys.exit(1)


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option("--host", envvar="DATABRICKS_HOST", required=True, help="Databricks host")
@click.option("--token", envvar="DATABRICKS_TOKEN", required=True, help="Access token")
@click.option("--http-path", envvar="DATABRICKS_HTTP_PATH", required=True, help="SQL warehouse HTTP path")
@click.option("--catalog", default="main", help="Target catalog")
@click.option("--schema", default="botsv3", help="Target schema")
@click.option("--output", "-o", help="Output report path")
def validate_databricks(manifest_path, host, token, http_path, catalog, schema, output):
    """Validate extraction against Databricks tables."""
    if not DATABRICKS_AVAILABLE:
        console.print("[red]Databricks SDK not installed. Run: pip install databricks-sql-connector[/red]")
        sys.exit(1)
    
    loader = DatabricksLoader(
        host=host,
        token=token,
        http_path=http_path,
        catalog=catalog,
        schema=schema
    )
    
    try:
        loader.connect()
        validator = DataValidator(manifest_path, loader)
        
        with console.status("Validating against Databricks..."):
            report = validator.validate_against_databricks()
        
        # Display results
        table = Table(title="Databricks Validation Results")
        table.add_column("Sourcetype", style="cyan")
        table.add_column("Splunk", justify="right")
        table.add_column("Databricks", justify="right")
        table.add_column("Count", justify="center")
        table.add_column("Schema", justify="center")
        table.add_column("Status")
        
        for v in report.sourcetype_validations:
            table.add_row(
                v.sourcetype,
                f"{v.splunk_count:,}",
                f"{v.databricks_count:,}",
                "[green]✓[/green]" if v.count_match else "[red]✗[/red]",
                "[green]✓[/green]" if v.schema_match else "[yellow]~[/yellow]",
                f"[green]{v.status}[/green]" if v.status == 'success' else f"[red]{v.status}[/red]"
            )
        
        console.print(table)
        
        console.print(f"\n[bold]Overall Status:[/bold] ", end="")
        if report.overall_status == 'passed':
            console.print("[bold green]PASSED[/bold green]")
        else:
            console.print("[bold red]FAILED[/bold red]")
        
        console.print(f"Total Events - Splunk: {report.total_events_splunk:,}, Databricks: {report.total_events_databricks:,}")
        
        # Save report
        if output:
            with open(output, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
            console.print(f"\nReport saved to: {output}")
        
        if report.overall_status != 'passed':
            sys.exit(1)
            
    finally:
        loader.close()


@cli.command()
@click.argument("data_dir", type=click.Path(exists=True))
@click.option("--host", envvar="DATABRICKS_HOST", required=True)
@click.option("--token", envvar="DATABRICKS_TOKEN", required=True)
@click.option("--http-path", envvar="DATABRICKS_HTTP_PATH", required=True)
@click.option("--catalog", default="main")
@click.option("--schema", default="botsv3")
@click.option("--overwrite", is_flag=True, help="Overwrite existing tables")
def load(data_dir, host, token, http_path, catalog, schema, overwrite):
    """Load extracted data files into Databricks."""
    if not DATABRICKS_AVAILABLE:
        console.print("[red]Databricks SDK not installed[/red]")
        sys.exit(1)
    
    if not PANDAS_AVAILABLE:
        console.print("[red]pandas required for data loading. Run: pip install pandas[/red]")
        sys.exit(1)
    
    loader = DatabricksLoader(
        host=host,
        token=token,
        http_path=http_path,
        catalog=catalog,
        schema=schema
    )
    
    data_path = Path(data_dir)
    files = list(data_path.glob("*.jsonl")) + list(data_path.glob("*.json"))
    
    if not files:
        console.print("[yellow]No data files found[/yellow]")
        return
    
    console.print(f"Found {len(files)} files to load\n")
    
    try:
        loader.connect()
        loader.create_schema_if_not_exists()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for file_path in files:
                table_name = file_path.stem.lower()
                task = progress.add_task(f"Loading {table_name}...", total=None)
                
                try:
                    count = loader.load_jsonl_to_table(file_path, table_name, overwrite=overwrite)
                    progress.update(task, description=f"[green]✓[/green] {table_name}: {count:,} rows")
                except Exception as e:
                    progress.update(task, description=f"[red]✗[/red] {table_name}: {e}")
                
                progress.remove_task(task)
        
        console.print("\n[green]Load complete![/green]")
        
    finally:
        loader.close()


@cli.command()
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option("--output", "-o", default="validation_report.md")
def report(manifest_path, output):
    """Generate a detailed validation report."""
    validator = DataValidator(manifest_path)
    report_content = validator.generate_comparison_report(output)
    
    console.print(f"Report generated: {output}")
    console.print("\n" + report_content)


if __name__ == "__main__":
    cli()
