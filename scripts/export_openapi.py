#!/usr/bin/env python3
"""Export and lint the database-free generated OpenAPI contract."""

import argparse
import sys
from pathlib import Path

from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

from scripts.openapi_contract import export


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/verification/openapi.json"))
    args = parser.parse_args()
    try:
        operations, cases = export(args.output)
    except (AssertionError, KeyError, OSError, TypeError, ValueError, OpenAPIValidationError) as error:
        print(f"OpenAPI contract error: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"Validated {operations} operations and {cases} acceptance outcomes; exported {args.output}")


if __name__ == "__main__":
    main()
