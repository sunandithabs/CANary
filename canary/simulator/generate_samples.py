"""
Generates the sample datasets shipped in data/. Run directly:
    python -m canary.simulator.generate_samples
"""

from .simulator import Simulator
from .scenarios import inject_spoofing, inject_malformed_frame, inject_replay_attack, inject_flooding


def generate_normal_traffic(path: str, ticks: int = 5000) -> None:
    sim = Simulator(path)
    sim.run(ticks)
    sim.close()
    print(f"{path}: {sim.detector.alerts.__len__()} alerts on clean traffic "
          f"(should be 0), {sim.stats.total_frames} frames")


def generate_mixed_attack_traffic(path: str) -> None:
    sim = Simulator(path)
    sim.run(1000)  # baseline normal traffic first

    captured = sim.detector.last_payload_for(0x0C0)
    sim.time = sim.detector.last_seen_for(0x0C0) + 0.0005
    inject_replay_attack(sim, captured)
    sim.run(50)

    inject_spoofing(sim)
    sim.run(50)

    inject_malformed_frame(sim)
    sim.run(50)

    inject_flooding(sim, frame_count=100)
    sim.run(200)

    sim.close()
    print(f"{path}: {len(sim.detector.alerts)} alerts on attack traffic "
          f"(should be > 0), {sim.stats.total_frames} frames")
    for alert in sim.detector.alerts:
        print(f"  {alert}")


if __name__ == "__main__":
    generate_normal_traffic("data/sample_logs/normal_traffic.csv")
    generate_mixed_attack_traffic("data/attack_scenarios/mixed_attacks.csv")
