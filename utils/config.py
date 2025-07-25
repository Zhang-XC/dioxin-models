import yaml


class ConfigValidator:
    def validate(self, key: str) -> None:
        config = load_config(key)
        if key == "profile_model":
            self._validate_profile_model_config(config)
        elif key == "quantity_model":
            self._validate_quantity_model_config(config)
        else:
            raise ValueError(f"Unknown configuration key: {key}.")

    def _validate_profile_model_config(self, config: dict) -> None:
        required_keys = ["data_path", "output_path", "index_label", "result_column", "devices"]
        has_required_keys(config, required_keys)
        for device_config in config["devices"]:
            self._validate_device_config(device_config)
            if "adjust" in device_config:
                self._validate_adjustment_config(device_config["adjust"])

    def _validate_device_config(self, device_config: dict) -> None:
        has_required_keys(device_config, ["partition"])
        if device_config["partition"]:
            required_keys = ["temperature", "ref_temperature", "conc_in", "conc_out"]
            has_required_keys(device_config, required_keys)

    def _validate_adjustment_config(self, adjustment_config: dict) -> None:
        required_keys = ["phase", "factors_path"]
        has_required_keys(adjustment_config, required_keys)

        valid_phases = ["gas", "particulate", "total"]
        diff_phases = set(adjustment_config["phase"]) - set(valid_phases)
        if diff_phases:
            raise ValueError(f"Invalid phases {diff_phases} in adjustment.")
        
    def _validate_quantity_model_config(self, config: dict) -> None:
        required_keys = [
            "data_path",
            "output_path",
            "index_label",
            "result_column",
            "combustion_temperature",
            "residence_time",
            "yearly_operation_hours",
            "congener",
            "congener_fraction",
            "removal_efficiencies"
        ]
        has_required_keys(config, required_keys)


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