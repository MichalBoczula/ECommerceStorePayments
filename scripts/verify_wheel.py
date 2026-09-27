"""Check that the built wheel installs and imports outside the source tree."""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    wheels = list(Path("dist").glob("ecommerce_store_payments-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected one Payments wheel in dist/, found {len(wheels)}")

    with TemporaryDirectory(prefix="payments-wheel-") as directory:
        root = Path(directory)
        environment = root / "venv"
        subprocess.run(["uv", "venv", "--no-project", "--python", sys.executable, str(environment)], check=True)
        interpreter = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run(
            ["uv", "pip", "install", "--python", str(interpreter), "--no-deps", str(wheels[0].resolve())],
            check=True,
        )
        subprocess.run(
            [
                str(interpreter),
                "-c",
                "from ecommerce_store_payments.domain.aggregates.payments.payment import Payment; "
                "assert Payment.__module__.startswith('ecommerce_store_payments.')",
            ],
            cwd=root,
            check=True,
        )


if __name__ == "__main__":
    main()
