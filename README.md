# canary
[![tests](https://github.com/sunandithabs/canary/actions/workflows/tests.yml/badge.svg)](https://github.com/sunandithabs/canary/actions/workflows/tests.yml)

can bus intrusion detection framework.
can, plus "canary in the coal mine." runs on almost every car, tractor, and industrial machine built in the last thirty years.

---

## problem

modern vehicles run 50-100+ ecus (engine, brakes, steering, infotainment) all talking over a shared can bus. can was designed in the 1980s for a closed, trusted network with no authentication, no encryption. any node can send a frame claiming to be any other node.

that stopped being safe once cars got bluetooth, cellular modems, and usb ports. an attacker who reaches the bus, through an infotainment exploit, an obd-ii dongle, or a compromised telematics unit and then inject frames that look completely legitimate to every other ecu on the network.

## why can attacks matter

miller and valasek's 2015 jeep cherokee remote takeover proved can injection can control steering, braking, and acceleration. the attack surface has only grown since, and can still has no defense against a node lying about who it is.

catching this means watching behavior, not checking protocol correctness. a malicious frame is usually a perfectly well-formed can frame. canary is built around that fact.

## architecture
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

everything downstream of the bus talks to it only through `businterface.subscribe()` and `.offer()`. the logger, detector, and stats engine don't know or care whether frames come from a simulation or a real `vcan0` interface.

## features

- multi-ecu simulation with realistic timing, jitter, and priority-based arbitration
- csv traffic logging plus timing-accurate replay from log files
- rule-based detection: id spoofing, malformed frames, impossible message frequency, flooding/dos, replay attacks
- severity-tagged alerts, low through critical
- live terminal dashboard showing bus utilization, arbitration latency, top talkers, and recent alerts
- a native c component for the crc-15 checksum, bridged via `ctypes`, the same way real can controllers compute frame integrity at the bit level
- socketcan support via a raw `af_can` socket, no external library. works against a real interface (`vcan0` or physical hardware) with zero changes to the detector, logger, or dashboard
- 46 unit and integration tests (2 socketcan tests skip automatically outside a can-capable kernel.
- pre-generated sample datasets: clean traffic and a mixed multi-attack scenario

## demo

```bash
pip install -r requirements.txt
bash canary/native/build.sh   
PYTHONPATH=. python -m canary.simulator.generate_samples
```

this regenerates `data/sample_logs/normal_traffic.csv` (0 alerts) and `data/attack_scenarios/mixed_attacks.csv` (spoofing, malformed frame, flooding, and replay all caught), printing each alert as it fires.

to run the live dashboard against a running simulation:
```python
from canary.simulator import Simulator
from canary.dashboard import run_dashboard

sim = Simulator("live_demo.csv")
run_dashboard(sim.stats, sim.detector)
```

## how it works

1. ecus send frames on a schedule with realistic jitter (`canary/ecu/`).
2. simulatedbus resolves priority via a min-heap on arbitration id — lower id wins, same as real can arbitration.
3. logger, detector, and statsengine each subscribe independently. none of them know the others exist.
4. detector tracks per-id baselines (expected source, size, period) and runs six independent rules against every frame, producing severity-tagged alerts.
5. statsengine aggregates telemetry — rates, latency, top talkers — purely from what it observes. it never touches bus internals.
6. dashboard renders both and owns nothing else.

## design decisions

arbitration is modeled as priority scheduling, not bit-level contention. that gets the real effect such as latency under load, deterministic priority, without simulating electrical signaling nothing downstream needs.

a few protocol features are left out on purpose: bit-stuffing, ack slots, error frames, remote frames, overload frames, the bus-off state machine, exact bit-level arbitration. none of them change what the detector can observe, so building them would just be chasing can-spec completeness instead of detection tooling.

`businterface` took zero changes to the detector, logger, or ecu code. that's the payoff of subscriber-pattern decoupling from day one.

two real bugs only showed up at integration time, ecu frames defaulted to wall-clock timestamps instead of simulated time, and the stats engine mixed wall-clock latency against simulated-time frames. both got fixed with explicit, documented clock-passing rather than patched over. see `simulator.__init__` and `statsengine.observe()`.

## future work

- can-fd support (larger payloads, flexible data rate)
- uds (unified diagnostic services) simulation
- j1939 (heavy-vehicle protocol layer)
- iso-tp (multi-frame transport protocol)
- ml-based anomaly detection, as a stretch goal

## running tests

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

46 tests cover frame validation, bus arbitration, ecu scheduling, logging/replay round-trips, the native crc-15 (checked against a pure-python reference implementation), all six detection rules, the stats engine, dashboard rendering, full simulator integration across every attack scenario, and socketcan frame encode/decode.

two of those tests exercise a live `vcan0` interface and skip automatically if the kernel has no can support. to run them locally on linux:
```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
PYTHONPATH=. python -m pytest tests/test_socketcan.py -v
```

## license

mit. see license.
