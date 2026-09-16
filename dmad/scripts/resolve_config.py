"""Resolve the layered DMAD project config and print a key as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_utils import get_key, merge_layers  # noqa: E402

LAYERS = (
    "_dmad/config.toml",
    "_dmad/config.user.toml",
    "_dmad/custom/config.toml",
    "_dmad/custom/config.user.toml",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Project root folder.")
    parser.add_argument(
        "--key",
        default=None,
        help="Dotted path, e.g. runtime.user_name. Omit for the whole config.",
    )
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    config = merge_layers([root / layer for layer in LAYERS])
    # Windows consoles/pipes default to cp1252, which cannot encode agent icons.
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(get_key(config, args.key), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
