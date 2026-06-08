import sys
import os
import glob
import numpy as np
import pandas as pd
import chardet
from scipy.signal import savgol_filter, find_peaks
import plotly.graph_objs as go
import base64
import webbrowser

# ==============================================================================
#  SYSTEM UTILITIES AND PATHS
# ==============================================================================

def obter_diretorio_base():
    """Returns the correct path for .py (dev) or .exe (production)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def extrair_nome_dataset(nome_arquivo):
    nome_base, _ = os.path.splitext(os.path.basename(nome_arquivo))
    return nome_base

# ==============================================================================
#  FILE READING
# ==============================================================================

def processar_arquivo_unico(caminho_arquivo):
    nome_dataset = extrair_nome_dataset(caminho_arquivo)
    
    # 1. Detectar Encoding
    try:
        raw = open(caminho_arquivo, 'rb').read(10000)
        encoding = chardet.detect(raw)['encoding'] or 'latin-1'
    except Exception as e:
        print(f"Encoding warning: {e}")
        encoding = 'latin-1'

    # 2. Ler linhas brutas para análise inteligente
    try:
        with open(caminho_arquivo, 'r', encoding=encoding, errors='replace') as f:
            linhas_raw = f.readlines()
    except Exception:
        try:
            with open(caminho_arquivo, 'r', encoding='latin-1', errors='replace') as f:
                linhas_raw = f.readlines()
        except Exception:
            return nome_dataset, None

    # 3. Detectar automaticamente onde os dados numéricos começam
    primeira_linha_dados = 0
    for i, linha in enumerate(linhas_raw):
        linha_limpa = linha.strip().lstrip('\ufeff')  # Remove BOM
        if not linha_limpa:
            continue
        # Tenta separar e verificar se há pelo menos 2 números
        numeros_encontrados = 0
        for sep in [';', ',', '\t', ' ']:
            partes = [p.strip() for p in linha_limpa.split(sep) if p.strip()]
            nums = 0
            for p in partes:
                p_clean = p.replace(',', '.').replace(';', '.')
                try:
                    float(p_clean)
                    nums += 1
                except ValueError:
                    pass
            numeros_encontrados = max(numeros_encontrados, nums)
        if numeros_encontrados >= 2:
            primeira_linha_dados = i
            break

    # 4. Montar lista de estratégias (mais combinações, incluindo skiprows dinâmico)
    skiprows_list = sorted(set([primeira_linha_dados, 0, 1, 2, 3]))
    configuracoes = []
    for skip in skiprows_list:
        configuracoes.extend([
            {'sep': ';',  'decimal': ',', 'skiprows': skip},
            {'sep': ',',  'decimal': '.', 'skiprows': skip},
            {'sep': '\t', 'decimal': '.', 'skiprows': skip},
            {'sep': '\t', 'decimal': ',', 'skiprows': skip},
            {'sep': None, 'decimal': '.', 'skiprows': skip},
            {'sep': ';',  'decimal': '.', 'skiprows': skip},
        ])
    
    # Remove duplicatas mantendo ordem
    seen = set()
    configs_unicas = []
    for c in configuracoes:
        key = (c['sep'], c['decimal'], c['skiprows'])
        if key not in seen:
            seen.add(key)
            configs_unicas.append(c)

    df_final = None
    melhor_score = 0  # Quantas linhas válidas a melhor config conseguiu

    for config in configs_unicas:
        try:
            df_temp = pd.read_csv(
                caminho_arquivo,
                sep=config['sep'],
                decimal=config['decimal'],
                skiprows=config['skiprows'],
                header=None,
                engine='python',
                encoding=encoding,
                on_bad_lines='skip'
            )

            if df_temp.shape[1] < 2: continue
            
            # Tenta múltiplas combinações de colunas (não só 0 e 1)
            for col_x in range(min(df_temp.shape[1], 4)):
                for col_y in range(min(df_temp.shape[1], 4)):
                    if col_x == col_y: continue
                    
                    cx = pd.to_numeric(df_temp.iloc[:, col_x], errors='coerce')
                    cy = pd.to_numeric(df_temp.iloc[:, col_y], errors='coerce')
                    
                    valid = (cx.notna() & cy.notna()).sum()
                    
                    if valid > melhor_score and valid > 10:
                        # Verifica se col_x parece wavenumber (range > 50)
                        x_vals = cx.dropna()
                        if len(x_vals) > 0 and (x_vals.max() - x_vals.min()) > 50:
                            melhor_score = valid
                            df_candidato = pd.DataFrame({'wavenumber': cx, 'absorbancia': cy})
                            df_final = df_candidato.dropna().sort_values('wavenumber', ascending=False).reset_index(drop=True)
        
        except Exception:
            continue

    # 5. ÚLTIMO RECURSO: Parser manual linha a linha
    if df_final is None or df_final.empty or len(df_final) < 10:
        dados_x, dados_y = [], []
        for linha in linhas_raw[primeira_linha_dados:]:
            linha_limpa = linha.strip()
            if not linha_limpa:
                continue
            
            # Tenta cada separador
            for sep in [';', '\t', ',', ' ']:
                partes = [p.strip() for p in linha_limpa.split(sep) if p.strip()]
                if len(partes) >= 2:
                    try:
                        # Tenta limpar valores (trocar , e ; por . como decimal)
                        x_str = partes[0].replace(',', '.').replace(';', '.')
                        y_str = partes[1].replace(',', '.').replace(';', '.')
                        x_val = float(x_str)
                        y_val = float(y_str)
                        dados_x.append(x_val)
                        dados_y.append(y_val)
                        break
                    except ValueError:
                        # Tenta com 3ª coluna se 2ª falhar
                        if len(partes) >= 3:
                            try:
                                x_str = partes[0].replace(',', '.').replace(';', '.')
                                y_str = partes[2].replace(',', '.').replace(';', '.')
                                x_val = float(x_str)
                                y_val = float(y_str)
                                dados_x.append(x_val)
                                dados_y.append(y_val)
                                break
                            except ValueError:
                                continue
        
        if len(dados_x) > 10:
            df_final = pd.DataFrame({'wavenumber': dados_x, 'absorbancia': dados_y})
            df_final = df_final.sort_values('wavenumber', ascending=False).reset_index(drop=True)
            print(f"INFO: '{nome_dataset}' loaded via manual parser ({len(df_final)} points)")

    if df_final is None or df_final.empty:
        return nome_dataset, None

    return nome_dataset, df_final

# ==============================================================================
#  SIGNAL PROCESSING (FILTERS)
# ==============================================================================

def baseline_correction(y, poly_order=2):
    # Handle NaNs (cuts) by temporarily filling to calculate the baseline
    y_clean = np.nan_to_num(y, nan=np.nanmean(y))
    x = np.arange(len(y_clean))
    coeffs = np.polyfit(x, y_clean, poly_order)
    baseline = np.polyval(coeffs, x)
    return y - baseline

def apply_savgol_filter(y, window_size=11, poly_order=2, deriv=0):
    # Savgol does not like NaNs. If there is a crop, return without filtering.
    if np.isnan(y).any():
        return y 
        
    if len(y) <= window_size: window_size = len(y) - 1
    if window_size % 2 == 0: window_size += 1
    
    # Protection: Polynomial must be less than the window
    if window_size <= poly_order: poly_order = window_size - 1
    
    return savgol_filter(y, window_size, poly_order, deriv=deriv)

def detect_peaks_and_valleys(y, prominence=0.01, distance=5):
    # Fill NaNs with zero only for detection, to not stall
    y_proc = np.nan_to_num(y, nan=0)
    peaks, _ = find_peaks(y_proc, prominence=prominence, distance=distance)
    valleys, _ = find_peaks(-y_proc, prominence=prominence, distance=distance)
    return peaks, valleys

# ==============================================================================
#  SAMPLE IDENTIFICATION
# ==============================================================================

def alinhar_espectros(x_amostra, y_amostra, x_ref, y_ref):
    # Intersection
    min_x = max(x_amostra.min(), x_ref.min())
    max_x = min(x_amostra.max(), x_ref.max())
    
    if max_x - min_x < 50: return None, None # Insufficient overlap

    # Create common axis
    x_comum = np.linspace(max_x, min_x, num=int(max_x - min_x)) 
    
    # Helper function to interpolate correctly (handling asc/desc order)
    def interpolar_seguro(x_in, y_in, x_target):
        # Remove NaNs before interpolating
        mask = ~np.isnan(y_in)
        if mask.sum() < 10: return None
        
        if x_in[0] > x_in[-1]: # Descending
            return np.interp(x_target, x_in[mask][::-1], y_in[mask][::-1])
        else:
            return np.interp(x_target, x_in[mask], y_in[mask])

    y_samp_interp = interpolar_seguro(x_amostra, y_amostra, x_comum)
    y_ref_interp = interpolar_seguro(x_ref, y_ref, x_comum)
    
    if y_samp_interp is None or y_ref_interp is None: return None, None
        
    return y_samp_interp, y_ref_interp

def identificar_amostra(df_amostra):
    base_path = obter_diretorio_base()
    pasta_lib = os.path.join(base_path, "biblioteca_espectros")
    
    if not os.path.exists(pasta_lib):
        # ... (code to create folder same as before) ...
        return []  # Returns empty if no lib
        
    arquivos = glob.glob(os.path.join(pasta_lib, "*.csv"))
    resultados = []

    # 1. Prepare the UNKNOWN SAMPLE
    df_amostra = df_amostra.dropna()
    x_samp = df_amostra['wavenumber'].values
    y_samp = df_amostra['absorbancia'].values
    
    # Apply correction to the sample
    y_samp = baseline_correction(y_samp) 

    for caminho_ref in arquivos:
        try:
            _, df_ref = processar_arquivo_unico(caminho_ref)
            if df_ref is None: continue
            
            x_ref = df_ref['wavenumber'].values
            y_ref_raw = df_ref['absorbancia'].values
            
            # 2. Prepare the REFERENCE (LIBRARY)
            # THE KEY STEP: We also correct the baseline of the reference!
            y_ref = baseline_correction(y_ref_raw)  # <<<< CORRECTION HERE
            
            # 3. Align X axes (Interpolation)
            y_samp_new, y_ref_new = alinhar_espectros(
                x_samp, y_samp, x_ref, y_ref
            )
            
            if y_samp_new is not None:
                # 4. Pearson Calculation
                score = np.corrcoef(y_samp_new, y_ref_new)[0, 1]
                resultados.append((extrair_nome_dataset(caminho_ref), score * 100))
        except Exception as e:
            print(f"Error comparing with {caminho_ref}: {e}")
            continue

    resultados.sort(key=lambda x: x[1], reverse=True)
    return resultados

# ==============================================================================
#  QUANTITATIVE CALCULATION (AREA/INTEGRATION)
# ==============================================================================

def calcular_area_pico(df, inicio, fim):
    """
    Calculates the area under the curve (integral) between two wavenumbers.
    Uses a 'local baseline' (chord) to subtract the background.
    """
    # 1. Filter data in the region
    # Note: In FTIR, wavenumbers generally decrease, so we ensure min/max
    mask = (df['wavenumber'] >= min(inicio, fim)) & (df['wavenumber'] <= max(inicio, fim))
    df_cut = df[mask].copy()
    
    if len(df_cut) < 2: return 0.0, None, None

    # Sort by x for the math to work (ascending)
    df_cut = df_cut.sort_values('wavenumber')
    x = df_cut['wavenumber'].values
    y = df_cut['absorbancia'].values

    # 2. Create the Local Baseline (Line between the first and last point)
    # Line equation: y = mx + c
    x1, y1 = x[0], y[0]
    x2, y2 = x[-1], y[-1]
    
    m = (y2 - y1) / (x2 - x1)
    c = y1 - m * x1
    y_baseline_local = m * x + c

    # 3. Subtract the baseline to get only the peak area
    y_pico_real = y - y_baseline_local

    # 4. Integration (Trapezoidal Rule)
    # The trapz function calculates the area under the curve.
    # We use abs() because in FTIR x decreases, which can invert the sign.
    area = np.trapz(y_pico_real, x)
    
    return abs(area), x, y_baseline_local

# ==============================================================================
#  OPERATIONS BETWEEN SPECTRA (Subtraction, Difference, Ratio)
# ==============================================================================

def interpolar_para_eixo_comum(df1, df2, n_pontos=2000):
    """Interpolates two spectra to a common X axis."""
    df1c = df1.dropna().sort_values('wavenumber')
    df2c = df2.dropna().sort_values('wavenumber')
    
    x_min = max(df1c['wavenumber'].min(), df2c['wavenumber'].min())
    x_max = min(df1c['wavenumber'].max(), df2c['wavenumber'].max())
    
    if x_max - x_min < 50:
        return None, None, None
    
    x_comum = np.linspace(x_min, x_max, n_pontos)
    y1 = np.interp(x_comum, df1c['wavenumber'].values, df1c['absorbancia'].values)
    y2 = np.interp(x_comum, df2c['wavenumber'].values, df2c['absorbancia'].values)
    
    return x_comum, y1, y2

def subtrair_espectros(df1, df2):
    """Returns df1 - df2 interpolated to a common axis."""
    x, y1, y2 = interpolar_para_eixo_comum(df1, df2)
    if x is None:
        return None
    return pd.DataFrame({'wavenumber': x, 'absorbancia': y1 - y2})

def razao_picos(df, centro1, centro2, largura=10):
    """Calculates ratio between peak intensities."""
    df_clean = df.dropna()
    
    mask1 = (df_clean['wavenumber'] >= centro1 - largura) & (df_clean['wavenumber'] <= centro1 + largura)
    mask2 = (df_clean['wavenumber'] >= centro2 - largura) & (df_clean['wavenumber'] <= centro2 + largura)
    
    y1 = df_clean.loc[mask1, 'absorbancia']
    y2 = df_clean.loc[mask2, 'absorbancia']
    
    if len(y1) == 0 or len(y2) == 0:
        return None, 0, 0
    
    intensidade1 = y1.max()
    intensidade2 = y2.max()
    
    if intensidade2 == 0:
        return float('inf'), intensidade1, intensidade2
    
    return intensidade1 / intensidade2, intensidade1, intensidade2

# ==============================================================================
#  CONVERSIONS (Transmittance ↔ Absorbance)
# ==============================================================================

def converter_T_A(y_values, direcao='T->A'):
    """Converte entre Transmitância (%) e Absorbância."""
    if direcao == 'T->A':
        y_safe = np.where(y_values <= 0, 0.001, y_values)
        return -np.log10(y_safe / 100.0)
    else:  # A->T
        return 100.0 * np.power(10, -np.abs(y_values))

def correcao_atr(wavenumbers, absorbancia, n_cristal=2.4, n_amostra=1.5, angulo=45):
    """Correção ATR baseada na profundidade de penetração."""
    theta = np.radians(angulo)
    sin2 = np.sin(theta) ** 2
    ratio2 = (n_amostra / n_cristal) ** 2
    
    if sin2 <= ratio2:
        return absorbancia  # Invalid angle
    
    dp = 1.0 / (wavenumbers * np.pi * n_cristal * np.sqrt(sin2 - ratio2))
    dp_norm = dp / np.nanmax(dp)
    dp_norm = np.where(dp_norm < 0.01, 0.01, dp_norm)
    
    return absorbancia / dp_norm

# ==============================================================================
#  ADVANCED BASELINES (ALS, Rubberband)
# ==============================================================================

def baseline_als(y, lam=1e6, p=0.01, niter=10):
    """Asymmetric Least Squares (ALS) baseline correction."""
    from scipy import sparse
    from scipy.sparse.linalg import spsolve
    
    y_clean = np.nan_to_num(y, nan=np.nanmean(y))
    L = len(y_clean)
    D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L-2))
    D = lam * D.dot(D.transpose())
    w = np.ones(L)
    
    for _ in range(niter):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + D
        z = spsolve(Z, w * y_clean)
        w = p * (y_clean > z) + (1 - p) * (y_clean < z)
    
    return y - z

def baseline_rubberband(x, y):
    """Rubber band baseline correction."""
    from scipy.spatial import ConvexHull
    
    y_clean = np.nan_to_num(y, nan=np.nanmean(y))
    points = np.column_stack([x, y_clean])
    
    try:
        hull = ConvexHull(points)
        v = hull.vertices
        v = np.sort(v)
        
        # Get only the lower part of the hull
        hull_x = x[v]
        hull_y = y_clean[v]
        
        # Interpolate baseline
        baseline = np.interp(x, hull_x, hull_y)
        
        # Ensure baseline does not exceed the signal
        baseline = np.minimum(baseline, y_clean)
        
        return y - baseline
    except Exception:
        return y - np.nanmin(y)

# ==============================================================================
#  PCA (Principal Component Analysis)
# ==============================================================================

def calcular_pca(datasets_dict, nomes_selecionados):
    """PCA via numpy SVD. Returns scores, variance, names."""
    dfs = []
    for nome in nomes_selecionados:
        df = datasets_dict[nome].dropna().sort_values('wavenumber')
        if len(df) > 10:
            dfs.append(df)
        else:
            return None, None, None
    
    # Common X axis
    x_min = max(df['wavenumber'].min() for df in dfs)
    x_max = min(df['wavenumber'].max() for df in dfs)
    x_comum = np.linspace(x_min, x_max, 500)
    
    matrix = []
    for df in dfs:
        y_interp = np.interp(x_comum, df['wavenumber'].values, df['absorbancia'].values)
        matrix.append(y_interp)
    
    matrix = np.array(matrix)
    matrix -= matrix.mean(axis=0)  # Center
    
    U, S, Vt = np.linalg.svd(matrix, full_matrices=False)
    scores = U * S
    var_explained = (S ** 2) / np.sum(S ** 2) * 100
    
    return scores, var_explained, x_comum

# ==============================================================================
#  PEAK DECONVOLUTION (Gaussian / Lorentzian)
# ==============================================================================

def _gaussian(x, amp, center, width):
    return amp * np.exp(-0.5 * ((x - center) / width) ** 2)

def _lorentzian(x, amp, center, width):
    return amp * width ** 2 / ((x - center) ** 2 + width ** 2)

def deconvolucao_picos(x, y, centros_iniciais, tipo='gaussian'):
    """Fits multiple Gaussian or Lorentzian peaks to the spectrum."""
    from scipy.optimize import curve_fit
    
    func = _gaussian if tipo == 'gaussian' else _lorentzian
    n_picos = len(centros_iniciais)
    
    def multi_peak(x, *params):
        result = np.zeros_like(x, dtype=float)
        for i in range(n_picos):
            result += func(x, params[i*3], params[i*3+1], params[i*3+2])
        return result
    
    # Initial guesses
    p0 = []
    for c in centros_iniciais:
        idx = np.argmin(np.abs(x - c))
        p0.extend([y[idx], c, 20.0])
    
    try:
        popt, _ = curve_fit(multi_peak, x, y, p0=p0, maxfev=10000)
        y_fit = multi_peak(x, *popt)
        
        picos = []
        for i in range(n_picos):
            picos.append({
                'amplitude': popt[i*3],
                'centro': popt[i*3 + 1],
                'largura': abs(popt[i*3 + 2]),
            })
        
        return y_fit, picos, func
    except Exception as e:
        print(f"Deconvolution error: {e}")
        return None, None, None

# ==============================================================================
#  PDF REPORT
# ==============================================================================

def gerar_relatorio_pdf(caminho, nome_amostra, figura, picos_data, areas_data, filtro_info):
    """Generates a PDF report with chart and data."""
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt
    from datetime import datetime
    import io, pickle
    
    with PdfPages(caminho) as pdf:
        # Page 1: Copy of the chart
        try:
            buf = io.BytesIO()
            pickle.dump(figura, buf)
            buf.seek(0)
            fig_copy = pickle.load(buf)
            pdf.savefig(fig_copy, dpi=150)
            plt.close(fig_copy)
        except Exception:
            pdf.savefig(figura, dpi=150)
        
        # Page 2: Data and tables
        fig2, ax2 = plt.subplots(figsize=(8.5, 11))
        ax2.axis('off')
        
        ax2.text(0.5, 0.95, f"FTIR Report — {nome_amostra}",
                 transform=ax2.transAxes, ha='center', fontsize=16, fontweight='bold')
        ax2.text(0.5, 0.92, f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                 transform=ax2.transAxes, ha='center', fontsize=10, color='gray')
        ax2.text(0.5, 0.89, f"Filtro: {filtro_info}",
                 transform=ax2.transAxes, ha='center', fontsize=10)
        
        y_pos = 0.83
        if picos_data:
            ax2.text(0.1, y_pos, "Detected Peaks:", fontsize=12, fontweight='bold',
                     transform=ax2.transAxes)
            y_pos -= 0.03
            ax2.text(0.1, y_pos, f"{'Position (cm⁻¹)':<25}{'Intensity':<15}",
                     fontsize=9, fontfamily='monospace', transform=ax2.transAxes)
            y_pos -= 0.02
            for pos, intens in picos_data[:30]:
                ax2.text(0.1, y_pos, f"{pos:<25.1f}{intens:<15.4f}",
                         fontsize=8, fontfamily='monospace', transform=ax2.transAxes)
                y_pos -= 0.018
                if y_pos < 0.15:
                    break
        
        if areas_data:
            y_pos -= 0.03
            ax2.text(0.1, y_pos, "Calculated Areas:", fontsize=12, fontweight='bold',
                     transform=ax2.transAxes)
            y_pos -= 0.03
            for area_info in areas_data:
                ax2.text(0.1, y_pos, f"Area = {area_info:.4f}",
                         fontsize=9, fontfamily='monospace', transform=ax2.transAxes)
                y_pos -= 0.02
        
        pdf.savefig(fig2, dpi=150)
        plt.close(fig2)

# ==============================================================================
#  ADVANCED PLOTLY
# ==============================================================================
def gerar_grafico_plotly(datasets_originais, datasets_selecionados, config_picos,
                         titulo, cores, zoom_wavenumber, zoom_absorbancia, corte_eixo):
    fig = go.Figure()

    for nome_base in datasets_selecionados:
        if nome_base not in datasets_originais:
            continue
        df = datasets_originais[nome_base].copy().dropna()
        df = df.sort_values('wavenumber', ascending=False)

        cor_atual = cores.get(nome_base, '#0000FF')
        fig.add_trace(go.Scatter(
            x=df['wavenumber'],
            y=df['absorbancia'],
            mode='lines',
            line=dict(color=cor_atual, width=2),
            name=nome_base
        ))

        # Picos
        y_processado = baseline_correction(df['absorbancia'].values)
        y_processado = apply_savgol_filter(y_processado)

        peaks, valleys = detect_peaks_and_valleys(
            y_processado,
            prominence=config_picos['prominence'],
            distance=config_picos['distance']
        )
        fig.add_trace(go.Scatter(
            x=df['wavenumber'].iloc[peaks],
            y=df['absorbancia'].iloc[peaks],
            mode='markers',
            marker=dict(symbol='x', size=8, color='red'),
            name=f"Peaks {nome_base}"
        ))
        fig.add_trace(go.Scatter(
            x=df['wavenumber'].iloc[valleys],
            y=df['absorbancia'].iloc[valleys],
            mode='markers',
            marker=dict(symbol='circle-open', size=8, color='blue'),
            name=f"Minima {nome_base}"
        ))

    fig.update_layout(
        title=dict(text=titulo, x=0.5),
        legend=dict(orientation='h', y=1.05, x=0.5, xanchor='center'),
        xaxis=dict(title='Wavenumber (cm⁻¹)'),
        yaxis=dict(title='Absorbance'),
        plot_bgcolor='white',
        xaxis_autorange='reversed'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

    filepath = os.path.join(os.getcwd(), "grafico_interativo.html")
    fig.write_html(filepath)
    try:
        import kaleido
        fig.write_image("grafico_interativo.png")
    except Exception as e:
        print(f"Could not save static image: {e}")
        pass
    webbrowser.open(f'file://{filepath}')
# ==============================================================================
#  CHEMICAL BOND DATABASE (For Polymers and Organics)
# ==============================================================================

TABELA_BANDAS = [
    # --- Hydrogen Region (High Frequency) ---
    {"nome": "O-H (Free)", "min": 3580, "max": 3700, "desc": "Alcohol/Phenol (Sharp)"},
    {"nome": "O-H (H-Bond)", "min": 3200, "max": 3550, "desc": "Alcohol/Water (Broad)"},
    {"nome": "N-H (Stretch)", "min": 3100, "max": 3500, "desc": "Amine/Amide (Nylon/PU)"},
    {"nome": "C-H (Aromatic)", "min": 3000, "max": 3100, "desc": "Benzene Ring (PS/PET)"},
    {"nome": "C-H (Aliphatic sp3)", "min": 2800, "max": 3000, "desc": "Carbon Chain (PE/PP)"},
    {"nome": "C-H (Aldehyde)", "min": 2700, "max": 2850, "desc": "Fermi Doublet"},
    
    # --- Triple and Cumulated Region ---
    {"nome": "C≡N (Nitrile)", "min": 2200, "max": 2260, "desc": "Acrylonitrile (PAN/ABS)"},
    {"nome": "C≡C (Alkyne)", "min": 2100, "max": 2260, "desc": "Weak"},
    {"nome": "O=C=N (Isocyanate)", "min": 2250, "max": 2275, "desc": "Uncured PU"},

    # --- Double Bond Region (Most Important) ---
    {"nome": "C=O (Ester)", "min": 1730, "max": 1750, "desc": "Polyester (PET/Acrylic)"},
    {"nome": "C=O (Ketone/Aldehyde)", "min": 1705, "max": 1725, "desc": "Base Carbonyl"},
    {"nome": "C=O (Carboxylic Acid)", "min": 1690, "max": 1760, "desc": "Broad if OH present"},
    {"nome": "C=O (Amide I)", "min": 1630, "max": 1690, "desc": "Nylon/Protein"},
    {"nome": "C=C (Alkene)", "min": 1600, "max": 1680, "desc": "Unsaturation (Rubber)"},
    {"nome": "C=C (Aromatic)", "min": 1450, "max": 1600, "desc": "Pair of peaks (PS/Epoxy)"},
    {"nome": "N-H (Amide II)", "min": 1500, "max": 1560, "desc": "Deformation (Nylon/PU)"},

    # --- Fingerprint Region ---
    {"nome": "CH2/CH3 (Deformation)", "min": 1350, "max": 1470, "desc": "PE/PP (Scissor/Umbrella)"},
    {"nome": "C-O (Stretch)", "min": 1000, "max": 1300, "desc": "Ether/Ester (Strong and Broad)"},
    {"nome": "C-H (Aromatic OOP)", "min": 670, "max": 900, "desc": "Ring Substitution (PS)"},
    {"nome": "C-Cl (Chloride)", "min": 600, "max": 800, "desc": "PVC (Usually in cut region)"}
]

def identificar_ligacao_quimica(wavenumber):
    """Retorna uma lista de possíveis ligações para aquele número de onda."""
    matches = []
    # Margem de erro de +/- 5 cm-1 para facilitar o clique
    busca = float(wavenumber)
    
    for banda in TABELA_BANDAS:
        if banda["min"] <= busca <= banda["max"]:
            matches.append(f"{banda['nome']}\n({banda['desc']})")
            
    if not matches:
        return "No common assignment\nfound."
    
    return "\nOR\n".join(matches)
