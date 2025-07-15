# Dioxin Emission Models

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
   pip install numpy pandas
   ```

4. Run simulations:

   ```
   python profile_model.py
   python quantity_model.py
   ```