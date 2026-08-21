"""Generate a deterministic dependency-closure SBOM from the installed StructuraX environment."""
from __future__ import annotations

import json
import re
from importlib import metadata
from typing import Any


_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str | None:
    match = _NAME.match(requirement)
    return canonical(match.group(1)) if match else None


def installed_distribution(name: str) -> metadata.Distribution | None:
    try:
        return metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return None


def dependency_closure(root: str = "structurax") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queue = [canonical(root)]
    visited: set[str] = set()
    components: dict[str, dict[str, Any]] = {}
    edges: dict[str, set[str]] = {}

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        dist = installed_distribution(current)
        if dist is None:
            raise SystemExit(f"installed dependency closure is incomplete; missing distribution: {current}")

        name = canonical(dist.metadata.get("Name", current))
        version = dist.version
        components[name] = {
            "type": "library" if name != canonical(root) else "application",
            "name": name,
            "version": version,
            "bom-ref": f"pkg:pypi/{name}@{version}",
        }

        dependencies: set[str] = set()
        for raw in dist.requires or []:
            dep_name = requirement_name(raw)
            if not dep_name:
                continue
            dep_dist = installed_distribution(dep_name)
            if dep_dist is None:
                # Requirements excluded by environment markers or extras are not part of the installed closure.
                continue
            dependencies.add(canonical(dep_dist.metadata.get("Name", dep_name)))
            if dep_name not in visited:
                queue.append(dep_name)
        edges[name] = dependencies

    ordered_components = [components[name] for name in sorted(components)]
    ref_by_name = {item["name"]: item["bom-ref"] for item in ordered_components}
    dependencies = [
        {
            "ref": ref_by_name[name],
            "dependsOn": sorted(ref_by_name[dep] for dep in edges.get(name, set()) if dep in ref_by_name),
        }
        for name in sorted(ref_by_name)
    ]
    return ordered_components, dependencies


def build_sbom() -> dict[str, Any]:
    components, dependencies = dependency_closure()
    root = next(item for item in components if item["name"] == "structurax")
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": root,
            "properties": [
                {"name": "structurax:scope", "value": "installed-dependency-closure"},
                {"name": "structurax:production-release-sbom", "value": "false"},
            ],
        },
        "components": components,
        "dependencies": dependencies,
    }


if __name__ == "__main__":
    print(json.dumps(build_sbom(), indent=2, sort_keys=True))
