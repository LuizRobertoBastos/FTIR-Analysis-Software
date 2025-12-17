# FTIR Spectrum Analysis Tool 🧪📊

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Libraries](https://img.shields.io/badge/Libraries-Tkinter%20%7C%20Pandas%20%7C%20Matplotlib%20%7C%20NumPy%20%7C%20SciPy%20%7C%20Plotly%20%7C%20Chardet%20%7C%20CSV%20%7C%20OS%20%7C%20Webbrowser%20%7C%20Regex%20%7C%20Base64-green)
![Status](https://img.shields.io/badge/Status-In_Development-orange)


## 📝 Overview

This repository contains a **Python-based software** designed to automate the processing, analysis, and visualization of **Fourier Transform Infrared (FTIR)** spectroscopy data.

Developed during my experience at the **Composite Materials and Adhesives Laboratory at UFRJ**, this tool was created to optimize the characterization workflow of metallic and non-metallic materials, reducing data processing time and ensuring standardization in spectral analysis.

> **Note:** Due to confidentiality agreements related to industrial research projects, the datasets provided in this repository are **dummy/simulated data** solely for demonstration purposes. No proprietary data from external partners is disclosed.

## 🎯 Key Features

* **Automated Data Import:** Batch processing of raw spectrum files (e.g., `.CSV`, `.SPA`, `.TXT`).
* **Signal Processing:**
    * Automatic Baseline Correction.
    * Transmittance to Absorbance conversion.
    * Noise reduction / Smoothing algorithms.
* **Peak Detection:** Algorithm to identify and label significant peaks in the spectrum automatically.
* **Visualization:** Interactive plotting for comparative analysis of multiple samples.
* **Report Generation:** Automatic export of processed data and graphs.

## 🛠️ Technologies & Tools

* **Language:** Python 3.x  
* **Graphical User Interface (GUI):** Tkinter  
* **Data Manipulation:** Pandas, NumPy, CSV  
* **Scientific Computing:** SciPy (savgol_filter, find_peaks)  
* **Visualization:** Matplotlib, Plotly  
* **Encoding Detection:** Chardet  
* **Utilities:** OS, Webbrowser, Regex (re), Base64  
* **Extras:** Cycles (itertools.cycle), Filedialog, Messagebox, Colorchooser  

## 🚀 How to Run

1.  Clone the repository:
    ```bash
    git clone [https://github.com/seu-usuario/nome-do-repo.git](https://github.com/seu-usuario/nome-do-repo.git)
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the main script:
    ```bash
    python main.py
    ```

## 📚 Background & Context

This project was developed as part of a Scientific Initiation (IC) aimed at material integrity analysis. The software was utilized to support research activities involving complex sample preparations and characterization protocols.

**Key Achievements with this tool:**
* Reduced spectral analysis time by approximately **X%** (chute uma porcentagem, ex: 40%).
* Processed over **X** samples during the research period.
* Standardized the reporting format for the laboratory's internal usage.

## 👨‍💻 Author

**Luiz Roberto Bastos de Oliveira**
*Materials Engineering Student @ UFRJ*

* https://www.linkedin.com/in/luiz-roberto-bastos-556358274/

---
