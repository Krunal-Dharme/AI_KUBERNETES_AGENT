"""Parse kubeconfig YAML directly to list all contexts (not only current-context)."""

from pathlib import Path

import yaml
from loguru import logger


def _clusters_from_config(config: dict) -> dict:
    current_context = config.get("current-context", "") or ""
    cluster_map = {
        item.get("name", ""): item.get("cluster", {})
        for item in config.get("clusters", [])
        if isinstance(item, dict) and item.get("name")
    }

    clusters = []
    for ctx in config.get("contexts", []):
        if not isinstance(ctx, dict):
            continue

        name = ctx.get("name", "")
        if not name:
            continue

        context = ctx.get("context", {}) if isinstance(ctx.get("context"), dict) else {}
        cluster_name = context.get("cluster", "")
        cluster_info = cluster_map.get(cluster_name, {})
        server = cluster_info.get("server", "unknown") if isinstance(cluster_info, dict) else "unknown"

        clusters.append(
            {
                "name": name,
                "cluster": cluster_name,
                "server": server,
                "is_current": name == current_context,
                "is_gke": "gke" in name.lower() or "googleapis.com" in str(server),
            }
        )

    return {
        "healthy": len(clusters) > 0,
        "error": None if clusters else "No cluster contexts found in kubeconfig.",
        "current_context": current_context,
        "clusters": clusters,
    }


def parse_clusters_from_kubeconfig(kubeconfig_path: str) -> dict:
    """
    Read kubeconfig from disk and return every context defined in the file.

    Parsing the file directly avoids kubectl --minify behaviour that can
    collapse output to the current context only.
    """
    path = Path(kubeconfig_path)
    if not path.is_file():
        return {
            "healthy": False,
            "error": f"Kubeconfig file not found at: {kubeconfig_path}",
            "current_context": "",
            "clusters": [],
        }

    try:
        with path.open(encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        logger.error("Failed to parse kubeconfig YAML at {}: {}", kubeconfig_path, exc)
        return {
            "healthy": False,
            "error": f"Invalid kubeconfig YAML at {kubeconfig_path}: {exc}",
            "current_context": "",
            "clusters": [],
        }

    if not isinstance(config, dict):
        return {
            "healthy": False,
            "error": f"Unexpected kubeconfig format at {kubeconfig_path}",
            "current_context": "",
            "clusters": [],
        }

    result = _clusters_from_config(config)
    logger.info(
        "Parsed {} context(s) from kubeconfig file {}",
        len(result["clusters"]),
        kubeconfig_path,
    )
    return result


def parse_clusters_from_yaml(yaml_content: str) -> dict:
    """Parse cluster contexts from kubeconfig YAML text (kubectl config view output)."""
    try:
        config = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError as exc:
        return {
            "healthy": False,
            "error": f"Invalid kubeconfig YAML: {exc}",
            "current_context": "",
            "clusters": [],
        }

    if not isinstance(config, dict):
        return {
            "healthy": False,
            "error": "Unexpected kubeconfig format",
            "current_context": "",
            "clusters": [],
        }

    return _clusters_from_config(config)
