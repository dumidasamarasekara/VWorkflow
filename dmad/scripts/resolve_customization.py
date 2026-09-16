"""Resolve an agent's layered customize.toml and print a key as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_utils import agent_layers, get_key, merge_layers  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent",
        required=True,
        help="Agent id, e.g. dmad-agent-business-analyst.",
    )
    parser.add_argument("--project-root", default=".", help="Project root folder.")
    parser.add_argument(
        "--key",
        default=None,
        help="Dotted path, e.g. agent. Omit for the whole customization.",
    )
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    merged = merge_layers(agent_layers(root, args.agent))
    # Windows consoles/pipes default to cp1252, which cannot encode agent icons.
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(get_key(merged, args.key), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
