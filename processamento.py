import pandas as pd
import numpy as np
import chardet
from scipy.signal import savgol_filter, find_peaks
import plotly.graph_objs as go
import os
import webbrowser
import re
import csv
import base64

# ---------------------------------------------------

def extrair_nome_dataset(nome_arquivo):
    nome_base, _ = os.path.splitext(os.path.basename(nome_arquivo))
    nome_base = nome_base.split('_')[0]
    match = re.search(r'\((\d+(?:\.\d+)?)\)', nome_base)
    if match:
        return nome_base[:match.start()].strip() + f" ({match.group(1)})"
    else:
        return nome_base.strip()

# ---------------------------------------------------

def processar_arquivo_unico(caminho_arquivo):
    nome_dataset = extrair_nome_dataset(caminho_arquivo)
    
    # 1. Detectar Encoding (para evitar erros de caracteres estranhos)
    try:
        raw = open(caminho_arquivo, 'rb').read(10000)
        encoding = chardet.detect(raw)['encoding'] or 'latin-1'
    except:
        encoding = 'latin-1'

    # LISTA DE TENTATIVAS (CONFIGURAÇÕES POSSÍVEIS)
    # 1ª Tentativa: O formato do seu arquivo atual (Sep: ';', Dec: ',', Pula 2 linhas)
    # 2ª Tentativa: Formato CSV Padrão (Sep: ',', Dec: '.')
    # 3ª Tentativa: Formato TXT/Tabulação (Sep: '\t', Dec: '.')
    # 4ª Tentativa: Genérico (Sep: ' ', Dec: '.')
    # Se não funcionar, verificar arquivo e add separador / espaçamento específico  dele

    configuracoes = [
        {'sep': ';',  'decimal': ',', 'skiprows': 2}, # Seu caso específico (Prioridade)
        {'sep': ',',  'decimal': '.', 'skiprows': 0}, # Padrão Excel/EUA
        {'sep': '\t', 'decimal': '.', 'skiprows': 0}, # Arquivos .txt de instrumentos
        {'sep': None, 'decimal': '.', 'skiprows': 0}, # Tentativa automática do Pandas
        {'sep': ';',  'decimal': ',', 'skiprows': 0}, # Seu caso, mas sem cabeçalho
    ]

    df_final = None

    # LOOP DE TENTATIVAS
    for config in configuracoes:
        try:
            # Tenta ler com a configuração atual
            df_temp = pd.read_csv(
                caminho_arquivo,
                sep=config['sep'],
                decimal=config['decimal'],
                skiprows=config['skiprows'],
                header=None,
                engine='python', # Engine python é mais flexível
                encoding=encoding,
                on_bad_lines='skip' # Pula linhas quebradas sem travar
            )

            # --- VALIDAÇÃO: Isso é dados ou lixo? ---
            
            # Se tiver menos de 2 colunas, essa configuração falhou
            if df_temp.shape[1] < 2:
                continue
            
            # Pega as 2 primeiras colunas
            df_teste = df_temp.iloc[:, :2].copy()
            
            # Tenta converter para número
            col0 = pd.to_numeric(df_teste.iloc[:, 0], errors='coerce')
            col1 = pd.to_numeric(df_teste.iloc[:, 1], errors='coerce')
            
            # Conta quantos números válidos conseguimos
            validos = col0.notna() & col1.notna()
            contagem_validos = validos.sum()

            # REGRA DE SUCESSO:
            # Se conseguimos ler mais de 10 linhas de números puros, achamos a config certa!
            if contagem_validos > 10:
                df_final = df_teste
                df_final.columns = ['wavenumber', 'absorbancia']
                df_final['wavenumber'] = col0
                df_final['absorbancia'] = col1
                df_final = df_final.dropna().reset_index(drop=True)
                # Ordena (opcional, mas bom para FTIR)
                df_final = df_final.sort_values('wavenumber', ascending=False)
                print(f"Sucesso lendo {nome_dataset} com config: {config}")
                break # Para o loop, achamos o arquivo!
        
        except Exception:
            continue # Tenta a próxima configuração

    # Se saiu do loop e df_final ainda é None, falhou tudo
    if df_final is None or df_final.empty:
        print(f"FALHA FATAL: Não foi possível ler {nome_dataset} em nenhum formato conhecido.")
        return nome_dataset, None

    return nome_dataset, df_final

