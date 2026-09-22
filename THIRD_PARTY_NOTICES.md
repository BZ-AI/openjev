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

OpenJev does **not** contain TypeSafe AI's proprietary Jev model, weights, hidden
architecture, private training data, private training code, or private sampler.

OpenJev also does not attempt to discover or reverse-engineer proprietary source code
behind TypeSafe AI's hosted service.

Where a future contributor copies or adapts source code from a third-party
MIT/Apache repository rather than independently reimplementing a concept, that file
must preserve the upstream copyright/license notice and be recorded here.

Names and trademarks remain the property of their respective owners.
