# OpenJev roadmap

## 0.1 — open decision runtime
Status: implemented in this package.

- typed `Noul`, `Choice`, `Score`;
- strict response validation;
- probability normalization;
- confidence metrics;
- OpenAI-compatible provider;
- offline mock provider;
- Goal Loop auditor integration;
- privacy-hashed tamper-evident JSONL events.

## 0.2 — evaluation harness

Build a first-party eval set from real, consented Goal Loop sessions.

Each case should contain:
- state snapshot;
- typed questions;
- human-reviewed labels or probability targets;
- severity/cost of false positive and false negative;
- expected deterministic hard-gate outcome.

Metrics:
- Brier score for Noul;
- log loss / top-1 for Choice;
- expected-score MAE + calibration for Score;
- completion false-positive rate;
- missed-trigger rate;
- unnecessary-escalation rate;
- cost and latency per audit.

## 0.3 — multi-provider benchmark

Run the same OpenJev contract over:
- local open-weight models;
- OpenAI-compatible hosted models;
- other supported providers via adapters.

Do not optimize on the public benchmark only. Keep a private holdout set.

## 0.4 — trained open decision model

Goal: stop paying a generative-model output tax for narrow decisions.

Clean training path:
1. collect user-owned / consented states + labels;
2. generate additional synthetic states from open models, but have humans or
   programmatic invariants verify labels;
3. encode state + question + criteria;
4. train heads for:
   - binary probability (`Noul`);
   - categorical distribution (`Choice`);
   - ordinal distribution (`Score`);
5. calibrate on held-out data (temperature / isotonic / Dirichlet as appropriate);
6. publish model card, data provenance, eval splits, and limitations;
7. serve locally, optionally through vLLM-compatible infrastructure if architecture permits.

Important boundary:
- do not use proprietary Jev outputs as a hidden teacher unless the service terms
  explicitly authorize that use;
- do not claim Jev-equivalent performance without independent evidence.

## 1.0 — portable decision service

- Python + TypeScript SDKs;
- stable HTTP schema;
- local server;
- pluggable model backends;
- confidence-aware policies;
- trace/replay;
- calibration dashboards;
- agent integrations.
