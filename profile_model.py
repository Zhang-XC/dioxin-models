import os

import numpy as np
import pandas as pd

from scipy.stats import linregress
from utils.io import CsvReader, CsvWriter
from utils.config import load_config, has_required_keys


def get_input_filename(device_index: int) -> str:
    return os.path.join(DATA_PATH, f"{int(device_index)}_input.csv")


def get_output_filename(device_index: int) -> str:
    return os.path.join(OUTPUT_PATH, f"{int(device_index)}_output.csv")


def save_initial_profile(df: pd.DataFrame, writer: CsvWriter) -> None:
    results = writer.init_df()
    results[RESULT_COLUMN] = df["gas"] + df["particulate"]
    writer.write_df(df=results, path=get_output_filename(0))


def linear_regression(x_fit: pd.Series, y_fit: pd.Series, x_pred: pd.Series) -> pd.Series:
    slope, intercept, _, _, _ = linregress(x_fit, y_fit)
    return slope * x_pred + intercept


def apply_adjustment_factors(s: pd.Series, phase: str, device_config: dict, reader: CsvReader) -> pd.Series:
    valid_phases = ["gas", "particulate", "total"]
    required_keys = ["phase", "factors_path"]
    if "adjust" in device_config:
        has_required_keys(device_config["adjust"], required_keys)
        diff_phases = set(device_config["adjust"]["phase"]) - set(valid_phases)
        if diff_phases:
            raise ValueError(f"Invalid phases {diff_phases} in adjustment")
        factors = reader.read_df(device_config["adjust"]["factors_path"])
        if phase in device_config["adjust"]["phase"]:
            s = s * factors[phase]
    return s


def simulate_removal_with_partitioning(
        device_config: dict,
        device_index: int,
        reader: CsvReader,
        writer: CsvWriter
    ) -> pd.DataFrame:
    init_profile = reader.read_df(get_output_filename(device_index - 1))
    ref_profile = reader.read_df(get_input_filename(device_index))
    
    vp_params = reader.read_df(os.path.join("params", "vapor_pressure.csv"))
    vapor_pressure = 10 ** (vp_params["b"] - vp_params["a"] / device_config["temperature"])
    ref_vapor_pressure = 10 ** (vp_params["b"] - vp_params["a"] / device_config["ref_temperature"])
    ref_gas_fraction = ref_profile["gas_before"] / (ref_profile["gas_before"] + ref_profile["particulate_before"])

    gas_fraction = linear_regression(
        x_fit=np.log(ref_vapor_pressure),
        y_fit=ref_gas_fraction,
        x_pred=np.log(vapor_pressure)
    )

    profile_before_g = init_profile[RESULT_COLUMN] * gas_fraction
    profile_before_p = init_profile[RESULT_COLUMN] * (1 - gas_fraction)

    conc_before_g = profile_before_g * device_config["conc_in"]
    conc_before_p = profile_before_p * device_config["conc_in"]

    removal_efficiency_g = 1 - ref_profile["gas_after"] * device_config["conc_out"] / \
        (ref_profile["gas_before"] * device_config["conc_in"])
    removal_efficiency_p = 1 - ref_profile["particulate_after"] * device_config["conc_out"] / \
        (ref_profile["particulate_before"] * device_config["conc_in"])
    
    removal_efficiency_g = apply_adjustment_factors(removal_efficiency_g, "gas", device_config, reader)
    removal_efficiency_p = apply_adjustment_factors(removal_efficiency_p, "particulate", device_config, reader)

    conc_after_g = (1 - removal_efficiency_g) * conc_before_g
    conc_after_p = (1 - removal_efficiency_p) * conc_before_p

    profile_after_g = conc_after_g / (conc_after_g + conc_after_p).sum()
    profile_after_p = conc_after_p / (conc_after_g + conc_after_p).sum()

    results = writer.init_df()
    results[RESULT_COLUMN] = profile_after_g + profile_after_p
    writer.write_df(df=results, path=get_output_filename(device_index))


def simulate_removal_without_partitioning(
        device_config: dict,
        device_index: int,
        reader: CsvReader,
        writer: CsvWriter
    ) -> pd.DataFrame:
    init_profile = reader.read_df(get_output_filename(device_index - 1))
    ref_removal_efficiency = reader.read_df(get_input_filename(device_index))

    removal_efficiency = ref_removal_efficiency["removal_efficiency"]
    profile_after = init_profile[RESULT_COLUMN] * (1 - removal_efficiency)
    removal_efficiency_adjusted = 1 - (1 - removal_efficiency) / profile_after.sum()
    
    removal_efficiency_adjusted = apply_adjustment_factors(removal_efficiency_adjusted, "total", device_config, reader)

    results = writer.init_df()
    results[RESULT_COLUMN] = init_profile[RESULT_COLUMN] * (1 - removal_efficiency_adjusted)
    writer.write_df(df=results, path=get_output_filename(device_index))


# Initialize simulation settings
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

INDEX_LABEL = "congener"
RESULT_COLUMN = "output"
COMMENTS = [
    "Output: Fraction of each congener in total PCDD/Fs after the device."
]

reader = CsvReader(index_label=INDEX_LABEL)
writer = CsvWriter(
    index=CONGENERS,
    columns=[RESULT_COLUMN],
    index_label=INDEX_LABEL,
    comments=COMMENTS
)

config = load_config("profile_model")

# Load and save initial profile
init_profile = reader.read_df(get_input_filename(0))
save_initial_profile(init_profile, writer)

# Run simulation for each device
for i, device_config in enumerate(config):
    device_index = i + 1
    if device_config["partition"]:
        results = simulate_removal_with_partitioning(device_config, device_index, reader, writer)
    else:
        results = simulate_removal_without_partitioning(device_config, device_index, reader, writer)