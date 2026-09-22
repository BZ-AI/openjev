from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .benchmark import cascade_sweep, evaluate_cases, load_cases, render_summary_table
from .engine import OpenJev
from .providers import JevProvider, LayaProvider, OpenAICompatibleProvider


def _thresholds(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _engine(kind: str, *, model: str | None, base_url: str | None, role: str) -> OpenJev:
    if kind == "laya":
        return OpenJev(LayaProvider(package="laya", checkpoint=model))
    if kind == "laya-mlx":
        return OpenJev(LayaProvider(package="laya_mlx", checkpoint=model))
    if kind == "jev":
        return OpenJev(
            JevProvider(
                model=model or "jev-latest",
                base_url=base_url or "https://api.typesafe.ai",
            )
        )
    if kind == "openai":
        if not model:
            raise SystemExit(f"--{role}-model is required for the openai backend")
        return OpenJev(
            OpenAICompatibleProvider(
                model=model,
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url=base_url or "https://api.openai.com/v1",
            )
        )
    raise SystemExit(f"unsupported backend {kind!r}")


def _close(engine: OpenJev | None) -> None:
    if engine is None:
        return
    close = getattr(engine.provider, "close", None)
    if callable(close):
        close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reproducible OpenJev local-vs-strong benchmark and cascade sweep"
    )
    parser.add_argument("dataset", type=Path, help="OpenJev benchmark JSON or JSONL")
    parser.add_argument(
        "--fast",
        choices=["laya", "laya-mlx", "jev", "openai"],
        default="laya",
        help="Fast/local backend (default: laya)",
    )
    parser.add_argument(
        "--strong",
        choices=["laya", "laya-mlx", "jev", "openai"],
        default=None,
        help="Optional escalation backend. No paid/remote backend is called unless explicitly selected.",
    )
    parser.add_argument("--fast-model", default=None)
    parser.add_argument("--strong-model", default=None)
    parser.add_argument("--fast-base-url", default=None)
    parser.add_argument("--strong-base-url", default=None)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--thresholds",
        type=_thresholds,
        default=_thresholds("0.30,0.40,0.50,0.60,0.70,0.80,0.90,0.95"),
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("dataset contains no benchmark cases")

    fast = _engine(args.fast, model=args.fast_model, base_url=args.fast_base_url, role="fast")
    strong = None
    try:
        fast_report = evaluate_cases(fast, cases, provider_name=args.fast)
        print(render_summary_table(fast_report))

        output: dict[str, object] = {"fast": fast_report.model_dump(mode="json")}
        if args.strong:
            strong = _engine(
                args.strong,
                model=args.strong_model,
                base_url=args.strong_base_url,
                role="strong",
            )
            strong_report = evaluate_cases(strong, cases, provider_name=args.strong)
            print(render_summary_table(strong_report))
            sweep = cascade_sweep(fast_report, strong_report, args.thresholds)
            output["strong"] = strong_report.model_dump(mode="json")
            output["cascade"] = [point.model_dump(mode="json") for point in sweep]

            print("\nthreshold  escalate  accuracy  ece    mean_ms  p95_ms")
            for point in sweep:
                print(
                    f"{point.threshold:>8.2f}  "
                    f"{point.escalation_rate:>8.1%}  "
                    f"{point.accuracy:>8.1%}  "
                    f"{point.ece:>5.3f}  "
                    f"{point.mean_latency_ms:>7.1f}  "
                    f"{point.p95_latency_ms:>6.1f}"
                )

        encoded = json.dumps(output, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n", encoding="utf-8")
            print(f"\nwrote {args.output}")
        else:
            print("\nUse --output report.json to save per-case results.")
    finally:
        _close(strong)
        _close(fast)


if __name__ == "__main__":
    main()
