import os

import numpy as np
import pandas as pd

from utils.io import CsvReader, CsvWriter
from utils.config import ConfigValidator, load_config


class QuantityModel:
    COMMENTS = [
        "Output: Yearly stack emission of PCDD/Fs [g]."
    ]

    def __init__(self, config: dict):
        self.config = config
        self.data_path = config["data_path"]
        self.output_path = config["output_path"]
        self.result_column = config["result_column"]
        self.index_label = config["index_label"]

        self.input_file = os.path.join(self.data_path, "input.csv")
        self.output_file = os.path.join(self.output_path, "output.csv")

        os.makedirs(self.output_path, exist_ok=True)
    
    def run(self) -> None:
        # --- Load input data ---
        reader = CsvReader(index_label=self.index_label)
        data = reader.read_df(self.input_file)
        data["f_metal"] = data["f_Fe"] + data["f_Cu"]

        # --- Model parameters from config ---
        T_comb = self.config["combustion_temperature"]
        t_res = self.config["residence_time"]
        hours = self.config["yearly_operation_hours"]
        congener = self.config["congener"]
        frac = self.config["congener_fraction"]
        rem_effs = self.config["removal_efficiencies"]

        # --- Kinetic constants (Palmer et al., 2021) ---
        Ad = 2.23 * 1e2    # decomposition pre-exponential factor, (pg PCDD/F)/(g waste·s)
        Ef = 16.79         # formation activation energy, kJ/mol 
        Ed = 44.56         # decomposition activation energy, kJ/mol
        K_Cl = 0.0509      # chlorine effect constant
        K_metal = 0.00259  # metal effect constant
        # Congener-specific formation pre-exponential factor, (pg PCDD/F)/(g waste·s)
        if congener == "2,3,7,8-TCDF":
            Af = 5.73 * 1e5
        elif congener == "OCDF":
            Af = 1.73 * 1e6
        elif congener == "1,2,3,6,7,8-HxCDD":
            Af = 5.03 * 1e5
        else:
            raise ValueError(f"Invalid congener: {congener}.")

        # --- Stepwise calculation ---
        # Calculation of kinetic and process parameters:
        #   R        : gas constant, kJ/(mol·K)
        #   ratio_O  : oxygen ratio
        #   E_Cl     : chlorine effect
        #   E_metal  : metal effect
        #   kf       : formation kinetics constant, (pg PCDD/F)/(g waste·s)
        #   kd       : decomposition kinetics constant, (pg PCDD/F)/(g waste·s)
        R = 8.314 * 1e-3
        ratio_O = (
            (data["m_air"] * 23 + 100 * data["f_O"] * data["m_waste"]) /
            (data["m_waste"] * 100 * (data["f_C"] / 12 + data["f_H"] / 4 + data["f_S"] / 32) * 32)
        )
        E_Cl = data["f_Cl"] / (data["f_Cl"] + K_Cl)
        E_metal = data["f_metal"] / (data["f_metal"] + K_metal)
        kf = Af * np.exp(-Ef / (R * T_comb))
        kd = Ad * np.exp(-Ed / (R * T_comb))

        # Solve kinetic equation for emission rate, (pg PCDD/F)/(g waste·s)
        emission_rate = kf * E_Cl * E_metal / kd * (1 - np.exp(-kd * ratio_O * t_res))

        # --- Post-processing ---
        results = pd.DataFrame(index=data.index, columns=[self.result_column])
        results.index.name = self.index_label
        # Convert emission rate to yearly stack emission, g
        results[self.result_column] = emission_rate * data["m_waste"] * hours * 3600 * 1e-9 / frac
        for rem_eff in rem_effs:
            results[self.result_column] *= (1 - rem_eff)

        # --- Save results ---
        writer = CsvWriter(
            index=data.index.tolist(),
            columns=[self.result_column],
            index_label=self.index_label,
            comments=self.COMMENTS
        )
        writer.write_df(df=results, path=self.output_file)


# Load configuration
ConfigValidator().validate("quantity_model")
config = load_config("quantity_model")

# Run simulation
model = QuantityModel(config)
model.run()