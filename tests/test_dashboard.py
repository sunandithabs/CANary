from rich.table import Table
from rich.panel import Panel

from canary.bus import SimulatedBus, CANFrame
from canary.detector import Detector, IDBaseline, Severity
from canary.detector.alert import Alert
from canary.stats import StatsEngine
from canary.dashboard import build_stats_table, build_alerts_table, build_dashboard_view


def test_build_stats_table_returns_table():
    bus = SimulatedBus()
    stats = StatsEngine(bus)
    bus.subscribe(stats.observe)
    bus.offer(CANFrame(arbitration_id=0x100, data=b"\x01", source_ecu="engine_ecu"))
    bus.tick()

    table = build_stats_table(stats.snapshot())
    assert isinstance(table, Table)
    assert table.row_count == 5  # total, utilization, latency, dropped, top talkers


def test_build_alerts_table_handles_empty_alerts():
    table = build_alerts_table([])
    assert isinstance(table, Table)
    assert table.row_count == 0


def test_build_alerts_table_respects_max_rows():
    alerts = [
        Alert(timestamp=i, severity=Severity.LOW, rule_name="test_rule",
              arbitration_id=0x100, message="test", source_ecu="engine_ecu")
        for i in range(20)
    ]
    table = build_alerts_table(alerts, max_rows=5)
    assert table.row_count == 5


def test_build_dashboard_view_returns_panel():
    bus = SimulatedBus()
    stats = StatsEngine(bus)
    detector = Detector(baseline={0x100: IDBaseline("engine_ecu", 1, 0.01)})
    bus.subscribe(stats.observe)
    bus.subscribe(detector.inspect)

    bus.offer(CANFrame(arbitration_id=0x100, data=b"\x01", source_ecu="engine_ecu"))
    bus.tick()

    view = build_dashboard_view(stats, detector)
    assert isinstance(view, Panel)
