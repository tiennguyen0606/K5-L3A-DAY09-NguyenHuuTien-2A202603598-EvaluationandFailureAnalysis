"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def _metric_index(spec: dict) -> dict[str, dict]:
    return {m["id"]: m for m in spec.get("metrics") or []}


def _slice_index(spec: dict) -> dict[str, dict]:
    return {s["name"]: s for s in spec.get("slices") or []}


def _looser_threshold(new_th: dict, old_th: dict) -> list[str]:
    problems = []
    if "max" in old_th and new_th.get("max", old_th["max"]) > old_th["max"]:
        problems.append("max rose")
    if "min" in old_th and new_th.get("min", old_th["min"]) < old_th["min"]:
        problems.append("min fell")
    if "max_increase" in old_th and new_th.get("max_increase", old_th["max_increase"]) > old_th["max_increase"]:
        problems.append("max_increase rose")
    if old_th.get("no_significant_drop") and not new_th.get("no_significant_drop"):
        problems.append("no_significant_drop dropped")
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate."""
    problems: list[str] = []

    for mid, val in (pr.get("metrics") or {}).items():
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            problems.append(f"metric {mid} is nan/inf")

    items = int(pr.get("manifest", {}).get("items") or 0)
    seeds = list(pr.get("manifest", {}).get("seeds") or [])
    expected_rows = items * len(seeds)
    if len(pr.get("rows") or []) != expected_rows:
        problems.append(f"row count {len(pr.get('rows') or [])} != items×seeds ({expected_rows})")

    pr_keys = {(r["item_id"], r["seed"]) for r in pr.get("rows") or []}
    base_keys = {(r["item_id"], r["seed"]) for r in base.get("rows") or []}
    if pr_keys != base_keys:
        problems.append("(item_id, seed) set differs from baseline")

    if pr.get("evaluator_failures"):
        problems.append("evaluator_failures non-empty")

    graded = [m["id"] for m in spec.get("metrics") or [] if m["id"] in GRADERS]
    for r in pr.get("rows") or []:
        for mid in graded:
            if mid in r and r[mid] is None:
                problems.append(f"row {r.get('item_id')}@{r.get('seed')} metric {mid} is None")
                break
        else:
            continue
        break

    if base_spec is not None and base_spec.get("eval_set_version") == spec.get("eval_set_version"):
        old_m = _metric_index(base_spec)
        new_m = _metric_index(spec)
        for mid, old in old_m.items():
            new = new_m.get(mid)
            if new is None:
                problems.append(f"metric {mid} removed (ratchet)")
                continue
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"metric {mid} no longer blocking (ratchet)")
            for tip in _looser_threshold(new.get("threshold") or {}, old.get("threshold") or {}):
                problems.append(f"metric {mid} loosened: {tip}")
        old_s = _slice_index(base_spec)
        new_s = _slice_index(spec)
        for name, old in old_s.items():
            new = new_s.get(name)
            if new is None:
                problems.append(f"slice {name} removed (ratchet)")
                continue
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"slice {name} no longer blocking (ratchet)")
            old_th = {k: old[k] for k in ("min", "max", "max_increase") if k in old}
            if old.get("no_significant_drop"):
                old_th["no_significant_drop"] = True
            new_th = {k: new[k] for k in ("min", "max", "max_increase") if k in new}
            if new.get("no_significant_drop"):
                new_th["no_significant_drop"] = True
            for tip in _looser_threshold(new_th, old_th):
                problems.append(f"slice {name} loosened: {tip}")

    base_slices: dict[str, tuple[str, ...]] = {}
    for r in base.get("rows") or []:
        base_slices[r["item_id"]] = tuple(sorted(r.get("slices") or []))
    for r in pr.get("rows") or []:
        got = tuple(sorted(r.get("slices") or []))
        want = base_slices.get(r["item_id"])
        if want is not None and got != want:
            problems.append(f"slice tags for {r['item_id']} differ from baseline")
            break

    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for sl in spec.get("slices") or []:
        name, metric = sl["name"], sl["metric"]
        per = per_item(pr, metric, slice_name=name)
        value = (sum(per.values()) / len(per)) if per else None
        verdict, note = "ok", ""
        if value is None:
            verdict = "missing"
        elif "min" in sl and value < sl["min"]:
            verdict = "fail"
        elif "max" in sl and value > sl["max"]:
            verdict = "fail"
        if sl.get("no_significant_drop") and value is not None:
            a = per_item(pr, metric, slice_name=name)
            b = per_item(base, metric, slice_name=name)
            keys = sorted(set(a) & set(b))
            if keys:
                d, lo, hi = stats.paired_bootstrap(
                    [a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                )
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        sid = f"slice:{name}/{metric}"
        if verdict != "ok" and sl.get("blocking"):
            blocked.append(sid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if sl.get("blocking") else "warn")
        th = {k: sl[k] for k in ("min", "max", "no_significant_drop") if k in sl}
        lines.append(f"  {sid:<22} {value!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
