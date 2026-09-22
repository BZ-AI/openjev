# Contributing

Contributions are welcome.

## Clean-room rule

Do not contribute proprietary Jev source, weights, training data, hidden prompts,
service-extracted implementation details, or material obtained by bypassing access
controls.

Publicly licensed source may be used only in compliance with its license and with
the required notices preserved.

## Development

```bash
python -m pip install -e '.[dev]'
pytest -q
ruff check .
```

## Design principle

Prefer:

```text
deterministic rule in code
+ narrow semantic model judgment
```

over one large prompt that asks a model to control the whole workflow.
