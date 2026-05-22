"""Hydra entry point for users that still prefer Hydra over the CLI."""

from __future__ import annotations

from pathlib import Path

import hydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig

from .configuration import DEFAULT_CONFIG_DIR
from .sync import process_all_configs, process_single_config


@hydra.main(version_base=None, config_path="config", config_name="all")
def main(cfg: DictConfig) -> None:
    """Run AutoPaper from Hydra configuration.

    The packaged ``all`` config runs every ``sync*.yaml`` file. Any other config
    name runs a single sync config through the same service layer as the CLI.
    """
    try:
        config_name = HydraConfig.get().job.config_name or "all"
    except Exception:
        config_name = "all"

    config_dir = Path(DEFAULT_CONFIG_DIR)
    if config_name == "all":
        ok = process_all_configs(config_dir)
    else:
        result = process_single_config(config_name, config_dir)
        ok = bool(result.get("success"))

    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
