import os
import json

import numpy as np
import pandas as pd


def load_input_data(path: str) -> pd.DataFrame:
    skip_rows = 0
    with open(path, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith('#') or line.startswith("\"#"):
                skip_rows += 1
            else:
                break

    df = pd.read_csv(path, skiprows=skip_rows, index_col="congener")
    return df.reindex(CONGENERS)


def init_results() -> pd.DataFrame:
    results = pd.DataFrame(index=CONGENERS, columns=["total"])
    results.index.name = "congener"
    return results


def save_results(df: pd.DataFrame, filename: str) -> None:
    df.to_csv(os.path.join(OUTPUT_PATH, filename), index_label="congener", index=True)


def save_initial_profile(df: pd.DataFrame) -> None:
    results = init_results()
    results["total"] = df["gas"] + df["particulate"]
    save_results(results, "0.csv")


def simulate_removal_with_partitioning(device_config: dict, device_index: int) -> pd.DataFrame:
    init_profile = load_input_data(os.path.join(OUTPUT_PATH, f"{int(device_index - 1)}.csv"))
    ref_profile = load_input_data(os.path.join(DATA_PATH, f"{int(device_index)}.csv"))
    
    vp_params = load_input_data(os.path.join("params", "vapor_pressure.csv"))
    vapor_pressure = 10 ** (vp_params["b"] - vp_params["a"] / device_config["temperature"])
    gas_fraction = 0.3491 + 0.0407 * np.log(vapor_pressure) # TODO
    
    profile_before_g = init_profile["total"] * gas_fraction
    profile_before_p = init_profile["total"] * (1 - gas_fraction)

    conc_before_g = profile_before_g * device_config["conc_in"]
    conc_before_p = profile_before_p * device_config["conc_in"]

    removal_efficiency_g = 1 - ref_profile["gas_after"] * device_config["conc_out"] / \
        (ref_profile["gas_before"] * device_config["conc_in"])
    removal_efficiency_p = 1 - ref_profile["particulate_after"] * device_config["conc_out"] / \
        (ref_profile["particulate_before"] * device_config["conc_in"])

    conc_after_g = (1 - removal_efficiency_g) * conc_before_g
    conc_after_p = (1 - removal_efficiency_p) * conc_before_p

    profile_after_g = conc_after_g / (conc_after_g + conc_after_p).sum()
    profile_after_p = conc_after_p / (conc_after_g + conc_after_p).sum()

    results = init_results()
    results["total"] = profile_after_g + profile_after_p
    save_results(results, f"{device_index}.csv")


def simulate_removal_without_partitioning(device_config: dict, device_index: int) -> pd.DataFrame:
    init_profile = load_input_data(os.path.join(OUTPUT_PATH, f"{int(device_index - 1)}.csv"))
    ref_profile = load_input_data(os.path.join(DATA_PATH, f"{int(device_index)}.csv"))

    removal_efficiency = 1 - ref_profile["total_after"] / ref_profile["total_before"]
    removal_efficiency_adjusted = (1 - removal_efficiency.sum()) / removal_efficiency.sum() + \
        removal_efficiency / removal_efficiency.sum()
    
    results = init_results()
    results["total"] = init_profile["total"] * (1 - removal_efficiency_adjusted)
    save_results(results, f"{device_index}.csv")


# %% Initialize simulation settings
CONGENERS = [
    "2,3,7,8-TCDD",
    "1,2,3,7,8-PeCDD",
    "1,2,3,4,7,8-HxCDD",
    "1,2,3,6,7,8-HxCDD",
    "1,2,3,7,8,9-HxCDD",
    "1,2,3,4,6,7,8-HpCDD",
    "OCDD",
    "2,3,7,8-TCDF",
    "1,2,3,7,8-PeCDF",
    "2,3,4,7,8-PeCDF",
    "1,2,3,4,7,8-HxCDF",
    "1,2,3,6,7,8-HxCDF",
    "1,2,3,7,8,9-HxCDF",
    "2,3,4,6,7,8-HxCDF",
    "1,2,3,4,6,7,8-HpCDF",
    "1,2,3,4,7,8,9-HpCDF",
    "OCDF"
]

DATA_PATH = os.path.join("data", "profile_model")
OUTPUT_PATH = os.path.join("results", "profile_model")

if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)

with open("config.json", "r") as f:
    config = json.load(f)

# %% Load and save initial profile
init_profile = load_input_data(os.path.join(DATA_PATH, "0.csv"))
save_initial_profile(init_profile)

# %% Run simulation for each device
for i, device_config in enumerate(config["devices"]):
    device_index = i + 1
    if device_config["mode"] == 1:
        results = simulate_removal_with_partitioning(device_config, device_index=device_index)
    elif device_config["mode"] == 2:
        results = simulate_removal_without_partitioning(device_config, device_index=device_index)
    else:
        raise ValueError(f"Invalid mode {device_config['mode']} for device {device_index}.")