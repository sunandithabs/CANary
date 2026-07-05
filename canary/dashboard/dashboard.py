"""
Terminal dashboard.

build_* functions are pure and testable: data in, Rich renderable out.
run_dashboard owns the terminal and refresh timing.
"""

import time

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from ..detector.alert import Alert, Severity
from ..detector.detector import Detector
from ..stats.stats_engine import StatsEngine

SEVERITY_STYLE = {
    Severity.LOW: "dim",
    Severity.MEDIUM: "yellow",
    Severity.HIGH: "bold orange3",
    Severity.CRITICAL: "bold red",
}


def build_stats_table(snapshot: dict) -> Table:
    table = Table(title="Bus Telemetry")
    table.add_column("Metric")
    table.add_column("Value")

    table.add_row("Total frames", str(snapshot["total_frames"]))
    table.add_row("Bus utilization", f"{snapshot['bus_utilization_pct']}%")
    table.add_row("Avg arbitration latency", f"{snapshot['average_latency_ms']} ms")
    table.add_row("Dropped frames", str(snapshot["dropped_frames"]))

    talkers = ", ".join(f"{name} ({count})" for name, count in snapshot["top_talkers"])
    table.add_row("Top talkers", talkers or "-")
    return table


def build_alerts_table(alerts: list[Alert], max_rows: int = 10) -> Table:
    table = Table(title="Recent Alerts")
    table.add_column("Severity")
    table.add_column("Rule")
    table.add_column("ID")
    table.add_column("Source")
    table.add_column("Message")

    for alert in alerts[-max_rows:]:
        style = SEVERITY_STYLE.get(alert.severity, "")
        table.add_row(
            f"[{style}]{alert.severity}[/{style}]",
            alert.rule_name,
            f"0x{alert.arbitration_id:03X}",
            alert.source_ecu,
            alert.message,
        )
    return table


def build_dashboard_view(stats: StatsEngine, detector: Detector) -> Panel:
    snapshot = stats.snapshot()
    body = Group(build_stats_table(snapshot), build_alerts_table(detector.alerts))
    return Panel(body, title="CANARY - Live Bus Monitor")


def run_dashboard(stats: StatsEngine, detector: Detector, refresh_hz: float = 4.0) -> None:
    """Owns the terminal. Renders build_dashboard_view() on a fixed
    interval until interrupted."""
    interval = 1.0 / refresh_hz
    with Live(build_dashboard_view(stats, detector), refresh_per_second=refresh_hz) as live:
        while True:
            time.sleep(interval)
            live.update(build_dashboard_view(stats, detector))
