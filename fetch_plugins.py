from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class FetchPluginsError(Exception):
    pass


@dataclass(frozen=True)
class ExternalPluginSpec:
    marketplace: str
    ref: str | None
    plugins: tuple[str, ...]


FetchMarketplace = Callable[[ExternalPluginSpec, Path], Path]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FetchPluginsError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FetchPluginsError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_external_specs(path: Path) -> list[ExternalPluginSpec]:
    raw_specs = load_json(path)
    if not isinstance(raw_specs, list):
        raise FetchPluginsError(f"{path} must contain a JSON array")

    specs: list[ExternalPluginSpec] = []
    for index, raw_spec in enumerate(raw_specs):
        if isinstance(raw_spec, str):
            marketplace = raw_spec
            ref = None
            plugins = []
        elif isinstance(raw_spec, dict):
            raw_spec_dict = cast(dict[str, Any], raw_spec)
            marketplace = raw_spec_dict.get("marketplace")
            ref = raw_spec_dict.get("ref")
            plugins = raw_spec_dict.get("plugins")
        else:
            raise FetchPluginsError(f"Entry {index} in {path} must be an object or marketplace string")
        if not isinstance(marketplace, str) or not marketplace.strip():
            raise FetchPluginsError(f"Entry {index} in {path} must have a marketplace string")
        if ref is not None and (not isinstance(ref, str) or not ref.strip()):
            raise FetchPluginsError(f"Entry {index} in {path} must have a ref string when ref is present")
        if plugins is None:
            plugins = []
        if not isinstance(plugins, list) or not all(isinstance(plugin, str) and plugin.strip() for plugin in plugins):
            raise FetchPluginsError(f"Entry {index} in {path} must have a plugins string array")
        specs.append(
            ExternalPluginSpec(
                marketplace=marketplace.strip(),
                ref=ref.strip() if isinstance(ref, str) else None,
                plugins=tuple(plugin.strip() for plugin in plugins),
            )
        )
    return specs


def github_url(marketplace: str) -> str:
    if marketplace.startswith("https://") or marketplace.startswith("git@"):
        return marketplace
    if marketplace.count("/") != 1:
        raise FetchPluginsError(
            f"Marketplace '{marketplace}' must be a GitHub owner/repo slug, HTTPS URL, or SSH URL"
        )
    return f"https://github.com/{marketplace}.git"


def clone_marketplace(spec: ExternalPluginSpec, workspace: Path) -> Path:
    destination = workspace / spec.marketplace.replace(":", "_").replace("/", "__")
    command = ["git", "clone", "--depth", "1"]
    if spec.ref is not None:
        command.extend(["--branch", spec.ref])
    command.extend([github_url(spec.marketplace), str(destination)])
    subprocess.run(command, check=True)
    return destination


def marketplace_path(root: Path) -> Path:
    return root / ".claude-plugin" / "marketplace.json"


def marketplace_storage_parts(marketplace: str) -> tuple[str, ...]:
    storage_path = marketplace.removesuffix(".git")
    if storage_path.startswith("https://"):
        storage_path = storage_path.removeprefix("https://")
    elif storage_path.startswith("git@"):
        storage_path = storage_path.removeprefix("git@").replace(":", "/", 1)

    parts = tuple(part for part in storage_path.split("/") if part)
    if not parts or any(part in {".", ".."} for part in parts):
        raise FetchPluginsError(f"Marketplace '{marketplace}' cannot be used as a storage path")
    return parts


def external_plugin_dir(root: Path, marketplace: str) -> Path:
    directory = root / "external_plugins"
    for part in marketplace_storage_parts(marketplace):
        directory /= part
    return directory


def external_skills_dir(root: Path, marketplace: str) -> Path:
    return external_plugin_dir(root, marketplace) / "skills"


