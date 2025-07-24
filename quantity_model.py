import os

import yaml
import numpy as np
import pandas as pd


# Paths
INPUT_FILE = os.path.join("data", "quantity_model", "input.csv")
OUTPUT_PATH = os.path.join("results", "quantity_model")
OUTPUT_FILE = os.path.join(OUTPUT_PATH, "output.csv")

if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
config = config["quantity_model"]

# Kinetic parameters (Palmer et al., 2021)
Af1 = 5.73 * 10 ** 5
Af2 = 1.73 * 10 ** 6
Af3 = 5.03 * 10 ** 5
Ad = 2.23 * 10 ** 2
Ef = 16.79
Ed = 44.56
K_Cl = 0.0509
K_metal = 0.00259

# Input parameters
data = pd.read_csv(INPUT_FILE, skiprows=1, index_col="year")
data["f_metal"] = data["f_Fe"] + data["f_Cu"]

T_comb = config["combustion_temperature"]
t_res = config["residence_time"]
hours = config["yearly_operation_hours"]
f_OCDF = config["ocdf_fraction"]
rem_effs = config["removal_efficiencies"]

# Calculate kinetic parameters
R = 8.314 * 10 ** (-3) # gas constant, kJ/(mol·K)
ratio_O = (data["m_air"] * 23 + 100 * data["f_O"] * data["m_waste"]) \
    / (data["m_waste"] * 100 * (data["f_C"] / 12 + data["f_H"] / 4 + data["f_S"] / 32) * 32) # oxygen ratio
E_Cl = data["f_Cl"] / (data["f_Cl"] + K_Cl) # chlorine effect
E_metal = data["f_metal"] / (data["f_metal"] + K_metal) # metal effect
kf1 = Af1 * np.exp(-Ef / (R * T_comb)) # formation kinetics constant for 2,3,7,8-TCDF, (pg PCDD/F)/(g waste·s)
kf2 = Af2 * np.exp(-Ef / (R * T_comb)) # formation kinetics constant for OCDF, (pg PCDD/F)/(g waste·s)
kf3 = Af3 * np.exp(-Ef / (R * T_comb)) # formation kinetics constant for 1,2,3,6,7,8-HxCDD, (pg PCDD/F)/(g waste·s)
kd = Ad * np.exp(-Ed / (R * T_comb)) # decomposition kinetics constant, (pg PCDD/F)/(g waste·s)

# Solve kinetic equation
emission_rate = kf2 * E_Cl * E_metal / kd * (1 - np.exp(-kd * ratio_O * t_res))

# Post-processing
results = pd.DataFrame(index=data.index, columns=["stack_emission"])
results.index.name = "year"

results["stack_emission"] = emission_rate * data["m_waste"] * hours * 3600 * 10 ** (-9) / f_OCDF
for rem_eff in rem_effs:
    results["stack_emission"] = results["stack_emission"] * (1 - rem_eff)

# Save results
results.to_csv(OUTPUT_FILE, index_label="year", index=True)