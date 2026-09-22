# TypeSafe AI public GitHub review — 2026-09-22

Scope: the ten public repositories visible under the official `typesafe-ai` GitHub organization.

## Directly relevant to Goal Loop / OpenJev

### 1. `typesafe-ai/skills`
- Purpose: agent-facing guidance for composing typed System One decisions.
- License: MIT.
- Relevance: **HIGH**.
- Useful ideas:
  - code owns deterministic workflow;
  - model supplies narrow semantic judgment;
  - keep questions atomic and independently useful;
  - thresholds must be evaluated on target data;
  - typed output guarantees interface, not truth.
- Goal Loop use: redesign fuzzy auditor checks as typed questions rather than a giant completion prompt.

### 2. `typesafe-ai/system-one-adapter-python`
- Purpose: emulate the System One evaluation shape using OpenAI-compatible, Anthropic, or Gemini LLM APIs.
- License: MIT.
- Relevance: **VERY HIGH**.
- Useful ideas:
  - provider seam;
  - strict structured output;
  - Choice/Noul/Score;
  - probability normalization;
  - confidence metrics;
  - retry malformed structure;
  - debug/usage accounting.
- Goal Loop use: this is the closest public blueprint for a portable decision layer.

### 3. `typesafe-ai/typesafe-sdk-python`
- Purpose: Python client and question/answer types for TypeSafe hosted API.
- License: MIT.
- Relevance: **HIGH** for API ergonomics, LOW for model implementation.
- Goal Loop use: typed schemas, strict validation, clear error boundary.

### 4. `typesafe-ai/typesafe-sdk-js`
- Purpose: JavaScript/TypeScript SDK.
- License: MIT.
- Relevance: **HIGH** if Goal Loop's local auditor remains Node/`.mjs`.
- Goal Loop use: mirror ergonomic typed interfaces in a future JS client or bridge.

## Indirectly useful

### 5. `typesafe-ai/daggerverse`
- Purpose: shared Dagger CI/build/security modules.
- License: Apache-2.0.
- Relevance: **MEDIUM**.
- Goal Loop use:
  - dependency audit;
  - GitHub Actions hardening;
  - commit/check-run status monitoring.
- Best use later: release engineering for OpenJev, not decision semantics.

### 6. `typesafe-ai/Overwatch`
- Purpose: local browser for cloud resources/training workloads.
- Root license not found during review.
- Relevance: **LOW to decision semantics, MEDIUM to observability thinking**.
- Goal Loop use: evidence-first local telemetry, append-only logs, resource/job state ideas.
- Do not copy until licensing is clarified.

## Not useful for Goal Loop logic

### 7. `typesafe-ai/LLaDA`
- Purpose: fork/copy of the public LLaDA diffusion-language-model project.
- License found: MIT, copyright upstream author.
- Relevance: **LOW**.
- It is not Jev source and does not reveal Jev architecture.

### 8. `typesafe-ai/vllm`
- Purpose: TypeSafe organization copy/fork of vLLM.
- License: Apache-2.0.
- Relevance: **LOW now / POSSIBLE LATER**.
- Potential later use: serve an actual open trained decision model efficiently.

### 9. `typesafe-ai/pulumi-clickhouse`
- Purpose: ClickHouse Pulumi provider.
- License: Apache-2.0.
- Relevance: **LOW**.
- Potential later use: telemetry infrastructure only; far too heavy for Goal Loop Beta.

### 10. `typesafe-ai/typesafe-ai.github.io`
- Purpose: legacy/static GitHub Pages repository.
- No root README or LICENSE found during review.
- Relevance: **NONE** for Goal Loop/OpenJev implementation.

## Overall conclusion

For Goal Loop, the useful set is not "all ten." It is primarily:

```text
system-one-adapter-python  -> architecture blueprint
skills                     -> composition rules
typesafe-sdk-python/js     -> type/API ergonomics
daggerverse                -> later CI hardening
```

Everything else should be kept out of the first integration to avoid unnecessary scope.