def plugin_by_name(marketplace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        raise FetchPluginsError("Marketplace JSON must contain a plugins array")

    result: dict[str, dict[str, Any]] = {}
    for plugin in plugins:
        if not isinstance(plugin, dict):
            raise FetchPluginsError("Marketplace plugins must be objects")
        name = plugin.get("name")
        if not isinstance(name, str) or not name:
            raise FetchPluginsError("Marketplace plugin is missing a name")
        result[name] = plugin
    return result


def resolve_skill_path(external_root: Path, skill_path: str) -> Path:
    clean_path = skill_path.removeprefix("./")
    source = external_root / clean_path
    if not source.is_dir():
        raise FetchPluginsError(f"Skill path does not exist or is not a directory: {skill_path}")
    return source


def plugin_source_root(plugin: dict[str, Any], external_root: Path) -> Path:
    source = plugin.get("source", "./")
    if not isinstance(source, str) or not source.strip():
        name = plugin.get("name", "<unknown>")
        raise FetchPluginsError(f"Plugin '{name}' must have a source string")
    return resolve_skill_path(external_root, source)


def source_plugin_metadata(plugin: dict[str, Any], external_root: Path) -> dict[str, Any] | None:
    metadata_path = plugin_source_root(plugin, external_root) / ".claude-plugin" / "plugin.json"
    if not metadata_path.is_file():
        return None
    metadata = load_json(metadata_path)
    if not isinstance(metadata, dict):
        raise FetchPluginsError(f"{metadata_path} must contain a JSON object")
    return cast(dict[str, Any], metadata)


def infer_skill_paths(plugin: dict[str, Any], external_root: Path) -> list[str]:
    skills_dir = plugin_source_root(plugin, external_root) / "skills"
    if not skills_dir.is_dir():
        name = plugin.get("name", "<unknown>")
        raise FetchPluginsError(f"Plugin '{name}' does not define skills and has no skills directory")

    skill_paths = [f"./{skill_dir.relative_to(external_root).as_posix()}" for skill_dir in sorted(skills_dir.iterdir()) if (skill_dir / "SKILL.md").is_file()]
    if not skill_paths:
        name = plugin.get("name", "<unknown>")
        raise FetchPluginsError(f"Plugin '{name}' does not define skills and no SKILL.md files were found")
    return skill_paths


def copy_skill(source: Path, local_skills_dir: Path, root: Path) -> str:
    local_skills_dir.mkdir(parents=True, exist_ok=True)
    destination = local_skills_dir / source.name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return f"./{destination.relative_to(root).as_posix()}"


def copy_plugin_metadata(plugin: dict[str, Any], external_root: Path, local_plugin_dir: Path) -> None:
    source = plugin_source_root(plugin, external_root) / ".claude-plugin"
    destination = local_plugin_dir / ".claude-plugin"
    if destination.exists():
        shutil.rmtree(destination)
    if source.is_dir():
        local_plugin_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("marketplace.json"))


def local_plugin_entry(plugin: dict[str, Any], external_root: Path, local_skills_dir: Path, root: Path) -> dict[str, Any]:
    skills_root = external_root
    skills = plugin.get("skills")
    if skills is None:
        metadata = source_plugin_metadata(plugin, external_root)
        if metadata is not None and "skills" in metadata:
            skills = metadata.get("skills")
            skills_root = plugin_source_root(plugin, external_root)
        else:
            skills = infer_skill_paths(plugin, external_root)
    if not isinstance(skills, list) or not all(isinstance(skill, str) and skill for skill in skills):
        name = plugin.get("name", "<unknown>")
        raise FetchPluginsError(f"Plugin '{name}' must contain a skills string array")

    copy_plugin_metadata(plugin, external_root, local_skills_dir.parent)
    copied_skill_paths = [copy_skill(resolve_skill_path(skills_root, skill), local_skills_dir, root) for skill in skills]
    entry = dict(plugin)
    entry["source"] = "./"
    entry["skills"] = copied_skill_paths
    return entry


def merge_plugin(local_marketplace: dict[str, Any], plugin: dict[str, Any]) -> None:
    plugins = local_marketplace.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise FetchPluginsError("Local marketplace plugins field must be an array")

    name = plugin.get("name")
    for index, existing_plugin in enumerate(plugins):
        if not isinstance(existing_plugin, dict):
            continue
        existing_plugin_dict = cast(dict[str, Any], existing_plugin)
        if existing_plugin_dict.get("name") == name:
            plugins[index] = plugin
            return
    plugins.append(plugin)


def import_external_plugins(
    root: Path,
    fetch_marketplace: FetchMarketplace = clone_marketplace,
) -> list[str]:
    specs = load_external_specs(root / "external_plugins.json")
    local_marketplace_file = marketplace_path(root)
    local_marketplace = load_json(local_marketplace_file)
    if not isinstance(local_marketplace, dict):
        raise FetchPluginsError(f"{local_marketplace_file} must contain a JSON object")

    imported: list[str] = []

    with tempfile.TemporaryDirectory() as workspace:
        workspace_path = Path(workspace)
        for spec in specs:
            external_root = fetch_marketplace(spec, workspace_path)
            external_marketplace = load_json(marketplace_path(external_root))
            if not isinstance(external_marketplace, dict):
                raise FetchPluginsError(f"{marketplace_path(external_root)} must contain a JSON object")
            available_plugins = plugin_by_name(external_marketplace)
            local_skills_dir = external_skills_dir(root, spec.marketplace)

            plugin_names = spec.plugins or tuple(available_plugins)
            for plugin_name in plugin_names:
                plugin = available_plugins.get(plugin_name)
                if plugin is None:
                    available = ", ".join(sorted(available_plugins)) or "none"
                    raise FetchPluginsError(
                        f"Configured plugin '{plugin_name}' was not found in {spec.marketplace}; available plugins: {available}"
                    )
                merge_plugin(local_marketplace, local_plugin_entry(plugin, external_root, local_skills_dir, root))
                imported.append(plugin_name)

    write_json(local_marketplace_file, local_marketplace)
    return imported


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import configured Claude Code plugins from external marketplaces.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing external_plugins.json and .claude-plugin/marketplace.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        imported = import_external_plugins(args.root.resolve())
    except (FetchPluginsError, subprocess.CalledProcessError) as exc:
        print(f"fetch_plugins.py: {exc}")
        return 1

    for plugin_name in imported:
        print(f"Imported {plugin_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
