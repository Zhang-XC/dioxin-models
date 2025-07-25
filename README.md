# Dioxin Emission Models

This is the Python implementation of the model described in the paper:

**Assessment of past dioxin emissions from waste incineration plants based on archive studies and process modeling: a new methodological tool** \
*Archives of Environmental Contamination and Toxicology* (under review) \
Xiaocheng Zhang*, Alexis de Aragao*, Fabien Moll-François, Aurélie Berthet, Florian Breider \
\* These authors contributed equally to this work.

## Introduction
We propose a novel approach for reconstructing the history of polychlorinated dibenzo-*p*-dioxin (PCDD) and polychlorinated dibenzofuran (PCDF) pollution from municipal solid waste incinerators (MSWIs) with unknown past emissions. The proposed methodology relies on the search for technical and operational data on the pollution source in archives, the extraction of representative data from the scientific literature, and the use of kinetic models of the formation and decomposition of PCDD/Fs within combustion chambers. This new methodological tool allows to estimate the MSWI’s stack emission and relative profile of seventeen PCDD/F congeners over time.

The model focuses on 17 toxicologically relevant PCDD/F congeners. It considers the formation and decomposition of PCDD/Fs in the furnace, and their formation, removal, and phase distribution in air pollution control devices (APCD). The model consists of two components:
* An **emission profile model** that estimates the fraction of each PCDD/F congener in total PCDD/Fs
* An **emission quantity model** that estimates the total amount of PCDD/Fs

## Prepare data
Simulation settings are defined in `config.yaml`. Congener-specific input data should be placed in the appropriate subdirectory under `data/` as CSV files, depending on the selected model:

* **Profile model:** Input files should be placed in `data/profile_model/` and named using the format `{device_index}_input.csv`, where `device_index` is the index of the air pollution control device starting from `1`. Use `0_input.csv` to specify input data before the first device.
* **Quantity model:** Input data should be placed in `data/quantity_model/` and named `input.csv`.

Both the YAML configuration file and the CSV input files must follow the format and naming conventions of the existing examples. Refer to the inline comments inside these files for instructions.

## How to run

### Requirements
- Python 3.9 or newer

### Steps

1. Create a virtual environment:

   ```bash
   python -m venv env
   ```

2. Activate the environment:

   - On Windows (PowerShell):

     ```
     .\env\Scripts\Activate.ps1
     ```

   - On Windows (cmd):

     ```
     .\env\Scripts\activate.bat
     ```

   - On macOS/Linux:

     ```
     source env/bin/activate
     ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Run simulations:

   ```
   python profile_model.py
   python quantity_model.py
   ```

## Results
Simulation results are saved in the `results/` directory, mirroring the structure and naming conventions of the input files.