import argparse

import numpy as np
import pandas as pd


# %% Initialize simulation parameters
congeners = [
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

result_columns = [
    "Before ESP (G.)",
    "Before ESP (P.)",
    "Before ESP (Total)",
    "Before ESP (G. abs)",
    "Before ESP (P. abs)",
    "Before ESP (Total abs)",
    "After ESP (G.)",
    "After ESP (P.)",
    "After ESP (Total)",
    "After ESP (G. abs)",
    "After ESP (P. abs)",
    "After ESP (Total abs)",
    "Removal Efficiency (G.)",
    "Removal Efficiency (P.)",
    "Removal Efficiency (Total)",
]

vp_params = pd.read_csv("./params/vapor_pressure.csv", index_col="Congener")
vp_params = vp_params.reindex(congeners)

esp_adj_coeffs = pd.read_csv("./params/esp_adjust_coeffs.csv", index_col="Congener")
esp_adj_coeffs = esp_adj_coeffs.reindex(congeners)
esp_adj_coeffs = esp_adj_coeffs["Coeff"]

results = pd.DataFrame({
    col: [pd.NA] * len(congeners)
    for col in result_columns
})
results.index = congeners

# %% Input parameters
parser = argparse.ArgumentParser()
parser.add_argument("--input_file", "-i", default="./data/input_profile_model.csv", type=str,
                    help="Path to CSV file of initial congener profile")
parser.add_argument("--output_file", "-o", default="./data/output_profile_model.csv", type=str,
                    help="Path to CSV file of results")
parser.add_argument("--T_esp", "-t", default=290, type=float,
                    help="ESP temperature [°C]")
parser.add_argument("--V_in", "-vi", default=58.966, type=float,
                    help="Inlet flow rate of PCDD/Fs [ng/Nm3]")
parser.add_argument("--V_out", "-vo", default=134.08, type=float,
                    help="Outlet flow rate of PCDD/Fs [ng/Nm3]")
args = parser.parse_args()

init_profile = pd.read_csv(args.input_file, skiprows=1, index_col="Congener")
init_profile = init_profile.reindex(congeners)
init_profile["Before ESP (Total)"] = init_profile["Before ESP (G.)"] + init_profile["Before ESP (P.)"]
init_profile["After ESP (Total)"] = init_profile["After ESP (G.)"] + init_profile["After ESP (P.)"]

T_esp = 273.15 + args.T_esp
V_in = args.V_in
V_out = args.V_out

# %% Simulation for ESP
vp = 10 ** (vp_params["b"] - vp_params["a"] / T_esp)
g_frac = 0.3491 + 0.0407 * np.log(vp)
results["Before ESP (G.)"] = init_profile["Before ESP (Total)"] * g_frac
results["Before ESP (P.)"] = init_profile["Before ESP (Total)"] * (1 - g_frac)
results["Before ESP (Total)"] = init_profile["Before ESP (Total)"]

results["Before ESP (G. abs)"] = results["Before ESP (G.)"] * V_in
results["Before ESP (P. abs)"] = results["Before ESP (P.)"] * V_in
results["Before ESP (Total abs)"] = results["Before ESP (G. abs)"] + results["Before ESP (P. abs)"]

results["Removal Efficiency (G.)"] = 1 - init_profile["After ESP (G.)"] * V_out / (init_profile["Before ESP (G.)"] * V_in)
results["Removal Efficiency (P.)"] = 1 - init_profile["After ESP (P.)"] * V_out / (init_profile["Before ESP (P.)"] * V_in)
results["Removal Efficiency (P.)"] = results["Removal Efficiency (P.)"] * esp_adj_coeffs

results["After ESP (G. abs)"] = (1 - results["Removal Efficiency (G.)"]) * results["Before ESP (G. abs)"]
results["After ESP (P. abs)"] = (1 - results["Removal Efficiency (P.)"]) * results["Before ESP (P. abs)"]
results["After ESP (Total abs)"] = results["After ESP (G. abs)"] + results["After ESP (P. abs)"]

results["Removal Efficiency (Total)"] = 1 - results["After ESP (Total abs)"] / results["Before ESP (Total abs)"]

sum_abs_after_esp = results["After ESP (G. abs)"].sum() + results["After ESP (P. abs)"].sum()
results["After ESP (G.)"] = results["After ESP (G. abs)"] / sum_abs_after_esp
results["After ESP (P.)"] = results["After ESP (P. abs)"] / sum_abs_after_esp
results["After ESP (Total)"] = results["After ESP (G.)"] + results["After ESP (P.)"]

# %% Drop temporary columns
results = results.drop(columns=[col for col in results.columns if "abs" in col])

# %% Save results
results.to_csv(args.output_file, index_label="Congener", index=True)