#  Aplicação de Filtros e Suavização -----

def baseline_correction(y, poly_order=2):
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, poly_order)
    return y - np.polyval(coeffs, x)

def apply_savgol_filter(y, window_size=11, poly_order=2):
    if len(y) <= window_size:
        window_size = len(y) - 1
    if window_size % 2 == 0:
        window_size += 1
    if window_size <= poly_order:
        return y
    return savgol_filter(y, window_size, poly_order)

def detect_peaks_and_valleys(y, prominence=0.01, distance=5):
    peaks, _ = find_peaks(y, prominence=prominence, distance=distance)
    valleys, _ = find_peaks(-y, prominence=prominence, distance=distance)
    return peaks, valleys

# ---------------------------------------------------

def normalize_column(dataframe, column_name):
    df = dataframe.copy()
    df[column_name] = pd.to_numeric(df[column_name], errors='coerce')
    df.dropna(subset=[column_name], inplace=True)
    min_val = df[column_name].min()
    max_val = df[column_name].max()
    if max_val - min_val == 0:
        return dataframe, False
    df[column_name] = (df[column_name] - min_val) / (max_val - min_val)
    return df, True

# ---------------------------------------------------

def gerar_grafico_plotly(datasets_originais, datasets_selecionados, config_picos,
                         titulo, cores, zoom_wavenumber, zoom_absorbancia, corte_eixo,
                         logo_path=None):
    fig = go.Figure()

    # 1. Adiciona as linhas dos espectros
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

        # Processamento para detecção de picos (para mostrar os marcadores 'x')
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
            name=f"Picos {nome_base}",
            showlegend=True # Oculta picos da legenda para limpar o visual
        ))

    # 2. Configuração da Logo (Estilo Assinatura)
    if logo_path and os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            fig.add_layout_image(
                dict(
                    source=f'data:image/png;base64,{encoded_string}',
                    xref="paper", yref="paper",
                    # Posição: Canto Inferior (0) Direito (1)
                    x=1, y=0,
                    sizex=0.15, sizey=0.15, # Tamanho da logo (ajuste preferência)
                    xanchor="right", yanchor="bottom", # Localizando a imagem no canto 
                    opacity=0.6, # Levemente transparente para parecer marca d'água
                    layer="above"
                )
            )
        except Exception as e:
            print(f"Erro na logo: {e}")

    # 3. Layout Limpo e Branco
    fig.update_layout(
        title=dict(text=titulo, x=0.5, font=dict(size=20, color='black')),
        legend=dict(
            orientation='h', 
            y=1.02, x=0.5, xanchor='center',
            bgcolor='rgba(255,255,255,0.8)' # Fundo da legenda semitransparente
        ),
        xaxis=dict(
            title='Número de onda (cm⁻¹)',
            showline=True, linewidth=1, linecolor='black', # Linha do eixo X preta
            mirror=True # Borda em cima também
        ),
        yaxis=dict(
            title='Absorbância',
            showline=True, linewidth=1, linecolor='black', # Linha do eixo Y preta
            mirror=True # Borda na direita também
        ),
        # FUNDO BRANCO TOTAL
        paper_bgcolor='white', # Cor de fundo fora do gráfico
        plot_bgcolor='white',  # Cor de fundo dentro do gráfico
        font=dict(color='black'), # Texto preto
        xaxis_autorange='reversed',
        margin=dict(l=60, r=40, t=80, b=60) # Margens para dar respiro
    )
    
    # Grade cinza bem suave (padrão literário)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#E5E5E5")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#E5E5E5")

    filepath = os.path.join(os.getcwd(), "grafico_interativo.html")
    fig.write_html(filepath)
    webbrowser.open(f'file://{filepath}')