#!/usr/bin/env python3
"""
Splunk REST API Testing Harness for BOTSv3
A command-line tool for interacting with Splunk Enterprise via REST API.

Usage:
    python splunk_client.py --help
    python splunk_client.py search "index=botsv3 earliest=0 | head 10"
    python splunk_client.py info
"""

import os
import sys
import time
import json
import click
import urllib3
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from dotenv import load_dotenv

try:
    import requests
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    from rich.panel import Panel
except ImportError:
    print("Missing dependencies. Install with: pip install -r requirements.txt")
    sys.exit(1)

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Rich console for pretty output
console = Console()


@dataclass
class SplunkConfig:
    """Splunk connection configuration."""
    host: str = "localhost"
    port: int = 8089
    username: str = "admin"
    password: str = "changeme123"
    scheme: str = "https"
    verify_ssl: bool = False
    
    @property
    def base_url(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"
    
    @classmethod
    def from_env(cls) -> "SplunkConfig":
        """Create config from environment variables."""
        return cls(
            host=os.getenv("SPLUNK_HOST", "localhost"),
            port=int(os.getenv("SPLUNK_PORT", "8089")),
            username=os.getenv("SPLUNK_USERNAME", "admin"),
            password=os.getenv("SPLUNK_PASSWORD", "changeme123"),
            scheme=os.getenv("SPLUNK_SCHEME", "https"),
            verify_ssl=os.getenv("SPLUNK_VERIFY_SSL", "false").lower() == "true"
        )


class SplunkClient:
    """Splunk REST API client for BOTSv3 testing."""
    
    def __init__(self, config: SplunkConfig):
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config.username, config.password)
        self.session.verify = config.verify_ssl
        self._session_key: Optional[str] = None
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        use_session_key: bool = False
    ) -> requests.Response:
        """Make a request to the Splunk REST API."""
        url = f"{self.config.base_url}{endpoint}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        if use_session_key and self._session_key:
            headers["Authorization"] = f"Splunk {self._session_key}"
        
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            headers=headers
        )
        return response
    
    def authenticate(self) -> bool:
        """Authenticate and get a session key."""
        try:
            response = self._request(
                "POST",
                "/services/auth/login",
                data={
                    "username": self.config.username,
                    "password": self.config.password,
                    "output_mode": "json"
                }
            )
            if response.status_code == 200:
                data = response.json()
                self._session_key = data.get("sessionKey")
                return True
            return False
        except Exception as e:
            console.print(f"[red]Authentication failed: {e}[/red]")
            return False
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get Splunk server information."""
        response = self._request(
            "GET",
            "/services/server/info",
            params={"output_mode": "json"}
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to get server info: {response.status_code}")
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get Splunk server status."""
        response = self._request(
            "GET",
            "/services/server/status",
            params={"output_mode": "json"}
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to get server status: {response.status_code}")
    
    def list_indexes(self) -> List[Dict[str, Any]]:
        """List all indexes."""
        response = self._request(
            "GET",
            "/services/data/indexes",
            params={"output_mode": "json"}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("entry", [])
        raise Exception(f"Failed to list indexes: {response.status_code}")
    
    def get_index_info(self, index_name: str) -> Dict[str, Any]:
        """Get information about a specific index."""
        response = self._request(
            "GET",
            f"/services/data/indexes/{index_name}",
            params={"output_mode": "json"}
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to get index info: {response.status_code}")
    
    def create_search_job(self, search_query: str, **kwargs) -> str:
        """Create a search job and return the job SID."""
        data = {
            "search": search_query if search_query.startswith("search ") else f"search {search_query}",
            "output_mode": "json",
            **kwargs
        }
        response = self._request("POST", "/services/search/jobs", data=data)
        if response.status_code == 201:
            result = response.json()
            return result.get("sid")
        raise Exception(f"Failed to create search job: {response.status_code} - {response.text}")
    
    def get_job_status(self, sid: str) -> Dict[str, Any]:
        """Get the status of a search job."""
        response = self._request(
            "GET",
            f"/services/search/jobs/{sid}",
            params={"output_mode": "json"}
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to get job status: {response.status_code}")
    
    def wait_for_job(self, sid: str, timeout: int = 300, poll_interval: int = 2) -> bool:
        """Wait for a search job to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_job_status(sid)
            entry = status.get("entry", [{}])[0]
            content = entry.get("content", {})
            
            dispatch_state = content.get("dispatchState", "")
            is_done = content.get("isDone", False)
            
            if is_done or dispatch_state == "DONE":
                return True
            elif dispatch_state == "FAILED":
                raise Exception(f"Search job failed: {content.get('messages', 'Unknown error')}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Search job {sid} timed out after {timeout} seconds")
    
    def get_job_results(
        self, 
        sid: str, 
        count: int = 100, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get results from a completed search job."""
        response = self._request(
            "GET",
            f"/services/search/jobs/{sid}/results",
            params={
                "output_mode": "json",
                "count": count,
                "offset": offset
            }
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to get job results: {response.status_code}")
    
    def search_blocking(
        self, 
        search_query: str, 
        timeout: int = 300,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Execute a search and wait for results (blocking)."""
        # Create job
        sid = self.create_search_job(search_query)
        
        # Wait for completion
        self.wait_for_job(sid, timeout=timeout)
        
        # Get results
        results = self.get_job_results(sid, count=max_results)
        return results.get("results", [])
    
    def oneshot_search(
        self, 
        search_query: str, 
        count: int = 100,
        earliest_time: str = "0",
        latest_time: str = "now"
    ) -> List[Dict[str, Any]]:
        """Execute a oneshot search (simpler for quick queries)."""
        data = {
            "search": search_query if search_query.startswith("search ") else f"search {search_query}",
            "output_mode": "json",
            "count": count,
            "earliest_time": earliest_time,
            "latest_time": latest_time
        }
        response = self._request(
            "POST",
            "/services/search/jobs/oneshot",
            data=data
        )
        if response.status_code == 200:
            return response.json().get("results", [])
        raise Exception(f"Oneshot search failed: {response.status_code} - {response.text}")
    
    def list_apps(self) -> List[Dict[str, Any]]:
        """List installed apps."""
        response = self._request(
            "GET",
            "/services/apps/local",
            params={"output_mode": "json"}
        )
        if response.status_code == 200:
            return response.json().get("entry", [])
        raise Exception(f"Failed to list apps: {response.status_code}")
    
    def get_sourcetypes(self, index: str = "botsv3") -> List[str]:
        """Get list of sourcetypes in an index."""
        results = self.oneshot_search(
            f"index={index} earliest=0 | stats count by sourcetype | sort -count",
            count=1000
        )
        return [r.get("sourcetype") for r in results if r.get("sourcetype")]
    
    def health_check(self) -> bool:
        """Perform a basic health check."""
        try:
            info = self.get_server_info()
            return bool(info.get("entry"))
        except Exception:
            return False


# CLI Commands using Click
@click.group()
@click.option("--host", default="localhost", envvar="SPLUNK_HOST", help="Splunk host")
@click.option("--port", default=8089, envvar="SPLUNK_PORT", help="Splunk REST port")
@click.option("--username", default="admin", envvar="SPLUNK_USERNAME", help="Username")
@click.option("--password", default="changeme123", envvar="SPLUNK_PASSWORD", help="Password")
@click.option("--no-ssl", is_flag=True, help="Use HTTP instead of HTTPS")
@click.pass_context
def cli(ctx, host, port, username, password, no_ssl):
    """Splunk REST API Testing Harness for BOTSv3."""
    ctx.ensure_object(dict)
    config = SplunkConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        scheme="http" if no_ssl else "https"
    )
    ctx.obj["client"] = SplunkClient(config)
    ctx.obj["config"] = config


@cli.command()
@click.pass_context
def info(ctx):
    """Display Splunk server information."""
    client: SplunkClient = ctx.obj["client"]
    
    with console.status("[bold green]Fetching server info..."):
        try:
            info = client.get_server_info()
            entry = info.get("entry", [{}])[0]
            content = entry.get("content", {})
            
            table = Table(title="Splunk Server Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            props = [
                ("Server Name", content.get("serverName", "N/A")),
                ("Version", content.get("version", "N/A")),
                ("Build", content.get("build", "N/A")),
                ("OS Name", content.get("os_name", "N/A")),
                ("OS Version", content.get("os_version", "N/A")),
                ("CPU Architecture", content.get("cpu_arch", "N/A")),
                ("License State", content.get("licenseState", "N/A")),
                ("GUID", content.get("guid", "N/A")),
            ]
            
            for prop, value in props:
                table.add_row(prop, str(value))
            
            console.print(table)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.pass_context
def health(ctx):
    """Check Splunk server health."""
    client: SplunkClient = ctx.obj["client"]
    config: SplunkConfig = ctx.obj["config"]
    
    console.print(f"\n[bold]Checking Splunk at {config.base_url}...[/bold]\n")
    
    checks = []
    
    # Connection check
    with console.status("[bold]Testing connection..."):
        try:
            if client.health_check():
                checks.append(("Connection", "[green]✓ OK[/green]"))
            else:
                checks.append(("Connection", "[red]✗ Failed[/red]"))
        except Exception as e:
            checks.append(("Connection", f"[red]✗ Error: {e}[/red]"))
    
    # Authentication check
    with console.status("[bold]Testing authentication..."):
        try:
            if client.authenticate():
                checks.append(("Authentication", "[green]✓ OK[/green]"))
            else:
                checks.append(("Authentication", "[red]✗ Failed[/red]"))
        except Exception as e:
            checks.append(("Authentication", f"[red]✗ Error: {e}[/red]"))
    
    # BOTSv3 index check
    with console.status("[bold]Checking BOTSv3 index..."):
        try:
            indexes = client.list_indexes()
            botsv3_exists = any(idx.get("name") == "botsv3" for idx in indexes)
            if botsv3_exists:
                checks.append(("BOTSv3 Index", "[green]✓ Found[/green]"))
            else:
                checks.append(("BOTSv3 Index", "[yellow]⚠ Not found[/yellow]"))
        except Exception as e:
            checks.append(("BOTSv3 Index", f"[red]✗ Error: {e}[/red]"))
    
    # Display results
    table = Table(title="Health Check Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    
    for check, status in checks:
        table.add_row(check, status)
    
    console.print(table)


@cli.command()
@click.argument("query")
@click.option("--count", "-c", default=100, help="Maximum results to return")
@click.option("--timeout", "-t", default=300, help="Search timeout in seconds")
@click.option("--earliest", "-e", default="0", help="Earliest time")
@click.option("--latest", "-l", default="now", help="Latest time")
@click.option("--json-output", "-j", is_flag=True, help="Output raw JSON")
@click.option("--fields", "-f", default=None, help="Comma-separated list of fields to display")
@click.pass_context
def search(ctx, query, count, timeout, earliest, latest, json_output, fields):
    """Execute a Splunk search query."""
    client: SplunkClient = ctx.obj["client"]
    
    # Ensure query has time bounds if searching botsv3
    if "index=botsv3" in query.lower() and "earliest=" not in query.lower():
        query = f"{query} earliest={earliest} latest={latest}"
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Executing search...", total=None)
        
        try:
            results = client.search_blocking(query, timeout=timeout, max_results=count)
            progress.update(task, description="[green]Search complete!")
        except Exception as e:
            console.print(f"[red]Search failed: {e}[/red]")
            sys.exit(1)
    
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return
    
    if json_output:
        console.print(Syntax(json.dumps(results, indent=2), "json"))
        return
    
    # Determine fields to display
    if fields:
        display_fields = [f.strip() for f in fields.split(",")]
    else:
        # Auto-detect common fields
        all_fields = set()
        for r in results[:10]:
            all_fields.update(r.keys())
        # Prioritize common fields
        priority = ["_time", "host", "source", "sourcetype", "_raw"]
        display_fields = [f for f in priority if f in all_fields]
        display_fields.extend([f for f in sorted(all_fields) if f not in display_fields][:5])
    
    # Create results table
    table = Table(title=f"Search Results ({len(results)} events)")
    for field in display_fields:
        table.add_column(field, overflow="fold", max_width=50)
    
    for result in results:
        row = [str(result.get(f, ""))[:100] for f in display_fields]
        table.add_row(*row)
    
    console.print(table)
    console.print(f"\n[dim]Total results: {len(results)}[/dim]")


@cli.command()
@click.pass_context
def indexes(ctx):
    """List all Splunk indexes."""
    client: SplunkClient = ctx.obj["client"]
    
    with console.status("[bold green]Fetching indexes..."):
        try:
            indexes = client.list_indexes()
            
            table = Table(title="Splunk Indexes")
            table.add_column("Index", style="cyan")
            table.add_column("Total Events", style="green")
            table.add_column("Current Size", style="yellow")
            table.add_column("Max Size", style="blue")
            
            for idx in indexes:
                name = idx.get("name", "")
                content = idx.get("content", {})
                current_size = content.get("currentDBSizeMB")
                max_size = content.get("maxTotalDataSizeMB")
                table.add_row(
                    name,
                    str(content.get("totalEventCount", "N/A")),
                    f"{current_size} MB" if current_size else "N/A",
                    f"{max_size} MB" if max_size else "N/A"
                )
            
            console.print(table)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.option("--index", "-i", default="botsv3", help="Index to query")
@click.pass_context
def sourcetypes(ctx, index):
    """List sourcetypes in an index."""
    client: SplunkClient = ctx.obj["client"]
    
    with console.status(f"[bold green]Fetching sourcetypes from {index}..."):
        try:
            results = client.oneshot_search(
                f"index={index} earliest=0 | stats count by sourcetype | sort -count",
                count=500
            )
            
            table = Table(title=f"Sourcetypes in '{index}'")
            table.add_column("Sourcetype", style="cyan")
            table.add_column("Event Count", style="green", justify="right")
            
            for r in results:
                table.add_row(
                    r.get("sourcetype", ""),
                    r.get("count", "0")
                )
            
            console.print(table)
            console.print(f"\n[dim]Total sourcetypes: {len(results)}[/dim]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.pass_context
def apps(ctx):
    """List installed Splunk apps."""
    client: SplunkClient = ctx.obj["client"]
    
    with console.status("[bold green]Fetching installed apps..."):
        try:
            apps = client.list_apps()
            
            table = Table(title="Installed Splunk Apps")
            table.add_column("Name", style="cyan")
            table.add_column("Label", style="green")
            table.add_column("Version", style="yellow")
            table.add_column("Visible", style="blue")
            
            for app in apps:
                name = app.get("name", "")
                content = app.get("content", {})
                table.add_row(
                    name,
                    content.get("label", "N/A"),
                    content.get("version", "N/A"),
                    "Yes" if content.get("visible", False) else "No"
                )
            
            console.print(table)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.pass_context
def botsv3_stats(ctx):
    """Display BOTSv3 dataset statistics."""
    client: SplunkClient = ctx.obj["client"]
    
    console.print(Panel.fit("[bold cyan]BOTSv3 Dataset Statistics[/bold cyan]"))
    
    queries = [
        ("Total Events", "index=botsv3 earliest=0 | stats count"),
        ("Time Range", "index=botsv3 earliest=0 | stats min(_time) as earliest max(_time) as latest"),
        ("Top Hosts", "index=botsv3 earliest=0 | stats count by host | sort -count | head 10"),
        ("Top Sources", "index=botsv3 earliest=0 | stats count by source | sort -count | head 10"),
    ]
    
    for title, query in queries:
        with console.status(f"[bold]Running: {title}..."):
            try:
                results = client.oneshot_search(query, count=100)
                
                console.print(f"\n[bold cyan]{title}:[/bold cyan]")
                
                if results:
                    if len(results) == 1 and "count" in results[0]:
                        console.print(f"  {results[0].get('count', 'N/A')}")
                    elif "earliest" in results[0]:
                        console.print(f"  Earliest: {results[0].get('earliest', 'N/A')}")
                        console.print(f"  Latest: {results[0].get('latest', 'N/A')}")
                    else:
                        table = Table(show_header=True, box=None)
                        if results:
                            for col in results[0].keys():
                                table.add_column(col)
                            for r in results:
                                table.add_row(*[str(r.get(c, "")) for c in results[0].keys()])
                        console.print(table)
                else:
                    console.print("  [yellow]No data[/yellow]")
            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")


@cli.command()
@click.argument("query")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--format", "-f", "output_format", type=click.Choice(["json", "csv"]), default="json")
@click.option("--count", "-c", default=10000, help="Maximum results")
@click.pass_context
def export(ctx, query, output, output_format, count):
    """Export search results to a file."""
    client: SplunkClient = ctx.obj["client"]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Executing search...", total=None)
        
        try:
            results = client.search_blocking(query, max_results=count)
            progress.update(task, description="[green]Search complete!")
        except Exception as e:
            console.print(f"[red]Export failed: {e}[/red]")
            sys.exit(1)
    
    if not results:
        console.print("[yellow]No results to export.[/yellow]")
        return
    
    if output_format == "json":
        content = json.dumps(results, indent=2)
    else:  # csv
        import csv
        import io
        output_io = io.StringIO()
        if results:
            writer = csv.DictWriter(output_io, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        content = output_io.getvalue()
    
    if output:
        with open(output, "w") as f:
            f.write(content)
        console.print(f"[green]Exported {len(results)} results to {output}[/green]")
    else:
        console.print(content)


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start an interactive search session."""
    client: SplunkClient = ctx.obj["client"]
    config: SplunkConfig = ctx.obj["config"]
    
    console.print(Panel.fit(
        f"[bold cyan]Splunk Interactive Session[/bold cyan]\n"
        f"Connected to: {config.base_url}\n"
        f"Type 'exit' or 'quit' to end session\n"
        f"Type 'help' for available commands"
    ))
    
    while True:
        try:
            query = console.input("\n[bold green]splunk>[/bold green] ")
            query = query.strip()
            
            if not query:
                continue
            
            if query.lower() in ("exit", "quit", "q"):
                console.print("[cyan]Goodbye![/cyan]")
                break
            
            if query.lower() == "help":
                console.print("""
[bold]Available Commands:[/bold]
  <search query>    Execute a search
  info              Show server info
  indexes           List indexes
  sourcetypes       List sourcetypes in botsv3
  stats             Show BOTSv3 statistics
  exit/quit         Exit interactive mode

[bold]Quick Searches:[/bold]
  index=botsv3 earliest=0 | head 10
  index=botsv3 sourcetype=wineventlog | head 10
  index=botsv3 | stats count by sourcetype
                """)
                continue
            
            if query.lower() == "info":
                ctx.invoke(info)
                continue
            
            if query.lower() == "indexes":
                ctx.invoke(indexes)
                continue
            
            if query.lower() == "sourcetypes":
                ctx.invoke(sourcetypes)
                continue
            
            if query.lower() == "stats":
                ctx.invoke(botsv3_stats)
                continue
            
            # Execute as search
            with console.status("[bold]Searching..."):
                results = client.search_blocking(query, max_results=50)
            
            if not results:
                console.print("[yellow]No results found.[/yellow]")
                continue
            
            # Display results
            console.print(f"\n[green]Found {len(results)} results:[/green]")
            for i, r in enumerate(results[:10], 1):
                raw = r.get("_raw", str(r))[:200]
                console.print(f"[dim]{i}.[/dim] {raw}")
            
            if len(results) > 10:
                console.print(f"[dim]... and {len(results) - 10} more[/dim]")
                
        except KeyboardInterrupt:
            console.print("\n[cyan]Use 'exit' to quit[/cyan]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    cli()
