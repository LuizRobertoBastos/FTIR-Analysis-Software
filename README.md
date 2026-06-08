# 🧪📊 LaCom Materials Suite: FTIR Pro

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-lightgrey)
![SciPy](https://img.shields.io/badge/Math-SciPy%20%7C%20NumPy-orange)
![Status](https://img.shields.io/badge/Status-Active_Development-success)

## 📝 Overview

This repository contains an open-source, Python-based software suite designed to automate the processing, analysis, and visualization of Fourier Transform Infrared (FTIR) spectroscopy data. 

Developed at the Composite Materials and Adhesives Laboratory (LaCom) at the Federal University of Rio de Janeiro (UFRJ), this tool was created to optimize the characterization workflow of polymeric and composite materials. It replaces manual, repetitive tasks in generic software with automated, chemistry-focused algorithms, reducing data processing time and ensuring standardization across the laboratory.

> **Note on Confidentiality:** Due to non-disclosure agreements related to industrial research projects (e.g., O&G sector), the datasets provided in this repository are simulated or baseline open-source data strictly for demonstration purposes. No proprietary data from external partners is disclosed.

---

## 🎯 Key Features

* **Automated Data Import:** Batch processing of raw spectrum files from multiple vendors (e.g., `.CSV`, `.SPA`, `.TXT`, `.DPT`).
* **Advanced Signal Processing:**
    * Automatic Polynomial Baseline Correction.
    * Transmittance to Absorbance conversion.
    * Noise reduction using the **Savitzky-Golay** filter to preserve peak integrity.
    * 1st and 2nd Derivative calculations to reveal hidden peak shoulders.
* **Quantitative Analysis:** Interactive numerical integration (Area Under the Curve) using the trapezoidal rule, essential for calculating the Carbonyl Index (degradation) and Degree of Crystallinity.
* **Intelligent Identification (The "Chemical Magnifying Glass"):** Interactive plot annotations that match peak wavenumbers with a built-in dictionary of chemical bonds and functional groups (e.g., distinguishing Carbonyls, Amides, Hydroxyls).
* **Forensic Comparison:** Automatic "Butterfly Plot" (mirror graph) generation and Pearson correlation algorithm ($r > 0.99$) to match unknown samples against a custom internal spectral library.
* **Dynamic Visualization:** Interactive, high-resolution plotting (waterfall/cascade mode) for comparative analysis of multiple samples.

---

## 📸 Screenshots

*(Add your images here. Save the images in a folder named `assets` in your repository and update the links below)*

| Main Interface & Cascade Plot | Chemical Magnifying Glass & Integration |
| :---: | :---: |
| <img src="assets/interface_print.png" alt="Main Interface" width="400"/> | <img src="assets/lupa_print.png" alt="Chemical Lupa" width="400"/> |

---

## 🛠️ Technologies & Tools

* **Language:** Python 3.12
* **Graphical User Interface (GUI):** Tkinter (Native, lightweight, and fast)
* **Data Manipulation:** Pandas, NumPy
* **Scientific Computing:** SciPy (`savgol_filter`, `find_peaks`, `integrate`)
* **Visualization:** Matplotlib
* **Architecture:** Modular design with isolated logic and interface layers for scalability.

---

## 🚀 Installation and Usage

**Not a programmer?** You don't need to touch the code. Download the ready-to-use Windows executable (`.exe`) from the [Releases page](https://github.com/seu-usuario/nome-do-repo/releases).

**For developers and researchers:**

Markdown
1. **Clone the repository:**
   git clone [https://github.com/seu-usuario/nome-do-repo.git](https://github.com/seu-usuario/nome-do-repo.git)
   cd nome-do-repo
2. Install the required dependencies:
   pip install -r requirements.txt
3. Launch the suite:
   python main_launcher.py

##🗺️ Roadmap (Next Steps)

This project is continuously evolving into a complete Materials Characterization Suite. Upcoming modules include:[x] FTIR Pro (Current Release)[ ] DSC Module: Differential Scanning Calorimetry (Automated $T_g$ and $T_m$ calculation).[ ] TGA Module: Thermogravimetric Analysis (Mass loss step calculation and DTG curves).[ ] DMA Module: Dynamic Mechanical Analysis (Viscoelastic properties plotting).📚 Background & ImpactThis project was developed as part of an Undergraduate Research program focused on material integrity and degradation analysis. It bridges the gap between Materials Engineering and computational toolsets.Key Achievements:Reduced routine spectral analysis time by approximately 40%.Successfully processed over 500 samples during the research period.Standardized the reporting and baseline correction format for the entire laboratory.👨‍💻 AuthorLuiz Roberto Bastos de Oliveira Materials Engineering Student @ UFRJ | Undergraduate Researcher
   
