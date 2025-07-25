import os

import numpy as np
import pandas as pd

from utils.io import CsvReader, CsvWriter
from utils.config import load_config, has_required_keys


# Constants
INPUT_FILE = os.path.join("data", "quantity_model", "input.csv")
OUTPUT_PATH = os.path.join("results", "quantity_model")
OUTPUT_FILE = os.path.join(OUTPUT_PATH, "output.csv")

if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)

INDEX_LABEL = "year"
RESULT_COLUMN = "output"
COMMENTS = [
    "Output: Yearly stack emission of PCDD/Fs [g]."
]

# Config
config = load_config("quantity_model")

required_keys = [
    "combustion_temperature",
    "residence_time",
    "yearly_operation_hours",
    "ocdf_fraction",
    "removal_efficiencies"
]
has_required_keys(config, required_keys)

# Kinetic parameters (Palmer et al., 2021)
Af1 = 5.73 * 10 ** 5
Af2 = 1.73 * 10 ** 6
Af3 = 5.03 * 10 ** 5
Ad = 2.23 * 10 ** 2
Ef = 16.79
Ed = 44.56
K_Cl = 0.0509
K_metal = 0.00259

# Initialize CSV reader
reader = CsvReader(index_label=INDEX_LABEL)

# Input parameters
data = reader.read_df(INPUT_FILE)
data["f_metal"] = data["f_Fe"] + data["f_Cu"]

T_comb = config["combustion_temperature"]
t_res = config["residence_time"]
hours = config["yearly_operation_hours"]
f_OCDF = config["ocdf_fraction"]
rem_effs = config["removal_efficiencies"]

# Initialize CSV writer
writer = CsvWriter(
    index=data.index.tolist(),
    columns=[RESULT_COLUMN],
    index_label=INDEX_LABEL,
    comments=COMMENTS
)

# Calculate kinetic parameters
# gas constant, kJ/(mol·K)
R = 8.314 * 10 ** (-3)
 # oxygen ratio
ratio_O = (data["m_air"] * 23 + 100 * data["f_O"] * data["m_waste"]) \
    / (data["m_waste"] * 100 * (data["f_C"] / 12 + data["f_H"] / 4 + data["f_S"] / 32) * 32)
# chlorine effect
E_Cl = data["f_Cl"] / (data["f_Cl"] + K_Cl)
 # metal effect
E_metal = data["f_metal"] / (data["f_metal"] + K_metal)
# formation kinetics constant for 2,3,7,8-TCDF, (pg PCDD/F)/(g waste·s)
kf1 = Af1 * np.exp(-Ef / (R * T_comb))
# formation kinetics constant for OCDF, (pg PCDD/F)/(g waste·s)
kf2 = Af2 * np.exp(-Ef / (R * T_comb))
# formation kinetics constant for 1,2,3,6,7,8-HxCDD, (pg PCDD/F)/(g waste·s)
kf3 = Af3 * np.exp(-Ef / (R * T_comb))
# decomposition kinetics constant, (pg PCDD/F)/(g waste·s)
kd = Ad * np.exp(-Ed / (R * T_comb))

# Solve kinetic equation
emission_rate = kf2 * E_Cl * E_metal / kd * (1 - np.exp(-kd * ratio_O * t_res))

# Post-processing
results = pd.DataFrame(index=data.index, columns=[RESULT_COLUMN])
results.index.name = "year"

results[RESULT_COLUMN] = emission_rate * data["m_waste"] * hours * 3600 * 10 ** (-9) / f_OCDF
for rem_eff in rem_effs:
    results[RESULT_COLUMN] = results[RESULT_COLUMN] * (1 - rem_eff)

# Save results
writer.write_df(df=results, path=OUTPUT_FILE)