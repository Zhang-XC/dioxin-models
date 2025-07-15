import argparse

import numpy as np
import pandas as pd


# %% Kinetic parameters (Palmer et al., 2021)
Af1 = 5.73 * 10 ** 5
Af2 = 1.73 * 10 ** 6
Af3 = 5.03 * 10 ** 5
Ad = 2.23 * 10 ** 2
Ef = 16.79
Ed = 44.56
K_Cl = 0.0509
K_metal = 0.00259

# %% Input parameters
parser = argparse.ArgumentParser()
parser.add_argument("--input_file", "-i", default="./data/input_quantity_model.csv", type=str,
                    help="Path to CSV file of input data")
parser.add_argument("--output_file", "-o", default="./data/output_quantity_model.csv", type=str,
                    help="Path to CSV file of results")
parser.add_argument("--T_comb", "-tc", default=950, type=float,
                    help="Combustion temperature [°C]")
parser.add_argument("--t_res", "-tr", default=2, type=float,
                    help="Residence time [s]")
parser.add_argument("--hours", "-hr", default=8050, type=int,
                    help="Annual hours of operation [h]")
parser.add_argument("--f_ocdf", "-f", default=0.207, type=float,
                    help="Fraction of OCDF in total PCDD/Fs [-]")
parser.add_argument("--R_esp", "-re", default=-1.61, type=float,
                    help="Removal efficiency of ESP [-]")
parser.add_argument("--R_ws", "-rw", default=0.4, type=float,
                    help="Removal efficiency of WS [-]")
parser.add_argument("--year_ws", "-y", default=1982, type=int,
                    help="Year of WS installation")
args = parser.parse_args()

data = pd.read_csv(args.input_file, skiprows=1, index_col="Year")
data["f_metal"] = data["f_Fe"] + data["f_Cu"]

T_comb = args.T_comb + 273.15
t_res = args.t_res
hours = args.hours
f_OCDF = args.f_ocdf
R_esp = args.R_esp
R_ws = args.R_ws
year_ws = args.year_ws

# %% Calculate kinetic parameters
R = 8.314 * 10 ** (-3) # gas constant, kJ/(mol·K)
ratio_O = (data["m_air"] * 23 + 100 * data["f_O"] * data["m_waste"]) \
    / (data["m_waste"] * 100 * (data["f_C"] / 12 + data["f_H"] / 4 + data["f_S"] / 32) * 32) # oxygen ratio
E_Cl = data["f_Cl"] / (data["f_Cl"] + K_Cl) # chlorine effect
E_metal = data["f_metal"] / (data["f_metal"] + K_metal) # metal effect
kf1 = Af1 * np.exp(-Ef / (R * T_comb)) # formation kinetics constant for 2,3,7,8-TCDF, (pg PCDD/F)/(g waste·s)
kf2 = Af2 * np.exp(-Ef / (R * T_comb)) # formation kinetics constant for OCDF, (pg PCDD/F)/(g waste·s)
kf3 = Af3 * np.exp(-Ef / (R * T_comb)) # formation kinetics constant for 1,2,3,6,7,8-HxCDD, (pg PCDD/F)/(g waste·s)
kd = Ad * np.exp(-Ed / (R * T_comb)) # decomposition kinetics constant, (pg PCDD/F)/(g waste·s)

# %% Solve kinetic equation
emission_rate = kf2 * E_Cl * E_metal / kd * (1 - np.exp(-kd * ratio_O * t_res))

# %% Post-processing
results = pd.DataFrame({
    "Year": data.index,
    "Stack emission [g]": [pd.NA] * len(data),
}).set_index("Year")

emission_yearly = emission_rate * data["m_waste"] * hours * 3600 * 10 ** (-9) / f_OCDF
results["Stack emission [g]"] = emission_yearly * (1 - R_esp)
results.loc[:year_ws, "Stack emission [g]"] = emission_yearly * (1 - R_esp)
results.loc[year_ws:, "Stack emission [g]"] = emission_yearly * (1 - R_esp) * (1 - R_ws)

# %% Save results
results.to_csv(args.output_file, index_label="Year", index=True)