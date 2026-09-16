#!/usr/bin/env python3
"""Install or sync the DMAD agent framework into a target project.

Examples:
    python install.py --target ../my-app --providers claude copilot
    python install.py --target ../my-app            # re-sync using recorded providers
    python install.py --list-providers
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent
PAYLOAD = PACKAGE_ROOT / "dmad"

sys.path.insert(0, str(PAYLOAD / "scripts"))

from config_utils import agent_layers, load_toml, merge_layers  # noqa: E402

DEFAULT_PROVIDERS = ("claude", "copilot")
RECORD_PATH = "_dmad/install.toml"


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def safe_id(value: str) -> str:
    """Reject ids that could escape the target directory when used in a path."""
    if not value or "/" in value or "\\" in value or value.startswith(".") or ".." in value:
        fail(f"unsafe id in manifest: {value!r}")
    return value


def yaml_scalar(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def seed(source: Path, dest: Path, substitutions: dict[str, str] | None = None) -> bool:
    """Write `dest` from `source` only when it does not already exist."""
    if dest.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8")
    for token, replacement in (substitutions or {}).items():
        text = text.replace(token, replacement)
    dest.write_text(text, encoding="utf-8")
    return True


def install_scripts(target: Path) -> None:
    dest = target / "_dmad" / "scripts"
    dest.mkdir(parents=True, exist_ok=True)
    for script in sorted((PAYLOAD / "scripts").glob("*.py")):
        shutil.copy2(script, dest / script.name)


def install_agent_sources(target: Path, agents: dict[str, Any]) -> None:
    templates = PAYLOAD / "templates" / "custom"
    for agent_id, spec in agents.items():
        source = PAYLOAD / spec["source"] / "customize.toml"
        if not source.is_file():
            fail(f"agent source missing: {source}")
        dest = target / "_dmad" / "agents" / agent_id / "customize.toml"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)

        custom = target / "_dmad" / "custom"
        seed(templates / "agent.toml", custom / f"{agent_id}.toml", {"{{agent_id}}": agent_id})
        seed(
            templates / "agent.user.toml",
            custom / f"{agent_id}.user.toml",
            {"{{agent_id}}": agent_id},
        )


def install_config(target: Path, project_name: str, user_name: str) -> None:
    templates = PAYLOAD / "templates"
    subs = {"{{project_name}}": project_name, "{{user_name}}": user_name}
    seed(templates / "config.toml", target / "_dmad" / "config.toml", subs)
    seed(templates / "config.user.toml", target / "_dmad" / "config.user.toml")
    seed(templates / "dmad-gitignore", target / "_dmad" / ".gitignore")
    seed(templates / "custom" / "config.toml", target / "_dmad" / "custom" / "config.toml")
    seed(
        templates / "custom" / "config.user.toml",
        target / "_dmad" / "custom" / "config.user.toml",
    )
    seed(templates / "custom" / "gitignore", target / "_dmad" / "custom" / ".gitignore")


def render_adapter(
    target: Path, agent_id: str, spec: dict[str, Any], provider: dict[str, Any]
) -> str:
    """Write one provider-specific wrapper around the shared agent body."""
    resolved = merge_layers(agent_layers(target, agent_id)).get("agent", {})
    name = resolved.get("name", agent_id)
    title = resolved.get("title", "Agent")
    icon = resolved.get("icon", "")
    description = (
        f"{resolved.get('description', '')} "
        f"Use when the user asks to talk to {name} or requests the {title.lower()}."
    ).strip()

    fields = {
        "agent": agent_id,
        "name": name,
        "title": title,
        "icon": icon,
        "description": description,
    }

    body = (PAYLOAD / spec["source"] / "agent.md").read_text(encoding="utf-8")
    # Literal token swap, not str.format — the body also contains {project-root},
    # which must survive as a runtime placeholder.
    for token, value in (
        ("{agent-id}", agent_id),
        ("{agent-name}", name),
        ("{agent-title}", title),
        ("{agent-icon}", icon),
    ):
        body = body.replace(token, value)

    frontmatter = provider.get("frontmatter") or {}
    if frontmatter:
        lines = [f"{key}: {yaml_scalar(value.format(**fields))}" for key, value in frontmatter.items()]
        body = "---\n" + "\n".join(lines) + "\n---\n\n" + body

    relative = provider["target"].format(**fields)
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(body, encoding="utf-8")
    return relative


def write_record(
    target: Path, version: str, providers: list[str], agents: list[str], generated: list[str]
) -> None:
    def array(values: list[str]) -> str:
        return "[" + ", ".join(f'"{value}"' for value in values) + "]"

    content = (
        "# Generated by install.py. Records what this project has installed so a\n"
        "# bare `python install.py --target .` can re-sync the same selection.\n\n"
        "[install]\n"
        f'version = "{version}"\n'
        f'installed_at = "{datetime.now(timezone.utc).isoformat(timespec="seconds")}"\n'
        f"providers = {array(providers)}\n"
        f"agents = {array(agents)}\n"
        f"generated = {array(generated)}\n"
    )
    (target / RECORD_PATH).write_text(content, encoding="utf-8")


def main() -> int:
    manifest = load_toml(PAYLOAD / "manifest.toml")
    if not manifest:
        fail(f"manifest not found at {PAYLOAD / 'manifest.toml'}")

    all_providers: dict[str, Any] = manifest["providers"]
    agents: dict[str, Any] = manifest["agents"]
    version = manifest["framework"]["version"]

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--target", default=".", help="Project to install into.")
    parser.add_argument(
        "--providers",
        nargs="+",
        metavar="NAME",
        help=f"AI tools to generate for, or 'all'. Available: {', '.join(all_providers)}.",
    )
    parser.add_argument("--project-name", help="Seeds core.project_name on first install.")
    parser.add_argument("--user-name", help="Seeds runtime.user_name on first install.")
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete adapter files from a previous install that are no longer selected.",
    )
    parser.add_argument("--list-providers", action="store_true", help="List providers and exit.")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")

    if args.list_providers:
        for key, provider in all_providers.items():
            print(f"  {key:<18} {provider['label']}\n  {'':<18} -> {provider['target']}")
        return 0

    target = Path(args.target).resolve()
    if not target.is_dir():
        fail(f"target is not a directory: {target}")

    previous = load_toml(target / RECORD_PATH).get("install", {})

    if args.providers:
        selected = list(all_providers) if args.providers == ["all"] else args.providers
    else:
        selected = previous.get("providers") or list(DEFAULT_PROVIDERS)

    unknown = [name for name in selected if name not in all_providers]
    if unknown:
        fail(f"unknown provider(s): {', '.join(unknown)}. Try --list-providers.")

    agent_ids = [safe_id(agent_id) for agent_id in agents]

    install_scripts(target)
    install_agent_sources(target, agents)
    install_config(
        target,
        args.project_name or previous.get("project_name") or target.name,
        args.user_name or "there",
    )

    generated: list[str] = []
    for agent_id, spec in agents.items():
        for provider_name in selected:
            generated.append(
                render_adapter(target, agent_id, spec, all_providers[provider_name])
            )

    stale = [path for path in previous.get("generated", []) if path not in generated]
    tracked = list(generated)
    if stale:
        if args.prune:
            for path in stale:
                candidate = target / path
                if candidate.is_file():
                    candidate.unlink()
                    print(f"  removed {path}")
        else:
            print("\nStale adapter files from a previous install (re-run with --prune to delete):")
            for path in stale:
                print(f"  {path}")
            # Keep tracking them, otherwise a later --prune can no longer find them.
            tracked += stale

    write_record(target, version, selected, agent_ids, tracked)

    print(f"\nDMAD {version} installed into {target}")
    print(f"  agents:    {', '.join(agent_ids)}")
    print(f"  providers: {', '.join(selected)}")
    for path in generated:
        print(f"  generated  {path}")
    print("\nEdit _dmad/config.toml, then customize personas in _dmad/custom/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
