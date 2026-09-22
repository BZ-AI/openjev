# Security policy

Please do not post credentials, private prompts, private model artifacts, access tokens,
or user data in public issues.

For security-sensitive reports, open a minimal issue that contains no exploit secret or
private data and asks maintainers for a private reporting channel.

OpenJev treats external model/provider output as untrusted input. Provider responses must
pass schema and probability validation before they can affect a workflow. Deterministic
application safety/completion gates must not be overridable by a semantic model decision.
