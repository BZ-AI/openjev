# Reproducible benchmarks

OpenJev v0.2 includes a measurement harness because routing decisions should be based on
your traffic, not a screenshot or a vendor headline.

The harness measures:

- top-1 accuracy;
- expected calibration error (ECE);
- Brier score;
- score MAE for ordinal questions;
- mean / p50 / p95 latency;
- results grouped by difficulty tier, domain, language and primitive;
- local-first cascade threshold sweeps.

## Benchmark 1 — 40-case Chinese support cascade

`benchmarks/yibie_support_40.json` is the MIT-licensed 40-case benchmark from
`yibie/laya-jev-lab`, retained with its upstream license notice.

Run Laya only:

```bash
pip install -e ".[laya]"
openjev-bench benchmarks/yibie_support_40.json \
  --fast laya \
  --output reports/support-laya.json
```

Run the local-first cascade against the hosted Jev API only when you explicitly want to
make those remote calls:

```bash
set TYPESAFE_API_KEY=...
openjev-bench benchmarks/yibie_support_40.json \
  --fast laya \
  --strong jev \
  --thresholds 0.30,0.40,0.50,0.60,0.70,0.80,0.90,0.95 \
  --output reports/support-cascade.json
```

On Apple Silicon, use `--fast laya-mlx` after installing the `laya-mlx` extra.

The report stores per-case outputs plus the sweep. Do not assume the upstream 0.60
threshold is correct for another model version or another workload.

When `--strong` is supplied, the benchmark intentionally evaluates the strong backend on every case so every threshold can be replayed from the same paired results. For a paid hosted backend, that means one strong-provider call per benchmark case; use `--limit` for a small smoke run first.

## Benchmark 2 — 500-example multi-domain comparison

`wdobry/laya-playground` compares Laya and Jev on five 100-example tasks. Some of its
source datasets restrict redistribution, so OpenJev does **not** copy those texts.

Rebuild them in a separate checkout, under the source datasets' own terms:

```bash
git clone https://github.com/wdobry/laya-playground
cd laya-playground
python eval/build_dataset.py
cd ..
python openjev/tools/import_laya_playground_eval.py \
  laya-playground \
  openjev/benchmarks/laya_playground_500.local.jsonl
```

Then run the same OpenJev harness:

```bash
cd openjev
openjev-bench benchmarks/laya_playground_500.local.jsonl \
  --fast laya \
  --strong jev \
  --output reports/playground-500.json
```

The generated `*.local.jsonl` should stay local unless you independently confirm every
source dataset permits redistribution.

## What to look for

A useful routing policy answers more than "which model has the higher average accuracy?"

Inspect at least:

1. clear vs ambiguous vs boundary/OOD traffic;
2. confident-and-wrong cases;
3. calibration, not only top-1 accuracy;
4. high-cardinality choice questions;
5. per-language performance;
6. the latency cost of escalation;
7. whether a deterministic rule can replace the model call entirely.

For Goal Loop specifically, add false-completion rate, missed-trigger rate and
unnecessary-escalation rate before using the router to authorize completion.
