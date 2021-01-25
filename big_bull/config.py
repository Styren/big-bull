import toml
import os

config = None


def load_config(config_path=None):
    with open(config_path or "./pyproject.toml", "r") as f:
        global config
        config = toml.loads(f)


def get_config(key: str):
    if config is None:
        raise Exception("Config has not been initialized")
    return os.environ.get(f"BIG_BULL_{key.upper()}", config.get(key))
