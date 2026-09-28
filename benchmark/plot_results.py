from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PLOTS = RESULTS / "plots"
PLOTS.mkdir(exist_ok=True)

files = sorted(RESULTS.glob("summary_*.csv"))
if not files:
    raise SystemExit("No benchmark CSV found in results/")

df = pd.read_csv(files[-1])

for metric in ["p50_ms", "p95_ms", "p99_ms", "overall_block_rate_pct", "context_attack_block_rate_pct", "role_attack_block_rate_pct", "approx_rps"]:
    plt.figure(figsize=(8, 5))
    plt.bar(df["mode"], df[metric])
    plt.title(metric)
    plt.xlabel("Gateway mode")
    plt.ylabel(metric)
    plt.tight_layout()
    plt.savefig(PLOTS / f"{metric}.png", dpi=180)
    plt.close()

print(f"Saved plots to {PLOTS}")
