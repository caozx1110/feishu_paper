"""Configuration loading and runtime settings for AutoPaper."""

from .loader import (
    DEFAULT_CONFIG_DIR,
    PACKAGE_DIR,
    find_sync_configs,
    load_config,
    load_default_config,
    normalize_config,
    resolve_config_dir,
    resolve_config_path,
    to_plain_container,
)
from .network import configure_network, healthcheck_url
from .runtime import ArxivRuntimeSettings, FeishuEnvPolicy, HealthcheckSettings, NetworkSettings, RuntimeSettings
from .validation import ConfigIssue, has_errors, print_validation_report, validate_config

__all__ = [
    "DEFAULT_CONFIG_DIR",
    "PACKAGE_DIR",
    "ArxivRuntimeSettings",
    "FeishuEnvPolicy",
    "HealthcheckSettings",
    "NetworkSettings",
    "RuntimeSettings",
    "ConfigIssue",
    "configure_network",
    "find_sync_configs",
    "has_errors",
    "healthcheck_url",
    "load_config",
    "load_default_config",
    "normalize_config",
    "print_validation_report",
    "resolve_config_dir",
    "resolve_config_path",
    "to_plain_container",
    "validate_config",
]
