"""Builds a Lambda zip: handler + shared/ + Linux versions of the libraries.

Run from the flowdesk folder with:  python -m scripts.build_lambda lead_intake
"""

import shutil
import subprocess
import sys
from pathlib import Path

PYTHON_VERSION = "3.12"  # must match the Lambda runtime


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.build_lambda <lambda folder name>")
    name = sys.argv[1]
    source = Path("lambdas") / name
    if not (source / "handler.py").exists():
        raise SystemExit(f"No handler.py in {source}")

    build = Path("build") / name
    shutil.rmtree(build, ignore_errors=True)
    build.mkdir(parents=True)

    # Linux versions of the libraries, because Lambda runs on Linux, not Windows.
    subprocess.run([
        sys.executable, "-m", "pip", "install", "requests",
        "--target", str(build),
        "--platform", "manylinux2014_x86_64",
        "--implementation", "cp",
        "--python-version", PYTHON_VERSION,
        "--only-binary=:all:",
        "--quiet",
    ], check=True)

    shutil.copytree("shared", build / "shared",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(source / "handler.py", build / "handler.py")

    zip_path = shutil.make_archive(str(Path("build") / name), "zip", build)
    print(f"Built {zip_path}")


if __name__ == "__main__":
    main()