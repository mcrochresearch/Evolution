# Error Signatures — Pattern Database

> The agent's immune system. Once an error is encountered and solved,
> the antibody (solution) is remembered for faster response next time.
> **This file is maintained by engine/error_signatures.py. Do not edit manually.**

## How It Works

1. **EXTRACT**: Parse error output to identify a normalized signature
2. **MATCH**: When a new error occurs, check if it matches a known signature
3. **RESOLVE**: Track which fixes work for each signature
4. **LEARN**: Build confidence in resolutions based on success rate

## Error Types Recognized

| Type | Pattern | Example |
|------|---------|---------|
| python_exception | `SomeError: message` | `ValueError: invalid literal` |
| python_traceback | `File "path", line N` | `File "app.py", line 42` |
| node_error | `TypeError: message` | `TypeError: undefined is not a function` |
| test_failure | `FAIL test_name` | `FAIL test_auth_flow` |
| build_error | `error[E1234]: message` | Rust compile errors |
| lint_error | `line:col error message` | ESLint/Ruff output |
| import_error | `ModuleNotFoundError: module` | Missing dependencies |
| permission_error | `PermissionError: detail` | File access issues |
| timeout_error | `TimeoutError` | Operation timeouts |
| connection_error | `ConnectionError` | Network failures |

## Signature Database Stats

_No signatures extracted yet. Errors encountered during evolution will be automatically catalogued._

## Commands

- Extract: `./engine/evolve error-extract "error output text"`
- Match: `./engine/evolve error-match "error output text"`
- Resolve: `./engine/evolve error-resolve <sig_id> "fix description" true`
- List: `./engine/evolve error-list [--unresolved]`
- Stats: `./engine/evolve error-stats`

State is stored in `evolution/.state/error_signatures.json`.
