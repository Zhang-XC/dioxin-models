import yaml


def load_config(key: str) -> dict:
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config[key]


def has_required_keys(config: dict, required_keys: list) -> None:
    missing_keys = []
    for key in required_keys:
        if config.get(key) is None:
            missing_keys.append(key)
    if missing_keys:
        raise KeyError(f"Missing keys {missing_keys} or their values contain None.")