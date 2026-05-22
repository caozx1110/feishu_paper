"""YAML configuration loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

import yaml
from omegaconf import DictConfig, OmegaConf

from ..terminal import bullet_list

PACKAGE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_DIR = PACKAGE_DIR / "config"


def resolve_config_dir(config_dir: Optional[Union[str, Path]] = None) -> Path:
    """Return a config directory, defaulting to the packaged config templates."""
    if config_dir is None:
        return DEFAULT_CONFIG_DIR
    return Path(config_dir).expanduser().resolve()


def resolve_config_path(config_name: str, config_dir: Optional[Union[str, Path]] = None) -> Path:
    """Resolve either a config name such as ``sync_7_vln`` or an explicit YAML path."""
    candidate = Path(config_name).expanduser()
    if candidate.suffix in {".yaml", ".yml"}:
        if candidate.exists():
            return candidate.resolve()
        if not candidate.is_absolute():
            config_candidate = resolve_config_dir(config_dir) / candidate
            if config_candidate.exists():
                return config_candidate.resolve()

    name = candidate.stem if candidate.suffix else config_name
    return resolve_config_dir(config_dir) / f"{name}.yaml"


def load_default_config(config_dir: Optional[Union[str, Path]] = None) -> DictConfig:
    """Load the default config from a package or user config directory."""
    return load_config("default", config_dir=config_dir, apply_default=False)


def load_config(
    config_name: str,
    config_dir: Optional[Union[str, Path]] = None,
    *,
    apply_default: bool = True,
) -> DictConfig:
    """Load a YAML config and apply the local ``defaults: - default`` convention."""
    config_path = resolve_config_path(config_name, config_dir)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    cfg_dict = _read_yaml(config_path)
    if apply_default:
        default_cfg = _load_declared_default_config(cfg_dict, config_path, config_dir)
        if default_cfg:
            cfg_dict = to_plain_container(OmegaConf.merge(default_cfg, cfg_dict))

    return OmegaConf.create(cfg_dict)


def normalize_config(cfg: DictConfig) -> DictConfig:
    """Normalize legacy extended configs into the runtime schema."""
    if hasattr(cfg, "search_config") or hasattr(cfg, "user_profile"):
        default_cfg = _base_runtime_config()
        return merge_named_config_sections(default_cfg, cfg)
    return cfg


def merge_named_config_sections(base_cfg: DictConfig, user_cfg: DictConfig) -> DictConfig:
    """Merge ``*_config`` sections used by legacy templates into canonical sections."""
    merged_cfg = OmegaConf.merge(base_cfg, user_cfg)

    if hasattr(user_cfg, "search_config"):
        merged_cfg.search = OmegaConf.merge(merged_cfg.search, user_cfg.search_config)

    config_mappings = {
        "intelligent_matching_config": "intelligent_matching",
        "download_config": "download",
        "display_config": "display",
        "output_config": "output",
    }

    for config_key, canonical_key in config_mappings.items():
        if hasattr(user_cfg, config_key):
            if not hasattr(merged_cfg, canonical_key):
                merged_cfg[canonical_key] = {}
            merged_cfg[canonical_key] = OmegaConf.merge(merged_cfg[canonical_key], user_cfg[config_key])

    return merged_cfg


def find_sync_configs(config_dir: Optional[Union[str, Path]] = None, *, verbose: bool = True) -> list[str]:
    """Find all ``sync*.yaml`` configs in deterministic order."""
    config_dir_path = resolve_config_dir(config_dir)
    config_names = [config.stem for config in sorted(config_dir_path.glob("sync*.yaml"))]

    if verbose:
        bullet_list(f"发现 {len(config_names)} 个同步配置文件", config_names)

    return config_names


def to_plain_container(cfg: Any, *, resolve: bool = False) -> Any:
    """Convert OmegaConf containers to regular Python objects."""
    if isinstance(cfg, DictConfig):
        return OmegaConf.to_container(cfg, resolve=resolve)
    return cfg


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_declared_default_config(
    cfg_dict: dict[str, Any],
    config_path: Path,
    config_dir: Optional[Union[str, Path]],
) -> Optional[dict[str, Any]]:
    if config_path.stem == "default":
        return None

    defaults = cfg_dict.get("defaults", [])
    declares_default = False
    for item in defaults:
        if item == "default":
            declares_default = True
            break
        if isinstance(item, dict) and item.get("default") is not None:
            declares_default = True
            break

    if not declares_default:
        return None

    default_path = resolve_config_path("default", config_dir)
    if not default_path.exists() or default_path == config_path:
        return None

    return _read_yaml(default_path)


def _base_runtime_config() -> DictConfig:
    """Use packaged ``default.yaml`` as the base for legacy extended configs."""
    return load_default_config()
