# CANARY

Real-time observability and intrusion detection for CAN bus networks.

CAN, plus "canary in the coal mine." An early-warning system for the network that runs almost every car, tractor, and industrial machine on the planet.

---

## Problem

Modern vehicles run 50-100+ ECUs (engine, brakes, steering, infotainment, and more), all talking over a shared CAN bus. CAN was designed in the 1980s for a closed, trusted network. It has no authentication and no encryption. Any node on the bus can send a frame claiming to be any other node.

That assumption stopped being safe once cars got Bluetooth, cellular modems, and USB ports. An attacker who reaches the bus, whether through an infotainment exploit, an OBD-II dongle, or a compromised telematics unit, can inject frames that look completely legitimate to every other ECU on the network.

## Why CAN Attacks Matter

Miller and Valasek's 2015 Jeep Cherokee remote takeover showed that CAN injection can control steering, braking, and acceleration. The attack surface has only grown since, as vehicles add more connectivity, while the CAN network itself still has essentially no built-in defense against a node that's lying about who it is.

Catching this means watching behavior, not just checking protocol correctness. A malicious frame is often a perfectly well-formed CAN frame. That's the actual engineering problem CANARY is built around.

## Architecture

```
                 ┌──────────────────────────────┐
                 │           ECU Nodes           │
                 │  (Engine, Brake, Door, or an  │
                 │   attacker injecting frames)  │
                 └───────────────┬────────────────┘
                                 │ CANFrame
                                 ▼
                 ┌──────────────────────────────┐
                 │        BusInterface           │
                 │   SimulatedBus (today)        │
                 │   SocketCANBus (future)       │
                 └───────────────┬────────────────┘
                        ┌────────┼────────┐
                        ▼        ▼         ▼
                 ┌─────────┐ ┌────────┐ ┌───────┐
                 │  Logger  │ │Detector│ │ Stats │
                 │ (CSV +   │ │(rules) │ │Engine │
                 │  replay) │ │        │ │       │
                 └─────────┘ └───┬────┘ └───┬───┘
                                 │ Alerts    │ Telemetry
                                 ▼           ▼
                        ┌──────────────────────────┐
                        │      Dashboard (TUI)       │
                        └──────────────────────────┘
```

Everything downstream of the bus talks to it only through `BusInterface.subscribe()` and `.offer()`. The logger, detector, and stats engine don't know or care whether frames come from a simulation or a real `vcan0` interface.

## Features

- Multi-ECU simulation with realistic timing, jitter, and priority-based arbitration
- CSV traffic logging plus timing-accurate replay from log files
- Rule-based anomaly detection: ID spoofing, malformed frames, impossible message frequency, flooding/DoS, replay attacks
- Severity-tagged alerts, LOW through CRITICAL
- Live terminal dashboard showing bus utilization, arbitration latency, top talkers, and recent alerts
- A native C component (CRC-15 checksum) bridged via `ctypes`, matching how real CAN controllers compute frame integrity at the bit level
- `SocketCANBus`: real Linux SocketCAN support via a raw `AF_CAN` socket, no external library. Works against a real interface (`vcan0` or physical hardware) with zero changes to the detector, logger, or dashboard
- 45 unit and integration tests (2 SocketCAN tests skip automatically outside a CAN-capable kernel, verified passing in CI against `vcan0`)
- Pre-generated sample datasets: clean traffic and a mixed multi-attack scenario

## Demo

```bash
pip install -r requirements.txt
bash canary/native/build.sh          # build the C CRC-15 component
PYTHONPATH=. python -m canary.simulator.generate_samples
```

This regenerates `data/sample_logs/normal_traffic.csv` (0 alerts) and `data/attack_scenarios/mixed_attacks.csv` (spoofing, malformed frame, flooding, and replay all caught), printing each alert as it fires.

To run the live dashboard against a running simulation:
```python
from canary.simulator import Simulator
from canary.dashboard import run_dashboard

sim = Simulator("live_demo.csv")
# in practice: run sim.step() on a timer thread, then:
run_dashboard(sim.stats, sim.detector)
```

## How It Works

1. ECUs send frames on a schedule with realistic jitter (`canary/ecu/`).
2. SimulatedBus resolves priority via a min-heap on arbitration ID, lower ID wins, the same way real CAN arbitration works (`canary/bus/`).
3. Logger, Detector, and StatsEngine each subscribe independently. None of them know the others exist.
4. Detector tracks per-ID baselines (expected source, size, period) and runs six independent rules against every frame, producing severity-tagged alerts.
5. StatsEngine aggregates telemetry, rates, latency, top talkers, purely from what it observes. It never touches bus internals.
6. Dashboard renders both and owns nothing else.

## Design Decisions

Arbitration is modeled as priority scheduling, not bit-level contention. This captures the real effect, latency under load and deterministic priority, without simulating electrical signaling that nothing downstream needs.

C shows up exactly once, for the CRC-15 checksum, because that's genuinely bit-level, hardware-adjacent work. It's not there for its own sake.

A number of protocol features are left out on purpose: bit-stuffing, ACK slots, error frames, remote frames, overload frames, the bus-off state machine, exact bit-level arbitration. None of them change what the detector can observe, so implementing them would just be chasing CAN-spec completeness instead of building detection tooling.

`BusInterface` got extracted after Module 4, not designed upfront, and it required zero changes to the detector, logger, or ECU code. That's what you get from subscriber-pattern decoupling from day one.

Two real bugs only showed up at integration time, in Module 7: ECU frames defaulted to wall-clock timestamps instead of simulated time, and the stats engine mixed wall-clock latency against simulated-time frames. Both got fixed with explicit, documented clock-passing rather than patched over. See `Simulator.__init__` and `StatsEngine.observe()`.

## Future Work

- CAN-FD support (larger payloads, flexible data rate)
- UDS (Unified Diagnostic Services) simulation
- J1939 (heavy-vehicle protocol layer)
- ISO-TP (multi-frame transport protocol)
- ML-based anomaly detection, as a stretch goal

## Running Tests

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

45 tests cover frame validation, bus arbitration, ECU scheduling, logging/replay round-trips, the native CRC-15 (checked against a pure-Python reference implementation), all six detection rules, the stats engine, dashboard rendering, full simulator integration across every attack scenario, and SocketCAN frame encode/decode.

Two of those tests exercise a live `vcan0` interface and skip automatically if the kernel has no CAN support. To run them locally on Linux:
```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
PYTHONPATH=. python -m pytest tests/test_socketcan.py -v
```
CI runs these for real against `vcan0` on every push.

## License

MIT. See LICENSE.
