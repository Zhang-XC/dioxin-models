import os

import numpy as np
import pandas as pd

from scipy.stats import linregress
from utils.io import CsvReader, CsvWriter
from utils.config import ConfigValidator, load_config


class ProfileModel:
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
    COMMENTS = [
        "Output: Fraction of each congener in total PCDD/Fs after the device."
    ]

    def __init__(self, config: dict):
        self.config = config
        self.data_path = config["data_path"]
        self.output_path = config["output_path"]
        self.result_column = config["result_column"]
        self.index_label = config["index_label"]

        os.makedirs(self.output_path, exist_ok=True)

        self.reader = CsvReader(index_label=self.index_label)
        self.writer = CsvWriter(
            index=self.CONGENERS,
            columns=[self.result_column],
            index_label=self.index_label,
            comments=self.COMMENTS
        )

    def run(self) -> None:
        # Load and save initial profile
        init_profile = self.reader.read_df(self._get_input_filename(0))
        init_results = init_profile["gas"] + init_profile["particulate"]
        self._write_results(init_results, device_index=0)

        # Run simulation for each device
        for i, device_config in enumerate(self.config["devices"]):
            device_index = i + 1
            if device_config["partition"]:
                self._simulate_with_partitioning(device_config, device_index)
            else:
                self._simulate_without_partitioning(device_config, device_index)

    def _calculate_vapor_pressure(self, temp: float) -> pd.Series:
        vp_params = self.reader.read_df(os.path.join("params", "vapor_pressure.csv"))
        vapor_pressure = 10 ** (vp_params["b"] - vp_params["a"] / temp)
        return vapor_pressure
    
    def _simulate_with_partitioning(self, device_config: dict, device_index: int) -> pd.DataFrame:
        init_profile = self.reader.read_df(self._get_output_filename(device_index - 1))
        ref_profile = self.reader.read_df(self._get_input_filename(device_index))

        vp_current = self._calculate_vapor_pressure(device_config["temperature"])
        vp_ref = self._calculate_vapor_pressure(device_config["ref_temperature"])
        
        gas_frac_ref = ref_profile["gas_before"] / (ref_profile["gas_before"] + ref_profile["particulate_before"])
        gas_frac = self._estimate_gas_fraction(
            gas_frac_ref=gas_frac_ref,
            vp_ref=vp_ref,
            vp_current=vp_current
        )

        profile_before_g = init_profile[self.result_column] * gas_frac
        profile_before_p = init_profile[self.result_column] * (1 - gas_frac)

        conc_before_g = profile_before_g * device_config["conc_in"]
        conc_before_p = profile_before_p * device_config["conc_in"]

        rem_eff_g = 1 - ref_profile["gas_after"] * device_config["conc_out"] / \
            (ref_profile["gas_before"] * device_config["conc_in"])
        rem_eff_p = 1 - ref_profile["particulate_after"] * device_config["conc_out"] / \
            (ref_profile["particulate_before"] * device_config["conc_in"])
        
        if "adjust" in device_config:
            rem_eff_g = self._apply_adjustment(rem_eff_g, "gas", device_config)
            rem_eff_p = self._apply_adjustment(rem_eff_p, "particulate", device_config)

        conc_after_g = (1 - rem_eff_g) * conc_before_g
        conc_after_p = (1 - rem_eff_p) * conc_before_p

        profile_after_g = conc_after_g / (conc_after_g + conc_after_p).sum()
        profile_after_p = conc_after_p / (conc_after_g + conc_after_p).sum()

        results = profile_after_g + profile_after_p
        self._write_results(results, device_index)

    def _simulate_without_partitioning(self, device_config: dict, device_index: int) -> pd.DataFrame:
        init_profile = self.reader.read_df(self._get_output_filename(device_index - 1))
        ref_rem_eff = self.reader.read_df(self._get_input_filename(device_index))

        rem_eff = ref_rem_eff["removal_efficiency"]
        profile_after = init_profile[self.result_column] * (1 - rem_eff)
        rem_eff_adjusted = 1 - (1 - rem_eff) / profile_after.sum()
        
        if "adjust" in device_config:
            rem_eff_adjusted = self._apply_adjustment(rem_eff_adjusted, "total", device_config)

        output = init_profile[self.result_column] * (1 - rem_eff_adjusted)
        self._write_results(output, device_index)
    
    def _apply_adjustment(self, series: pd.Series, phase: str, device_config: dict) -> pd.Series:
        factors = self.reader.read_df(device_config["adjust"]["factors_path"])
        if phase in device_config["adjust"]["phase"]:
            series = series * factors[phase]
        return series
    
    def _estimate_gas_fraction(
            self,
            gas_frac_ref: pd.Series,
            vp_ref: pd.Series,
            vp_current: pd.Series
        ) -> pd.Series:
        slope, intercept, _, _, _ = linregress(np.log(vp_ref), gas_frac_ref)
        gas_fraction = slope * np.log(vp_current) + intercept
        return np.clip(gas_fraction, 0, 1)

    def _write_results(self, data: pd.Series, device_index: int) -> None:
        results = self.writer.init_df()
        results[self.result_column] = data
        self.writer.write_df(df=results, path=self._get_output_filename(device_index))
    
    def _get_input_filename(self, device_index: int) -> str:
        return os.path.join(self.data_path, f"{device_index}_input.csv")

    def _get_output_filename(self, device_index: int) -> str:
        return os.path.join(self.output_path, f"{device_index}_output.csv")


# Load configuration
ConfigValidator().validate("profile_model")
config = load_config("profile_model")

# Run simulation
model = ProfileModel(config)
model.run()