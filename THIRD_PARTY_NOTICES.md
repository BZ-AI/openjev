# Third-party notices and clean-room boundary

OpenJev is an independent implementation.

During design, the maintainers reviewed public TypeSafe AI materials and its
open-source repositories, including the MIT-licensed:

- `typesafe-ai/skills`
- `typesafe-ai/system-one-adapter-python`
- `typesafe-ai/typesafe-sdk-python`
- `typesafe-ai/typesafe-sdk-js`

Those repositories document public concepts such as typed `Choice`, `Noul`, and
`Score` questions, probability distributions, confidence handling, and provider
adapters.

OpenJev v0.2 also interoperates with public open-source work without vendoring its
model code or weights:

- `NandhaKishorM/laya` — Apache-2.0; optional local typed-decision backend.
- `MohammadAsadi-7/laya-mlx` — MLX port used through an optional adapter on Apple Silicon.
- `yibie/laya-jev-lab` — MIT; the file `benchmarks/yibie_support_40.json` is copied from
  its 40-case support benchmark. The upstream MIT text is preserved in
  `licenses/YIBIE_LAYA_JEV_LAB_MIT.txt`.
- `wdobry/laya-playground` — MIT benchmark methodology. OpenJev implements a compatible
  converter, but intentionally does not redistribute the benchmark's source texts because
  some underlying datasets impose separate restrictions.

The Laya adapters call the upstream packages through their documented public APIs. No Laya
source code or model weights are copied into OpenJev.

OpenJev does **not** contain TypeSafe AI's proprietary Jev model, weights, hidden
architecture, private training data, private training code, or private sampler.

OpenJev also does not attempt to discover or reverse-engineer proprietary source code
behind TypeSafe AI's hosted service.

Where a future contributor copies or adapts source code from a third-party
MIT/Apache repository rather than independently reimplementing a concept, that file
must preserve the upstream copyright/license notice and be recorded here.

Names and trademarks remain the property of their respective owners.
