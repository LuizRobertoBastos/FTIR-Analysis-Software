import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import pandas as pd
import numpy as np
import os
import glob
import shutil
from itertools import cycle
import copy 

# Bibliotecas de Gráfico
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import jcamp 

# Importa nosso módulo de lógica
import processamento

class AppFTIR(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FTIR Analyzer Pro 3.3 - LaCom / UFRJ")
        self.geometry("1400x900")

        # ÍCONE DO APLICATIVO
        try:
            self.iconbitmap("logo_lacom.ico.ico")
        except Exception:
            pass  # If icon not found, open without it

        # =======================================================
        # ESTADO E VARIÁVEIS DO SISTEMA
        # =======================================================
        self.datasets_originais = {}  
        self.datasets_carregados = {} 
        self.dataset_cores = {}
        self.dataset_estilos = {}     # 'solid', 'markers', 'both'
        self.dataset_espessuras = {}  # 1=fina, 2=normal, 3=grossa
        self.dataset_notas = {}       # Notas/observações por amostra
        self.metodo_baseline = 'polynomial'  # 'polynomial', 'als', 'rubberband'
        
        # Históricos de Edição
        self.historico_cortes = {}      # {'amostra': [(idx_start, idx_end), ...]}
        self.areas_calculadas = {}      # {'amostra': [(x_array, y_base_array, area_val), ...]}
        
        # Fs do Mouse (Seleção de Área)
        self.modo_selecao_area = False  
        self.ponto_inicio_area = None   
        self.linha_guia_area = None  
        
        # Modo de Análise Química (Lupa)
        self.modo_analise_quimica = False 
        self.anotacoes_quimicas = []
        
        # Notas no Gráfico (posicionadas pelo usuário)
        self.notas_grafico = []       # [(x, y, texto), ...]
        self.modo_nota_grafico = False      
        
        # Parâmetros do Filtro (Processamento)
        self.filtro_window = tk.IntVar(value=11)
        self.filtro_poly = tk.IntVar(value=2)
        self.filtro_derivada = tk.IntVar(value=0) # 0=Abs, 1=1ª Deriv, 2=2ª Deriv
        
        # Cache de Processamento
        self.cache_processamento = {}  # {'amostra': y_processado}
        self.cache_params = None       # (win, poly, deriv) - para invalidação
        
        # Presets de Filtros Salvos
        self.filtros_salvos = {
            "Default (Smooth)": {'w': 11, 'p': 2, 'd': 0},
            "Strong Noise Removal": {'w': 31, 'p': 3, 'd': 0},
            "Peak Search (Derivative)": {'w': 5, 'p': 2, 'd': 2}
        }
        
        # Ciclo de Cores para os Gráficos
        self.cores_ciclo = cycle(["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"])

        # =======================================================
        # BARRA DE MENU SUPERIOR
        # =======================================================
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Menu Biblioteca
        menu_lib = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📚 Library", menu=menu_lib)
        menu_lib.add_command(label="Manage Library (Add/Remove)", command=self.abrir_gerenciador_biblioteca)
        menu_lib.add_separator()
        menu_lib.add_command(label="Import from NIST (.jdx)", command=self.importar_jdx_nist)
        menu_lib.add_command(label="Load All to List", command=self.carregar_biblioteca_visual)
        
        # Settings menu
        menu_conf = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="⚙️ Settings", menu=menu_conf)
        menu_conf.add_command(label="Adjust Processing Filters", command=self.abrir_config_filtros)
        
        # Quick access button
        menubar.add_command(label="🔧 Edit Filters", command=self.abrir_config_filtros)
        
        # Help menu
        menu_ajuda = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Help", menu=menu_ajuda)
        menu_ajuda.add_command(label="📖 User Guide", command=self.abrir_guia_uso)
        menu_ajuda.add_command(label="ℹ️ About", command=self.abrir_sobre)

        # =======================================================
        # LAYOUT PRINCIPAL (DIVISÃO ESQUERDA / DIREITA)
        # =======================================================
        frame_esquerda = ttk.Frame(self, width=280)
        frame_esquerda.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        frame_esquerda.pack_propagate(False)
        
        frame_direita = ttk.Frame(self)
        frame_direita.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- PAINEL ESQUERDO SCROLLÁVEL ---
        self.canvas_painel = tk.Canvas(frame_esquerda, highlightthickness=0)
        scrollbar_painel = ttk.Scrollbar(frame_esquerda, orient="vertical", command=self.canvas_painel.yview)
        
        # Frame interno onde os widgets ficam
        frame_conteudo = ttk.Frame(self.canvas_painel)
        
        frame_conteudo.bind("<Configure>", lambda e: self.canvas_painel.configure(scrollregion=self.canvas_painel.bbox("all")))
        
        self.canvas_painel.create_window((0, 0), window=frame_conteudo, anchor="nw")
        self.canvas_painel.configure(yscrollcommand=scrollbar_painel.set)
        
        scrollbar_painel.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas_painel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scroll com rodinha do mouse APENAS quando o cursor está no painel
        def _on_mousewheel_painel(event):
            self.canvas_painel.yview_scroll(int(-1*(event.delta/120)), "units")
        def _bind_mousewheel(event):
            self.canvas_painel.bind_all("<MouseWheel>", _on_mousewheel_painel)
        def _unbind_mousewheel(event):
            self.canvas_painel.unbind_all("<MouseWheel>")
        self.canvas_painel.bind("<Enter>", _bind_mousewheel)
        self.canvas_painel.bind("<Leave>", _unbind_mousewheel)

        # --- PAINEL ESQUERDO: CONTROLES (dentro do frame_conteudo) ---
        
        # 1. Lista de Arquivos
        fr_arq = ttk.LabelFrame(frame_conteudo, text="1. Samples")
        fr_arq.pack(fill=tk.X, pady=5, padx=3)
        ttk.Button(fr_arq, text="📂 Load Files", command=self.carregar_arquivos).pack(fill=tk.X, padx=5, pady=2)
        
        self.lista_datasets = tk.Listbox(fr_arq, selectmode=tk.MULTIPLE, height=10)
        self.lista_datasets.pack(fill=tk.X, padx=5, pady=5)
        self.lista_datasets.bind('<<ListboxSelect>>', self.agendar_atualizacao)

        # Right-click bind
        self.lista_datasets.bind('<Button-3>', self.abrir_menu_contexto)

        # 2. Visualization controls
        fr_vis = ttk.LabelFrame(frame_conteudo, text="2. Visualization")
        fr_vis.pack(fill=tk.X, pady=5, padx=3)
        
        self.show_original = tk.BooleanVar(value=True)
        self.show_processado = tk.BooleanVar(value=False)
        self.show_picos = tk.BooleanVar(value=True)
        self.show_labels = tk.BooleanVar(value=False)
        self.modo_cascata_var = tk.BooleanVar(value=False) 
        self.normalizar_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(fr_vis, text="Original (Dashed)", variable=self.show_original, command=self.atualizar_visualizacao).pack(anchor='w', padx=5)
        ttk.Checkbutton(fr_vis, text="Processed (Solid)", variable=self.show_processado, command=self.atualizar_visualizacao).pack(anchor='w', padx=5)
        ttk.Checkbutton(fr_vis, text="Show Values (cm⁻¹)", variable=self.show_labels, command=self.atualizar_visualizacao).pack(anchor='w', padx=5)
        ttk.Checkbutton(fr_vis, text="📏 Normalize (0-1)", variable=self.normalizar_var, command=self.atualizar_visualizacao).pack(anchor='w', padx=5)
        ttk.Separator(fr_vis, orient='horizontal').pack(fill=tk.X, pady=5)
        ttk.Checkbutton(fr_vis, text="🌊 Waterfall Mode (Offset)", variable=self.modo_cascata_var, command=self.atualizar_visualizacao).pack(anchor='w', padx=5) 
        
        # Active filter indicator
        self.label_filtro = ttk.Label(fr_vis, text="Filter: W=11, P=2, D=0", font=('Arial', 8))
        self.label_filtro.pack(anchor='w', padx=5, pady=(5,0))

        # 3. Ferramentas de Engenharia
        fr_tools = ttk.LabelFrame(frame_conteudo, text="3. Tools & Actions")
        fr_tools.pack(fill=tk.X, pady=5, padx=3)
        
        btn_frame = ttk.Frame(fr_tools)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="⚙️ Filters", command=self.abrir_config_filtros, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✂️ Crop", command=self.cortar_regiao, width=10).pack(side=tk.LEFT, padx=2)
        
        self.btn_area = ttk.Button(fr_tools, text="📐 Select Area (Mouse)", command=self.ativar_selecao_area)
        self.btn_area.pack(fill=tk.X, padx=5, pady=2)

        self.btn_quimica = ttk.Button(fr_tools, text="🔍 What is this peak?", command=self.ativar_analise_quimica)
        self.btn_quimica.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(fr_tools, text="🔢 Area (Manual)", command=self.calcular_area_manual).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(fr_tools, text="↺ Reset Sample", command=self.resetar_amostra).pack(fill=tk.X, padx=5, pady=2) 
        ttk.Button(fr_tools, text="↩ Undo Last Crop", command=self.desfazer_ultimo_corte).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_tools, text="📝 Add Note to Graph", command=self.ativar_nota_grafico).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_tools, text="🗑️ Clear Annotations", command=self.limpar_anotacoes).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_tools, text="🔍 Identify (Blind Search)", command=self.acao_identificar).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_tools, text="🆚 Compare with Standard", command=self.acao_comparar_especifico).pack(fill=tk.X, padx=5, pady=2) 

        # 4. Export
        fr_exp = ttk.LabelFrame(frame_conteudo, text="4. Export")
        fr_exp.pack(fill=tk.X, pady=5, padx=3)
        ttk.Button(fr_exp, text="📊 Interactive Chart (HTML)", command=self.abrir_janela_plot_avancado).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_exp, text="💾 Save CSV (Peaks)", command=self.exportar_picos).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_exp, text="📸 Save Image (PNG)", command=self.salvar_imagem_png).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_exp, text="📄 PDF Report", command=self.acao_relatorio_pdf).pack(fill=tk.X, padx=5, pady=2)

        # 5. Advanced Analysis
        fr_adv = ttk.LabelFrame(frame_conteudo, text="5. Advanced Analysis")
        fr_adv.pack(fill=tk.X, pady=5, padx=3)
        
        ttk.Button(fr_adv, text="🔄 Convert T↔A", command=self.acao_converter_T_A).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_adv, text="➖ Subtract Spectra", command=self.acao_subtrair).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_adv, text="📊 Peak Ratio", command=self.acao_razao_picos).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_adv, text="🔬 ATR Correction", command=self.acao_correcao_atr).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_adv, text="📈 Peak Deconvolution", command=self.acao_deconvolucao).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(fr_adv, text="📉 PCA (Multivariate)", command=self.acao_pca).pack(fill=tk.X, padx=5, pady=2)
        
        # Baseline selector
        fr_bl = ttk.Frame(fr_adv)
        fr_bl.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(fr_bl, text="Baseline:").pack(side=tk.LEFT)
        self.combo_baseline = ttk.Combobox(fr_bl, values=['Polynomial', 'ALS', 'Rubberband'], state='readonly', width=12)
        self.combo_baseline.set('Polynomial')
        self.combo_baseline.pack(side=tk.LEFT, padx=5)
        self.combo_baseline.bind('<<ComboboxSelected>>', self.ao_mudar_baseline)

        # --- PAINEL DIREITO: GRÁFICO ---
        plot_frame = ttk.Frame(frame_direita)
        plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.figura = Figure(figsize=(8, 6), dpi=100)
        self.ax_plot = self.figura.add_subplot(111)
        
        self.canvas = FigureCanvasTkAgg(self.figura, master=plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # CONEXÃO DO MOUSE (IMPORTANTE)
        self.canvas.mpl_connect("button_press_event", self.ao_clicar_no_grafico)
        self.canvas.mpl_connect("scroll_event", self.ao_scroll_zoom)
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, plot_frame)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Tabela de Picos
        table_frame = ttk.Frame(frame_direita, height=150)
        table_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        cols = ('amostra', 'posicao', 'intensidade')
        self.tabela_picos = ttk.Treeview(table_frame, columns=cols, show='headings', height=5)
        for col in cols: self.tabela_picos.heading(col, text=col.capitalize())
        self.tabela_picos.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tabela_picos.yview)
        self.tabela_picos.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # =======================================================
    # MOUSE E SELEÇÃO DE COR
    # =======================================================

    def abrir_menu_contexto(self, event):
        # Descobre em qual item o mouse clicou
        try:
            indice = self.lista_datasets.nearest(event.y)
            self.lista_datasets.selection_clear(0, tk.END)
            self.lista_datasets.selection_set(indice)
            self.lista_datasets.activate(indice)

            # Cria o menu flutuante
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="🎨 Change Color", command=self.mudar_cor_amostra)
            
            menu_estilo = tk.Menu(menu, tearoff=0)
            menu_estilo.add_command(label="─ Solid Line", command=lambda: self.mudar_estilo_amostra('solid'))
            menu_estilo.add_command(label="• Dots (Markers)", command=lambda: self.mudar_estilo_amostra('markers'))
            menu_estilo.add_command(label="─• Line + Dots", command=lambda: self.mudar_estilo_amostra('both'))
            menu.add_cascade(label="📊 Line Style", menu=menu_estilo)
            
            menu_esp = tk.Menu(menu, tearoff=0)
            menu_esp.add_command(label="Thin (1)", command=lambda: self.mudar_espessura_amostra(1))
            menu_esp.add_command(label="Normal (2)", command=lambda: self.mudar_espessura_amostra(2))
            menu_esp.add_command(label="Thick (3)", command=lambda: self.mudar_espessura_amostra(3))
            menu.add_cascade(label="📏 Line Width", menu=menu_esp)
            
            menu.add_separator()
            menu.add_command(label="📝 Notes", command=self.acao_notas_amostra)
            menu.add_separator()
            menu.add_command(label="❌ Remove Sample", command=self.remover_amostra_lista)

            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def mudar_cor_amostra(self):
        # Pega o item selecionado
        idx = self.lista_datasets.curselection()
        if not idx: return
        nome = self.lista_datasets.get(idx[0])

        # Abre o seletor de cor do Windows
        cor_atual = self.dataset_cores.get(nome, '#000000')
        _, nova_cor = colorchooser.askcolor(initialcolor=cor_atual, title=f"Color for {nome}")

        if nova_cor:
            self.dataset_cores[nome] = nova_cor
            self.atualizar_visualizacao()

    def remover_amostra_lista(self):
        idx = self.lista_datasets.curselection()
        if not idx: return
        nome = self.lista_datasets.get(idx[0])

        for d in [self.datasets_carregados, self.datasets_originais, self.dataset_cores,
                  self.dataset_estilos, self.dataset_espessuras, self.cache_processamento,
                  self.dataset_notas]:
            if nome in d: del d[nome]

        self.lista_datasets.delete(idx[0])
        self.atualizar_visualizacao()

    def mudar_estilo_amostra(self, estilo):
        idx = self.lista_datasets.curselection()
        if not idx: return
        nome = self.lista_datasets.get(idx[0])
        self.dataset_estilos[nome] = estilo
        self.atualizar_visualizacao()

    def mudar_espessura_amostra(self, espessura):
        idx = self.lista_datasets.curselection()
        if not idx: return
        nome = self.lista_datasets.get(idx[0])
        self.dataset_espessuras[nome] = espessura
        self.atualizar_visualizacao()

    # =======================================================
    # LÓGICA DO MOUSE (SELEÇÃO DE ÁREA)
    # =======================================================

    def ativar_selecao_area(self):
        """Ativa o modo de seleção. O usuário deve clicar no gráfico."""
        indices = self.lista_datasets.curselection()
        if not indices:
            messagebox.showwarning("Warning", "Select a sample first from the side list.")
            return
            
        self.modo_selecao_area = True
        self.ponto_inicio_area = None
        
        # Feedback visual
        self.btn_area.config(text="CLICK ON THE PEAK START...")
        self.config(cursor="crosshair") # Muda o cursor para uma mira
        messagebox.showinfo("Instruction", "Area Mode Active:\n1. Click on the LEFT side of the peak.\n2. Click on the RIGHT side of the peak.")

    def ao_clicar_no_grafico(self, event):
        if event.inaxes != self.ax_plot: return

        # CASO 0: Nota no Gráfico
        if self.modo_nota_grafico:
            self.tratar_clique_nota(event)
            return

        # CASO 1: Análise Química (Prioridade)
        if self.modo_analise_quimica:
            self.tratar_clique_quimico(event)
            return

        # CASO 2: Seleção de Área (Código antigo)
        if self.modo_selecao_area:
            # ... (seu código de área que já existe) ...
            x_clicado = event.xdata
            if self.ponto_inicio_area is None:
                self.ponto_inicio_area = x_clicado
                self.linha_guia_area = self.ax_plot.axvline(x=x_clicado, color='green', linestyle='--')
                self.canvas.draw()
                self.btn_area.config(text="CLICK ON THE PEAK END...")
            else:
                x_inicio = self.ponto_inicio_area
                x_fim = x_clicado
                self.modo_selecao_area = False
                self.ponto_inicio_area = None
                self.config(cursor="")
                self.btn_area.config(text="📐 Select Area (Mouse)")
                if self.linha_guia_area:
                    self.linha_guia_area.remove()
                    self.linha_guia_area = None
                self.finalizar_calculo_area(x_inicio, x_fim)

    def finalizar_calculo_area(self, inicio, fim):
        indices = self.lista_datasets.curselection()
        msg_result = "Calculated Areas:\n"
        
        for i in indices:
            nome = self.lista_datasets.get(i)
            df = self.datasets_carregados[nome]
            
            # Pega configuração atual de filtro
            win = self.filtro_window.get()
            poly = self.filtro_poly.get()
            
            # Processa o sinal para calcular a área no dado limpo
            y_base = processamento.baseline_correction(df['absorbancia'].values)
            try:
                # Tenta usar derivada se configurado, mas área costuma ser em Absorbância (deriv=0)
                y_proc = processamento.apply_savgol_filter(y_base, win, poly, deriv=0)
            except:
                y_proc = processamento.apply_savgol_filter(y_base, win, poly)
            
            df_proc = pd.DataFrame({'wavenumber': df['wavenumber'], 'absorbancia': y_proc})
            
            # Chama o processamento matemático
            area, x_area, y_baseline = processamento.calcular_area_pico(df_proc, inicio, fim)
            
            if area > 0:
                msg_result += f"\n{nome}: {area:.4f}"
                if nome not in self.areas_calculadas: self.areas_calculadas[nome] = []
                # Salva os dados geométricos para desenhar a hachura
                self.areas_calculadas[nome].append((x_area, y_baseline, area))

        self.atualizar_visualizacao()
        messagebox.showinfo("Integration Result", msg_result)
    
    # =======================================================
    # LÓGICA DE ANÁLISE QUÍMICA (CLICK)
    # =======================================================

    def ativar_analise_quimica(self):
        """Ativa o modo de identificação de picos."""
        self.modo_analise_quimica = True
        self.modo_selecao_area = False # Desativa o outro modo se estiver ligado
        
        self.config(cursor="help") # Muda cursor para '?' ou 'mãozinha'
        self.btn_quimica.config(text="CLICK ON THE PEAK...")
        messagebox.showinfo("Analysis Mode", "Click exactly on a peak to see which chemical bond it represents.")

    def tratar_clique_quimico(self, event):
        """Chamado pelo evento de clique quando o modo químico está ativo"""
        x_clicado = event.xdata
        y_clicado = event.ydata
        
        # 1. Busca a informação química
        try:
            texto_resultado = processamento.identificar_ligacao_quimica(x_clicado)
        except AttributeError:
            texto_resultado = "Erro: Atualize o processamento.py"

        # 2. Cria o balãozinho
        # MUDANÇA: Adicionei textcoords="offset points" e mudei xytext para (30, 30)
        # Isso garante que o texto apareça 30 pixels ao lado, visível em qualquer zoom.
        anotacao = self.ax_plot.annotate(
            f"{int(x_clicado)} cm⁻¹\n{texto_resultado}",
            xy=(x_clicado, y_clicado),
            xytext=(30, 30),                # <--- 30 pixels para direita e cima
            textcoords="offset points",     # <--- O PULO DO GATO (fixa em pixels)
            arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5),
            fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", fc="#ffffe0", alpha=0.9, ec="black") # Amarelo claro
        )
        
        self.canvas.draw()
        
        # 3. Reseta o botão
        self.modo_analise_quimica = False
        self.config(cursor="")
        self.btn_quimica.config(text="🔍 What is this peak?")
        
        # Salva referência (opcional, para limpar depois)
        self.anotacoes_quimicas.append(anotacao)
        
    # =======================================================
    # LÓGICA PRINCIPAL E ATUALIZAÇÃO DO GRÁFICO
    # =======================================================

    def agendar_atualizacao(self, event=None):
        self.after(50, self.atualizar_visualizacao)

    def carregar_arquivos(self):
        caminhos = filedialog.askopenfilenames(filetypes=[("Data Files", "*.txt *.csv *.dpt")])
        if not caminhos: return
        
        count = 0
        for caminho in caminhos:
            nome_ds, df = processamento.processar_arquivo_unico(caminho)
            if df is not None:
                if nome_ds not in self.datasets_carregados:
                    self.datasets_originais[nome_ds] = df.copy() 
                    self.datasets_carregados[nome_ds] = df.copy()
                    
                    # Inicializa listas vazias para essa nova amostra
                    self.historico_cortes[nome_ds] = []
                    self.areas_calculadas[nome_ds] = []
                    
                    self.lista_datasets.insert(tk.END, nome_ds)
                    self.dataset_cores[nome_ds] = next(self.cores_ciclo)
                    self.dataset_estilos[nome_ds] = 'solid'
                    self.dataset_espessuras[nome_ds] = 2
                    count += 1
        
        if count > 0: messagebox.showinfo("Done", f"{count} file(s) loaded.")

    def atualizar_visualizacao(self):
        self.ax_plot.clear()
        self.tabela_picos.delete(*self.tabela_picos.get_children())
        
        selecionados = [self.lista_datasets.get(i) for i in self.lista_datasets.curselection()]
        if not selecionados:
            self.canvas.draw()
            return

        usar_cascata = self.modo_cascata_var.get()
        usar_normalizar = self.normalizar_var.get()
        offset_step = 0.5 
        offset_counter = 0

        # Pega parâmetros dos sliders
        win = self.filtro_window.get()
        poly = self.filtro_poly.get()
        deriv = self.filtro_derivada.get()

        # Atualiza indicador de filtro
        self.label_filtro.config(text=f"Filter: W={win}, P={poly}, D={deriv}")

        # Invalida cache se parâmetros mudaram
        params_atuais = (win, poly, deriv)
        if self.cache_params != params_atuais:
            self.cache_processamento.clear()
            self.cache_params = params_atuais

        for nome in selecionados:
            df = self.datasets_carregados[nome]
            cor = self.dataset_cores.get(nome, 'black')
            estilo = self.dataset_estilos.get(nome, 'solid')
            espessura = self.dataset_espessuras.get(nome, 2)
            offset_val = offset_counter * offset_step if usar_cascata else 0

            # 1. Processamento (com cache)
            if nome in self.cache_processamento:
                y_proc = self.cache_processamento[nome]
            else:
                y_base = self.aplicar_baseline(df['absorbancia'].values, df['wavenumber'].values)
                try:
                    y_proc = processamento.apply_savgol_filter(y_base, window_size=win, poly_order=poly, deriv=deriv)
                except TypeError:
                    y_proc = processamento.apply_savgol_filter(y_base, window_size=win, poly_order=poly)
                self.cache_processamento[nome] = y_proc

            # 2. Normalização (se ativada)
            y_orig_base = df['absorbancia'].values.copy()
            y_proc_base = y_proc.copy()
            if usar_normalizar:
                # Normaliza original
                o_min, o_max = np.nanmin(y_orig_base), np.nanmax(y_orig_base)
                if o_max != o_min:
                    y_orig_base = (y_orig_base - o_min) / (o_max - o_min)
                # Normaliza processado
                p_min, p_max = np.nanmin(y_proc_base), np.nanmax(y_proc_base)
                if p_max != p_min:
                    y_proc_base = (y_proc_base - p_min) / (p_max - p_min)

            y_vis_orig = y_orig_base + offset_val
            y_vis_proc = y_proc_base + offset_val

            # Determina parâmetros de plot conforme estilo escolhido
            if estilo == 'markers':
                plot_kw = {'linestyle': 'None', 'marker': 'o', 'markersize': 3}
                plot_kw_orig = {'linestyle': 'None', 'marker': 'o', 'markersize': 2}
            elif estilo == 'both':
                plot_kw = {'linestyle': '-', 'marker': 'o', 'markersize': 2}
                plot_kw_orig = {'linestyle': '--', 'marker': 'o', 'markersize': 2}
            else:  # solid
                plot_kw = {'linestyle': '-'}
                plot_kw_orig = {'linestyle': '--'}

            # --- PLOT ORIGINAL ---
            if self.show_original.get():
                self.ax_plot.plot(df['wavenumber'], y_vis_orig, color=cor, alpha=0.3,
                                 linewidth=espessura * 0.7,
                                 label=f"{nome} (Raw)" if not usar_cascata else None,
                                 **plot_kw_orig)
                
                # Desenha cortes no original
                if nome in self.historico_cortes:
                    for (idx1, idx2) in self.historico_cortes[nome]:
                        x1, x2 = df['wavenumber'].iloc[idx1], df['wavenumber'].iloc[idx2]
                        y1, y2 = y_vis_orig[idx1], y_vis_orig[idx2]
                        self.ax_plot.plot([x1, x2], [y1, y2], color='red', linewidth=2, linestyle='-', alpha=0.5)

            # --- PLOT PROCESSADO ---
            if self.show_processado.get():
                lbl = nome if not usar_cascata else f"{nome} (+{offset_val:.1f})"
                self.ax_plot.plot(df['wavenumber'], y_vis_proc, color=cor, linewidth=espessura,
                                 label=lbl, **plot_kw)

                # Desenha cortes no processado
                if nome in self.historico_cortes:
                    for (idx1, idx2) in self.historico_cortes[nome]:
                        x1, x2 = df['wavenumber'].iloc[idx1], df['wavenumber'].iloc[idx2]
                        y1, y2 = y_vis_proc[idx1], y_vis_proc[idx2]
                        self.ax_plot.plot([x1, x2], [y1, y2], color='red', linewidth=2, linestyle='-')

                # --- DESENHO DAS ÁREAS (HACHURA) ---
                if nome in self.areas_calculadas:
                    for (x_area, y_baseline, area_val) in self.areas_calculadas[nome]:
                        y_curve_segment = np.interp(x_area, df['wavenumber'], y_proc_base)
                        self.ax_plot.fill_between(x_area, y_baseline + offset_val, y_curve_segment + offset_val, color=cor, alpha=0.4, hatch='///')
                        mid_idx = len(x_area)//2
                        self.ax_plot.text(x_area[mid_idx], y_curve_segment[mid_idx] + offset_val, f"A={area_val:.2f}", 
                                          color=cor, fontsize=9, fontweight='bold', ha='center', va='bottom')

                # --- PICOS E LABELS ---
                if self.show_picos.get():
                    picos, _ = processamento.detect_peaks_and_valleys(y_proc_base) 
                    if len(picos) > 0:
                        if self.show_labels.get():
                            for p in picos:
                                x_val = df['wavenumber'].iloc[p]
                                y_val = y_vis_proc[p]
                                self.ax_plot.annotate(f"{int(x_val)}", xy=(x_val, y_val), xytext=(0, 8), 
                                                      textcoords="offset points", rotation=90, fontsize=8, ha='center', va='bottom', color=cor)
                        for p in picos:
                            self.tabela_picos.insert('', tk.END, values=(nome, f"{df['wavenumber'].iloc[p]:.1f}", f"{y_proc_base[p]:.4f}"))

            offset_counter += 1

        self.ax_plot.set_xlabel("Wavenumber (cm⁻¹)")
        lbl_y = "Absorbance" if deriv == 0 else ("1st Deriv" if deriv == 1 else "2nd Deriv")
        self.ax_plot.set_ylabel(f"{lbl_y} (a.u.)")
        self.ax_plot.invert_xaxis()
        self.ax_plot.grid(True, linestyle=':', alpha=0.6)
        if len(selecionados) < 10: self.ax_plot.legend()
        self.figura.tight_layout()
        self.canvas.draw()

    # =======================================================
    # FERRAMENTAS: CORTE, ÁREA MANUAL, RESET
    # =======================================================

    def resetar_amostra(self):
        indices = self.lista_datasets.curselection()
        if not indices: return
        if messagebox.askyesno("Reset", "Undo all crops, areas and edits?"):
            for i in indices:
                nome = self.lista_datasets.get(i)
                self.datasets_carregados[nome] = self.datasets_originais[nome].copy()
                self.historico_cortes[nome] = [] 
                self.areas_calculadas[nome] = []
                if nome in self.cache_processamento: del self.cache_processamento[nome]
            self.atualizar_visualizacao()

    def desfazer_ultimo_corte(self):
        """Remove apenas o último corte, preservando os anteriores."""
        indices = self.lista_datasets.curselection()
        if not indices:
            messagebox.showwarning("Warning", "Select a sample.")
            return
        algum_desfeito = False
        for i in indices:
            nome = self.lista_datasets.get(i)
            if nome in self.historico_cortes and self.historico_cortes[nome]:
                self.historico_cortes[nome].pop()
                # Restaura do original e re-aplica cortes restantes
                self.datasets_carregados[nome] = self.datasets_originais[nome].copy()
                df = self.datasets_carregados[nome]
                for (idx_s, idx_e) in self.historico_cortes[nome]:
                    wn_s = df['wavenumber'].iloc[idx_s]
                    wn_e = df['wavenumber'].iloc[idx_e]
                    mask = (df['wavenumber'] >= min(wn_s, wn_e)) & (df['wavenumber'] <= max(wn_s, wn_e))
                    df.loc[mask, 'absorbancia'] = np.nan
                if nome in self.cache_processamento: del self.cache_processamento[nome]
                algum_desfeito = True
        if algum_desfeito:
            self.atualizar_visualizacao()
            messagebox.showinfo("Done", "Last crop undone.")
        else:
            messagebox.showinfo("Info", "No crop to undo.")

    def ativar_nota_grafico(self):
        """Ativa modo de posicionar nota no gráfico."""
        if self.modo_nota_grafico:
            self.modo_nota_grafico = False
            self.config(cursor="")
            return
        self.modo_nota_grafico = True
        self.config(cursor="tcross")

    def tratar_clique_nota(self, event):
        """Quando o gráfico é clicado no modo nota."""
        x_clicado = event.xdata
        y_clicado = event.ydata
        
        texto = simpledialog.askstring("Note", "Note text:")
        if not texto:
            self.modo_nota_grafico = False
            self.config(cursor="")
            return
        
        # Salva a nota (persiste entre redraws)
        self.notas_grafico.append((x_clicado, y_clicado, texto))
        
        # Desenha no gráfico
        anotacao = self.ax_plot.annotate(
            texto,
            xy=(x_clicado, y_clicado),
            xytext=(20, 25),
            textcoords="offset points",
            arrowprops=dict(facecolor='#4a90d9', shrink=0.05, width=1.5, headwidth=6, edgecolor='#4a90d9'),
            fontsize=9, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.4", fc="#d4e6f1", alpha=0.95, ec="#4a90d9", lw=1.5)
        )
        self.anotacoes_quimicas.append(anotacao)
        self.canvas.draw()
        
        self.modo_nota_grafico = False
        self.config(cursor="")

    def limpar_anotacoes(self):
        """Remove todos os balões de anotação e notas do gráfico."""
        for anotacao in self.anotacoes_quimicas:
            try:
                anotacao.remove()
            except Exception:
                pass
        self.anotacoes_quimicas.clear()
        self.notas_grafico.clear()
        self.canvas.draw()

    def salvar_imagem_png(self):
        """Salva o gráfico atual como imagem PNG de alta resolução."""
        caminho = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("SVG", "*.svg"), ("PDF", "*.pdf")],
            title="Save Chart"
        )
        if not caminho: return
        try:
            self.figura.savefig(caminho, dpi=300, bbox_inches='tight', facecolor='white')
            messagebox.showinfo("Saved", f"Image saved to:\n{caminho}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def ao_scroll_zoom(self, event):
        """Zoom com a rodinha do mouse, centrado no cursor."""
        if event.inaxes != self.ax_plot: return
        base_scale = 1.3
        cur_xlim = self.ax_plot.get_xlim()
        cur_ylim = self.ax_plot.get_ylim()
        xdata, ydata = event.xdata, event.ydata

        if event.button == 'up':
            scale = 1 / base_scale
        elif event.button == 'down':
            scale = base_scale
        else:
            return

        new_w = (cur_xlim[1] - cur_xlim[0]) * scale
        new_h = (cur_ylim[1] - cur_ylim[0]) * scale
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        self.ax_plot.set_xlim([xdata - new_w * (1 - relx), xdata + new_w * relx])
        self.ax_plot.set_ylim([ydata - new_h * (1 - rely), ydata + new_h * rely])
        self.canvas.draw_idle()

    def cortar_regiao(self):
        indices = self.lista_datasets.curselection()
        if not indices:
            messagebox.showwarning("Warning", "Select samples to crop.")
            return

        inicio = simpledialog.askfloat("Crop Data", "From (cm⁻¹):", minvalue=400, maxvalue=4000)
        if inicio is None: return
        fim = simpledialog.askfloat("Crop Data", "To (cm⁻¹):", minvalue=inicio, maxvalue=4000)
        if fim is None: return

        for i in indices:
            nome = self.lista_datasets.get(i)
            df = self.datasets_carregados[nome]
            
            mask = (df['wavenumber'] >= inicio) & (df['wavenumber'] <= fim)
            indices_afetados = np.where(mask)[0]
            
            if len(indices_afetados) > 0:
                idx_start = max(0, indices_afetados[0] - 1)
                idx_end = min(len(df)-1, indices_afetados[-1] + 1)
                
                if nome not in self.historico_cortes: self.historico_cortes[nome] = []
                self.historico_cortes[nome].append((idx_start, idx_end))
                
                df.loc[mask, 'absorbancia'] = np.nan
                self.datasets_carregados[nome] = df
                if nome in self.cache_processamento: del self.cache_processamento[nome]

        self.atualizar_visualizacao()
        messagebox.showinfo("Done", "Region cropped.")

    def calcular_area_manual(self):
        """Versão antiga (input de texto) mantida como backup"""
        indices = self.lista_datasets.curselection()
        if not indices: return
        inicio = simpledialog.askfloat("Manual Area", "Start (cm⁻¹):", minvalue=400, maxvalue=4000)
        if inicio is None: return
        fim = simpledialog.askfloat("Manual Area", "End (cm⁻¹):", minvalue=inicio, maxvalue=4000)
        if fim is None: return
        self.finalizar_calculo_area(inicio, fim)

    # =======================================================
    # IDENTIFICAÇÃO E BUTTERFLY PLOT
    # =======================================================

    def acao_identificar(self):
        idx = self.lista_datasets.curselection()
        if not idx:
            messagebox.showwarning("Warning", "Select a sample.")
            return
        
        nome_amostra = self.lista_datasets.get(idx[0])
        df_amostra = self.datasets_carregados[nome_amostra]
        resultados = processamento.identificar_amostra(df_amostra)
        
        top = tk.Toplevel(self)
        top.title(f"ID: {nome_amostra}")
        top.geometry("600x450")
        
        tv = ttk.Treeview(top, columns=('mat', 'score'), show='headings')
        tv.heading('mat', text='Material'); tv.heading('score', text='%')
        tv.pack(fill=tk.BOTH, expand=True)
        
        if resultados:
            for mat, score in resultados[:15]:
                tag = 'green' if score > 80 else ('orange' if score > 60 else 'red')
                tv.insert('', tk.END, values=(mat, f"{score:.2f}%"), tags=(tag,))
            tv.tag_configure('green', foreground='green')
            tv.tag_configure('orange', foreground='#cf7a00')
        
        def chamar_butterfly():
            sel = tv.selection()
            if not sel: return
            nome_ref = tv.item(sel[0])['values'][0]
            self.abrir_butterfly_plot(nome_amostra, df_amostra, nome_ref)

        ttk.Button(top, text="🦋 Visual Comparison (Mirror)", command=chamar_butterfly).pack(fill=tk.X, pady=10)

    def abrir_butterfly_plot(self, nome_amostra, df_amostra, nome_ref):
        base = processamento.obter_diretorio_base()
        caminho_ref = os.path.join(base, "biblioteca_espectros", f"{nome_ref}.csv")
        if not os.path.exists(caminho_ref):
            messagebox.showerror("Error", "Library file not found.")
            return
            
        _, df_ref = processamento.processar_arquivo_unico(caminho_ref)
        if df_ref is None: return

        import matplotlib.pyplot as plt
        win = self.filtro_window.get()
        poly = self.filtro_poly.get()
        
        # Processamento rápido para visualização
        y_samp = processamento.apply_savgol_filter(processamento.baseline_correction(df_amostra['absorbancia'].values), win, poly, 0)
        y_ref = processamento.apply_savgol_filter(processamento.baseline_correction(df_ref['absorbancia'].values), win, poly, 0)

        # Normalização
        if np.max(y_samp)!=0: y_samp/=np.max(y_samp)
        if np.max(y_ref)!=0: y_ref/=np.max(y_ref)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df_amostra['wavenumber'], y_samp, label=f"Sample: {nome_amostra}", color='#1f77b4')
        ax.fill_between(df_amostra['wavenumber'], y_samp, 0, alpha=0.3, color='#1f77b4')
        
        ax.plot(df_ref['wavenumber'], -y_ref, label=f"Ref: {nome_ref}", color='#d62728')
        ax.fill_between(df_ref['wavenumber'], -y_ref, 0, alpha=0.3, color='#d62728')
        
        ax.invert_xaxis()
        ax.axhline(0, color='black', linewidth=1)
        ax.legend()
        ax.set_title(f"Butterfly Plot: {nome_amostra} vs {nome_ref}")
        plt.show()

    # =======================================================
    # NOVA FUNÇÃO: COMPARAR ESPECÍFICO (CONTROLE DE QUALIDADE)
    # =======================================================
    def acao_comparar_especifico(self):
        # 1. Verifica se tem amostra selecionada
        idx = self.lista_datasets.curselection()
        if not idx:
            messagebox.showwarning("Ops", "Select your sample first from the left side list.")
            return
        
        nome_amostra = self.lista_datasets.get(idx[0])
        df_amostra = self.datasets_carregados[nome_amostra]
        
        # 2. Janela
        top = tk.Toplevel(self)
        top.title(f"Compare '{nome_amostra}' with...")
        top.geometry("400x450")
        
        ttk.Label(top, text="Choose a Standard from the Library:", font=('Arial', 10, 'bold')).pack(pady=5)

        # --- BARRA DE PESQUISA (A LUPA 🔍) ---
        fr_busca = ttk.Frame(top)
        fr_busca.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(fr_busca, text="🔍 Search:").pack(side=tk.LEFT)
        entry_busca = ttk.Entry(fr_busca)
        entry_busca.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 3. Lista e Scrollbar
        fr_lista = ttk.Frame(top)
        fr_lista.pack(fill=tk.BOTH, expand=True, padx=10)
        
        scrollbar = ttk.Scrollbar(fr_lista, orient="vertical")
        lista_ref = tk.Listbox(fr_lista, yscrollcommand=scrollbar.set, height=15)
        scrollbar.config(command=lista_ref.yview)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        lista_ref.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Carrega arquivos
        base = processamento.obter_diretorio_base()
        pasta_lib = os.path.join(base, "biblioteca_espectros")
        arquivos_brutos = glob.glob(os.path.join(pasta_lib, "*.csv"))
        
        # Lista limpa (apenas nomes) para facilitar a busca
        # Guardamos tuplas: (Nome Bonito, Caminho Completo)
        todos_itens = []
        if arquivos_brutos:
            for f in arquivos_brutos:
                nome_simples = os.path.basename(f).replace(".csv", "")
                todos_itens.append(nome_simples)
        
        # Função de Filtragem (Mágica da Busca)
        def atualizar_lista(termo=""):
            lista_ref.delete(0, tk.END)
            termo = termo.lower()
            for nome in todos_itens:
                if termo in nome.lower():
                    lista_ref.insert(tk.END, nome)
        
        # Inicializa a lista cheia
        atualizar_lista()
        
        # Liga a digitação à função de filtro
        entry_busca.bind("<KeyRelease>", lambda event: atualizar_lista(entry_busca.get()))
        
        # 4. Botão Confirmar
        def confirmar_comparacao():
            idx_ref = lista_ref.curselection()
            if not idx_ref: return
            
            nome_ref = lista_ref.get(idx_ref[0]) # Pega o nome selecionado
            top.destroy()
            
            self.abrir_butterfly_plot(nome_amostra, df_amostra, nome_ref)

        ttk.Button(top, text="Generate Comparison (Butterfly)", command=confirmar_comparacao).pack(fill=tk.X, padx=10, pady=10)
    # =======================================================
    # CONFIGURAÇÃO DE FILTROS E BIBLIOTECA (As funções que faltavam)
    # =======================================================

    def abrir_config_filtros(self):
        top = tk.Toplevel(self)
        top.title("Filter Editor")
        top.geometry("400x550")
        
        ttk.Label(top, text="Fine Processing Adjustment", font=('Arial', 11, 'bold')).pack(pady=10)
        
        # 1. Window
        fr_w = ttk.LabelFrame(top, text="Smoothing (Window)")
        fr_w.pack(fill=tk.X, padx=10, pady=5)
        lbl_w = tk.Label(fr_w, text=f"Points: {self.filtro_window.get()}")
        lbl_w.pack()
        def update_lbl_w(val):
            v = int(float(val))
            if v % 2 == 0: v += 1 
            self.filtro_window.set(v)
            lbl_w.config(text=f"Points: {v}")
            self.atualizar_visualizacao()
        sc_w = ttk.Scale(fr_w, from_=3, to=51, command=update_lbl_w)
        sc_w.set(self.filtro_window.get())
        sc_w.pack(fill=tk.X, padx=5)

        # 2. Poly
        fr_p = ttk.LabelFrame(top, text="Polynomial")
        fr_p.pack(fill=tk.X, padx=10, pady=5)
        lbl_p = tk.Label(fr_p, text=f"Order: {self.filtro_poly.get()}")
        lbl_p.pack()
        def update_lbl_p(val):
            v = int(float(val))
            self.filtro_poly.set(v)
            lbl_p.config(text=f"Order: {v}")
            self.atualizar_visualizacao()
        sc_p = ttk.Scale(fr_p, from_=1, to=5, command=update_lbl_p)
        sc_p.set(self.filtro_poly.get())
        sc_p.pack(fill=tk.X, padx=5)
        
        # 3. Derivada
        fr_d = ttk.LabelFrame(top, text="Math")
        fr_d.pack(fill=tk.X, padx=10, pady=5)
        ttk.Radiobutton(fr_d, text="Normal Spectrum", variable=self.filtro_derivada, value=0, command=self.atualizar_visualizacao).pack(anchor='w')
        ttk.Radiobutton(fr_d, text="1st Derivative", variable=self.filtro_derivada, value=1, command=self.atualizar_visualizacao).pack(anchor='w')
        ttk.Radiobutton(fr_d, text="2nd Derivative", variable=self.filtro_derivada, value=2, command=self.atualizar_visualizacao).pack(anchor='w')

        # 4. Gerenciamento de Presets
        fr_save = ttk.LabelFrame(top, text="Saved Presets")
        fr_save.pack(fill=tk.X, padx=10, pady=15)
        combo_filtros = ttk.Combobox(fr_save, values=list(self.filtros_salvos.keys()), state="readonly")
        combo_filtros.pack(fill=tk.X, padx=5, pady=2)

        def carregar_preset(event):
            nome = combo_filtros.get()
            if nome in self.filtros_salvos:
                vals = self.filtros_salvos[nome]
                self.filtro_window.set(vals['w'])
                self.filtro_poly.set(vals['p'])
                self.filtro_derivada.set(vals['d'])
                sc_w.set(vals['w']); sc_p.set(vals['p'])
                self.atualizar_visualizacao()
        combo_filtros.bind("<<ComboboxSelected>>", carregar_preset)

        entry_nome = ttk.Entry(fr_save)
        entry_nome.pack(fill=tk.X, padx=5, pady=2)
        entry_nome.insert(0, "New Filter")
        def salvar_preset():
            nome = entry_nome.get()
            if nome:
                self.filtros_salvos[nome] = {'w': self.filtro_window.get(), 'p': self.filtro_poly.get(), 'd': self.filtro_derivada.get()}
                combo_filtros['values'] = list(self.filtros_salvos.keys())
                messagebox.showinfo("Saved", "Filter saved.")
        ttk.Button(fr_save, text="Save Current Filter", command=salvar_preset).pack(fill=tk.X)

        # 5. Reset
        def resetar_fabrica():
            self.filtro_window.set(11); self.filtro_poly.set(2); self.filtro_derivada.set(0)
            sc_w.set(11); sc_p.set(2)
            self.atualizar_visualizacao()
        ttk.Separator(top, orient='horizontal').pack(fill=tk.X, pady=5)
        ttk.Button(top, text="↺ Reset to Default", command=resetar_fabrica).pack(fill=tk.X, padx=10, pady=10)

    def abrir_gerenciador_biblioteca(self):
        top = tk.Toplevel(self)
        top.title("Library Manager")
        top.geometry("600x450")
        
        # Frame Esquerdo (Lista + Busca)
        fr_esq = ttk.Frame(top)
        fr_esq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- BUSCA ---
        fr_busca = ttk.Frame(fr_esq)
        fr_busca.pack(fill=tk.X, pady=5)
        ttk.Label(fr_busca, text="🔍 Search:").pack(side=tk.LEFT)
        entry_filtro = ttk.Entry(fr_busca)
        entry_filtro.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Lista
        fr_lista = ttk.LabelFrame(fr_esq, text="Files (CSV)")
        fr_lista.pack(fill=tk.BOTH, expand=True)
        
        lista_lib = tk.Listbox(fr_lista)
        lista_lib.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame Direito (Botoes)
        fr_botoes = ttk.Frame(top)
        fr_botoes.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        base = processamento.obter_diretorio_base()
        pasta_lib = os.path.join(base, "biblioteca_espectros")
        if not os.path.exists(pasta_lib): os.makedirs(pasta_lib)

        # Variável para guardar todos os arquivos em memória
        self.cache_arquivos_lib = [] 

        def recarregar_lista(filtro=""):
            lista_lib.delete(0, tk.END)
            
            # Se o filtro estiver vazio, recarrega do disco (para pegar novos arquivos adicionados)
            # Se tiver filtro, usa o cache para ser rápido
            if not filtro:
                self.cache_arquivos_lib = []
                for f in glob.glob(os.path.join(pasta_lib, "*.csv")):
                    self.cache_arquivos_lib.append(os.path.basename(f))
            
            # Aplica o filtro
            termo = filtro.lower()
            for nome in self.cache_arquivos_lib:
                if termo in nome.lower():
                    lista_lib.insert(tk.END, nome)
        
        # Bind da busca
        entry_filtro.bind("<KeyRelease>", lambda event: recarregar_lista(entry_filtro.get()))

        def add():
            files = filedialog.askopenfilenames(filetypes=[("CSV", "*.csv")])
            for f in files: 
                try: shutil.copy(f, pasta_lib)
                except Exception as e: print(f"Erro ao copiar: {e}")
            entry_filtro.delete(0, tk.END) # Limpa busca ao adicionar
            recarregar_lista()
            
        def remove():
            idx = lista_lib.curselection()
            if not idx: return
            nome_arquivo = lista_lib.get(idx[0])
            if messagebox.askyesno("Confirm", f"Delete '{nome_arquivo}'?"):
                try:
                    os.remove(os.path.join(pasta_lib, nome_arquivo))
                    entry_filtro.delete(0, tk.END) # Limpa busca ao remover
                    recarregar_lista()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to remove: {e}")

        ttk.Button(fr_botoes, text="➕ Add CSV", command=add).pack(fill=tk.X, pady=5)
        ttk.Button(fr_botoes, text="🗑️ Remove Selected", command=remove).pack(fill=tk.X, pady=5)
        ttk.Button(fr_botoes, text="🔄 Refresh List", command=lambda: recarregar_lista("")).pack(fill=tk.X, pady=5)
        
        recarregar_lista()
        
    # =======================================================
    # IMPORTAR, EXPORTAR E PLOT AVANÇADO
    # =======================================================

    def importar_jdx_nist(self):
        path = filedialog.askopenfilename(filetypes=[("NIST JDX", "*.jdx")])
        if not path: return
        try:
            dados = jcamp.jcamp_read(path)
            x, y = np.array(dados['x']), np.array(dados['y'])
            if np.max(y) > 1.5: y = 2 - np.log10(np.where(y<=0, 0.001, y)) 
            else: y = -np.log10(np.where(y<=0, 0.0001, y)) 
            y = np.where(y<0, 0, y)
            df = pd.DataFrame({'wavenumber': x, 'absorbancia': y})
            base = processamento.obter_diretorio_base()
            dest = os.path.join(base, "biblioteca_espectros")
            if not os.path.exists(dest): os.makedirs(dest)
            nome_csv = os.path.splitext(os.path.basename(path))[0] + ".csv"
            df.to_csv(os.path.join(dest, nome_csv), sep=';', decimal=',', index=False)
            messagebox.showinfo("Done", f"Imported: {nome_csv}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def carregar_biblioteca_visual(self):
        base = processamento.obter_diretorio_base()
        for path in glob.glob(os.path.join(base, "biblioteca_espectros", "*.csv")):
            nome, df = processamento.processar_arquivo_unico(path)
            nome_lib = f"[LIB] {nome}"
            if df is not None and nome_lib not in self.datasets_carregados:
                self.datasets_originais[nome_lib] = df.copy()
                self.datasets_carregados[nome_lib] = df.copy()
                self.historico_cortes[nome_lib] = []
                self.areas_calculadas[nome_lib] = []
                self.lista_datasets.insert(tk.END, nome_lib)
                self.dataset_cores[nome_lib] = next(self.cores_ciclo)
                self.dataset_estilos[nome_lib] = 'solid'
                self.dataset_espessuras[nome_lib] = 2
        self.atualizar_visualizacao()

    def exportar_picos(self):
        idx = self.lista_datasets.curselection()
        if not idx: return
        data = []
        for i in idx:
            nome = self.lista_datasets.get(i)
            df = self.datasets_carregados[nome]
            y = processamento.apply_savgol_filter(processamento.baseline_correction(df['absorbancia'].values))
            picos, _ = processamento.detect_peaks_and_valleys(y)
            for p in picos:
                data.append({'Amostra': nome, 'cm-1': df['wavenumber'].iloc[p], 'Abs': y[p]})
        if data:
            pd.DataFrame(data).to_csv("Relatorio_Picos.csv", index=False, sep=';', decimal=',')
            messagebox.showinfo("Saved", "Peaks_Report.csv saved.")

    def abrir_janela_plot_avancado(self):
        if not self.datasets_carregados:
            messagebox.showwarning("Warning", "Load files first.")
            return
        janela_avancada = JanelaPlotly(self, self.datasets_carregados, self.dataset_cores)

    # =======================================================
    # ANÁLISE AVANÇADA (PESQUISA)
    # =======================================================

    def ao_mudar_baseline(self, event=None):
        sel = self.combo_baseline.get()
        mapa = {'Polynomial': 'polynomial', 'ALS': 'als', 'Rubberband': 'rubberband'}
        self.metodo_baseline = mapa.get(sel, 'polynomial')
        self.cache_processamento.clear()
        self.atualizar_visualizacao()

    def aplicar_baseline(self, y, x=None):
        """Aplica o método de baseline selecionado."""
        if self.metodo_baseline == 'als':
            return processamento.baseline_als(y)
        elif self.metodo_baseline == 'rubberband' and x is not None:
            return processamento.baseline_rubberband(x, y)
        else:
            return processamento.baseline_correction(y)

    def acao_converter_T_A(self):
        idx = self.lista_datasets.curselection()
        if not idx:
            messagebox.showwarning("Warning", "Select samples.")
            return
        
        top = tk.Toplevel(self)
        top.title("Convert T↔A")
        top.geometry("300x150")
        
        direcao = tk.StringVar(value='T->A')
        ttk.Label(top, text="Conversion direction:", font=('Arial', 10, 'bold')).pack(pady=10)
        ttk.Radiobutton(top, text="Transmittance → Absorbance", variable=direcao, value='T->A').pack(anchor='w', padx=20)
        ttk.Radiobutton(top, text="Absorbance → Transmittance", variable=direcao, value='A->T').pack(anchor='w', padx=20)
        
        def confirmar():
            for i in idx:
                nome = self.lista_datasets.get(i)
                df = self.datasets_carregados[nome]
                df['absorbancia'] = processamento.converter_T_A(df['absorbancia'].values, direcao.get())
                self.datasets_carregados[nome] = df
                if nome in self.cache_processamento: del self.cache_processamento[nome]
            top.destroy()
            self.atualizar_visualizacao()
            messagebox.showinfo("Done", f"Conversion {direcao.get()} applied.")
        
        ttk.Button(top, text="Convert", command=confirmar).pack(pady=10)

    def acao_subtrair(self):
        nomes = list(self.datasets_carregados.keys())
        if len(nomes) < 2:
            messagebox.showwarning("Warning", "Load at least 2 samples.")
            return
        
        top = tk.Toplevel(self)
        top.title("Subtract Spectra")
        top.geometry("400x300")
        
        ttk.Label(top, text="Sample A (minuend):", font=('Arial', 10, 'bold')).pack(pady=5)
        combo_a = ttk.Combobox(top, values=nomes, state='readonly')
        combo_a.pack(fill=tk.X, padx=10)
        
        ttk.Label(top, text="– Sample B (subtrahend):", font=('Arial', 10, 'bold')).pack(pady=5)
        combo_b = ttk.Combobox(top, values=nomes, state='readonly')
        combo_b.pack(fill=tk.X, padx=10)
        
        def confirmar():
            a, b = combo_a.get(), combo_b.get()
            if not a or not b or a == b:
                messagebox.showwarning("Warning", "Select different samples.")
                return
            df_result = processamento.subtrair_espectros(
                self.datasets_carregados[a], self.datasets_carregados[b])
            if df_result is None:
                messagebox.showerror("Error", "Spectra have insufficient overlap.")
                return
            nome_novo = f"{a} - {b}"
            self.datasets_originais[nome_novo] = df_result.copy()
            self.datasets_carregados[nome_novo] = df_result.copy()
            self.historico_cortes[nome_novo] = []
            self.areas_calculadas[nome_novo] = []
            self.lista_datasets.insert(tk.END, nome_novo)
            self.dataset_cores[nome_novo] = next(self.cores_ciclo)
            self.dataset_estilos[nome_novo] = 'solid'
            self.dataset_espessuras[nome_novo] = 2
            top.destroy()
            messagebox.showinfo("Done", f"Difference spectrum '{nome_novo}' created.")
        
        ttk.Button(top, text="Subtract (A - B)", command=confirmar).pack(pady=15)

    def acao_razao_picos(self):
        idx = self.lista_datasets.curselection()
        if not idx:
            messagebox.showwarning("Warning", "Select a sample.")
            return
        
        centro1 = simpledialog.askfloat("Peak Ratio", "Peak 1 — Center (cm⁻¹):", minvalue=400, maxvalue=4000)
        if centro1 is None: return
        centro2 = simpledialog.askfloat("Peak Ratio", "Peak 2 — Center (cm⁻¹):", minvalue=400, maxvalue=4000)
        if centro2 is None: return
        largura = simpledialog.askfloat("Peak Ratio", "Search width (±cm⁻¹):", initialvalue=10, minvalue=1, maxvalue=100)
        if largura is None: largura = 10
        
        msg = "Peak Ratio Results:\n"
        for i in idx:
            nome = self.lista_datasets.get(i)
            df = self.datasets_carregados[nome]
            razao, i1, i2 = processamento.razao_picos(df, centro1, centro2, largura)
            if razao is not None:
                msg += f"\n{nome}:\n  Peak1({centro1:.0f}): {i1:.4f}\n  Peak2({centro2:.0f}): {i2:.4f}\n  Ratio: {razao:.4f}\n"
            else:
                msg += f"\n{nome}: Peaks not found.\n"
        
        messagebox.showinfo("Peak Ratio", msg)

    def acao_correcao_atr(self):
        idx = self.lista_datasets.curselection()
        if not idx:
            messagebox.showwarning("Warning", "Select samples.")
            return
        
        top = tk.Toplevel(self)
        top.title("ATR Correction")
        top.geometry("350x250")
        
        ttk.Label(top, text="ATR Crystal Parameters", font=('Arial', 11, 'bold')).pack(pady=10)
        
        fr = ttk.Frame(top)
        fr.pack(padx=20, pady=5)
        
        ttk.Label(fr, text="n crystal:").grid(row=0, column=0, sticky='w', pady=3)
        e_nc = ttk.Entry(fr, width=10); e_nc.insert(0, "2.4"); e_nc.grid(row=0, column=1, padx=5)
        
        ttk.Label(fr, text="n sample:").grid(row=1, column=0, sticky='w', pady=3)
        e_na = ttk.Entry(fr, width=10); e_na.insert(0, "1.5"); e_na.grid(row=1, column=1, padx=5)
        
        ttk.Label(fr, text="Angle (°):").grid(row=2, column=0, sticky='w', pady=3)
        e_ang = ttk.Entry(fr, width=10); e_ang.insert(0, "45"); e_ang.grid(row=2, column=1, padx=5)
        
        ttk.Label(top, text="Common crystals: Diamond=2.4, ZnSe=2.4, Ge=4.0", font=('Arial', 8), foreground='gray').pack()
        
        def confirmar():
            try:
                nc = float(e_nc.get()); na = float(e_na.get()); ang = float(e_ang.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid values."); return
            for i in idx:
                nome = self.lista_datasets.get(i)
                df = self.datasets_carregados[nome]
                df['absorbancia'] = processamento.correcao_atr(
                    df['wavenumber'].values, df['absorbancia'].values, nc, na, ang)
                if nome in self.cache_processamento: del self.cache_processamento[nome]
            top.destroy()
            self.atualizar_visualizacao()
            messagebox.showinfo("Done", "ATR Correction applied.")
        
        ttk.Button(top, text="Apply Correction", command=confirmar).pack(pady=15)

    def acao_deconvolucao(self):
        idx = self.lista_datasets.curselection()
        if not idx:
            messagebox.showwarning("Warning", "Select a sample.")
            return
        
        nome = self.lista_datasets.get(idx[0])
        df = self.datasets_carregados[nome].dropna().sort_values('wavenumber')
        
        top = tk.Toplevel(self)
        top.title(f"Deconvolution — {nome}")
        top.geometry("450x300")
        
        ttk.Label(top, text="Peak centers (cm⁻¹, comma-separated):", font=('Arial', 10, 'bold')).pack(pady=10)
        e_centros = ttk.Entry(top, width=40)
        e_centros.pack(padx=10)
        e_centros.insert(0, "1720, 1600, 1450")
        
        tipo_var = tk.StringVar(value='gaussian')
        fr_tipo = ttk.Frame(top)
        fr_tipo.pack(pady=10)
        ttk.Radiobutton(fr_tipo, text="Gaussian", variable=tipo_var, value='gaussian').pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(fr_tipo, text="Lorentzian", variable=tipo_var, value='lorentzian').pack(side=tk.LEFT, padx=10)
        
        def confirmar():
            try:
                centros = [float(c.strip()) for c in e_centros.get().split(',')]
            except ValueError:
                messagebox.showerror("Error", "Invalid format. Use: 1720, 1600, 1450")
                return
            
            x = df['wavenumber'].values
            y = df['absorbancia'].values
            
            y_fit, picos, func = processamento.deconvolucao_picos(x, y, centros, tipo_var.get())
            if y_fit is None:
                messagebox.showerror("Error", "Deconvolution failed. Try different peak centers.")
                return
            
            # Plota resultado em janela separada
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(x, y, 'k-', label='Original', linewidth=1.5)
            ax.plot(x, y_fit, 'r--', label='Fit Total', linewidth=1.5)
            
            cores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            for i, p in enumerate(picos):
                y_ind = func(x, p['amplitude'], p['centro'], p['largura'])
                cor = cores[i % len(cores)]
                ax.fill_between(x, 0, y_ind, alpha=0.3, color=cor,
                               label=f"Peak {p['centro']:.0f} cm⁻¹")
            
            ax.invert_xaxis()
            ax.legend()
            ax.set_title(f"Deconvolution — {nome}")
            ax.set_xlabel("Wavenumber (cm⁻¹)")
            ax.set_ylabel("Absorbance")
            ax.grid(True, linestyle=':', alpha=0.5)
            plt.tight_layout()
            plt.show()
            
            # Mostra resultados
            msg = "Fitted peaks:\n"
            for p in picos:
                msg += f"\n  Center: {p['centro']:.1f} cm⁻¹\n  Amplitude: {p['amplitude']:.4f}\n  Width: {p['largura']:.1f}\n"
            messagebox.showinfo("Deconvolution", msg)
            top.destroy()
        
        ttk.Button(top, text="Run Deconvolution", command=confirmar).pack(pady=15)

    def acao_pca(self):
        selecionados = [self.lista_datasets.get(i) for i in self.lista_datasets.curselection()]
        if len(selecionados) < 3:
            messagebox.showwarning("Warning", "Select at least 3 samples for PCA.")
            return
        
        scores, var_exp, x_comum = processamento.calcular_pca(self.datasets_carregados, selecionados)
        if scores is None:
            messagebox.showerror("Error", "PCA failed. Check data.")
            return
        
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Score plot
        cores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
        for i, nome in enumerate(selecionados):
            cor = cores[i % len(cores)]
            ax1.scatter(scores[i, 0], scores[i, 1] if scores.shape[1] > 1 else 0,
                       s=100, color=cor, zorder=5)
            ax1.annotate(nome, (scores[i, 0], scores[i, 1] if scores.shape[1] > 1 else 0),
                        fontsize=8, ha='center', va='bottom', xytext=(0, 8),
                        textcoords='offset points')
        
        ax1.set_xlabel(f"PC1 ({var_exp[0]:.1f}%)")
        ax1.set_ylabel(f"PC2 ({var_exp[1]:.1f}%)" if len(var_exp) > 1 else "PC2")
        ax1.set_title("Score Plot (PCA)")
        ax1.axhline(0, color='gray', linestyle='--', alpha=0.5)
        ax1.axvline(0, color='gray', linestyle='--', alpha=0.5)
        ax1.grid(True, linestyle=':', alpha=0.4)
        
        # Scree plot
        n_comp = min(len(var_exp), 10)
        ax2.bar(range(1, n_comp + 1), var_exp[:n_comp], color='steelblue')
        ax2.set_xlabel("Principal Component")
        ax2.set_ylabel("Explained Variance (%)")
        ax2.set_title("Scree Plot")
        ax2.set_xticks(range(1, n_comp + 1))
        
        plt.tight_layout()
        plt.show()

    def acao_relatorio_pdf(self):
        idx = self.lista_datasets.curselection()
        if not idx:
            messagebox.showwarning("Warning", "Select a sample.")
            return
        
        nome = self.lista_datasets.get(idx[0])
        caminho = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            title="Save Report", initialfile=f"Report_{nome}.pdf")
        if not caminho: return
        
        # Coleta dados de picos
        df = self.datasets_carregados[nome]
        y_proc = processamento.apply_savgol_filter(
            processamento.baseline_correction(df['absorbancia'].values))
        picos, _ = processamento.detect_peaks_and_valleys(y_proc)
        
        picos_data = []
        for p in picos:
            picos_data.append((df['wavenumber'].iloc[p], y_proc[p]))
        
        areas_data = []
        if nome in self.areas_calculadas:
            for (_, _, area_val) in self.areas_calculadas[nome]:
                areas_data.append(area_val)
        
        filtro_info = f"W={self.filtro_window.get()}, P={self.filtro_poly.get()}, D={self.filtro_derivada.get()}"
        
        try:
            processamento.gerar_relatorio_pdf(caminho, nome, self.figura, picos_data, areas_data, filtro_info)
            messagebox.showinfo("Done", f"Report saved to:\n{caminho}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF: {e}")

    def acao_notas_amostra(self):
        idx = self.lista_datasets.curselection()
        if not idx: return
        nome = self.lista_datasets.get(idx[0])
        
        top = tk.Toplevel(self)
        top.title(f"Notes — {nome}")
        top.geometry("400x300")
        
        ttk.Label(top, text=f"Notes for: {nome}", font=('Arial', 10, 'bold')).pack(pady=5)
        
        texto = tk.Text(top, wrap=tk.WORD, font=('Arial', 10))
        texto.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        texto.insert(tk.END, self.dataset_notas.get(nome, ""))
        
        def salvar():
            self.dataset_notas[nome] = texto.get("1.0", tk.END).strip()
            top.destroy()
            messagebox.showinfo("Saved", "Notes saved.")
        
        ttk.Button(top, text="Save Notes", command=salvar).pack(pady=10)

    # =======================================================
    # AJUDA E SOBRE
    # =======================================================

    def abrir_sobre(self):
        top = tk.Toplevel(self)
        top.title("About")
        top.geometry("450x350")
        top.resizable(False, False)
        
        ttk.Label(top, text="FTIR Analyzer Pro", font=('Arial', 16, 'bold')).pack(pady=(20, 5))
        ttk.Label(top, text="Version 3.3", font=('Arial', 11)).pack()
        ttk.Separator(top, orient='horizontal').pack(fill=tk.X, pady=15, padx=30)
        
        info = (
            "Software for infrared spectrum analysis\n"
            "by Fourier Transform (FTIR).\n\n"
            "Developed for the LaCom Laboratory\n"
            "Federal University of Rio de Janeiro (UFRJ)\n\n"
            "Author: Luiz Roberto Bastos de Oliveira\n\n"
            "Features: Loading, processing,\n"
            "identification and comparison of spectra."
        )
        ttk.Label(top, text=info, justify='center', font=('Arial', 10)).pack(padx=20)
        ttk.Button(top, text="Close", command=top.destroy).pack(pady=15)

    def abrir_guia_uso(self):
        top = tk.Toplevel(self)
        top.title("📖 User Guide — FTIR Analyzer Pro")
        top.geometry("700x600")
        
        # Texto scrollável
        frame_txt = ttk.Frame(top)
        frame_txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(frame_txt)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        texto = tk.Text(frame_txt, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                        font=('Arial', 10), padx=15, pady=15, spacing1=2)
        texto.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=texto.yview)
        
        # Tags de formatação
        texto.tag_configure('titulo', font=('Arial', 14, 'bold'), spacing1=10, spacing3=5)
        texto.tag_configure('subtitulo', font=('Arial', 11, 'bold'), spacing1=8, spacing3=3)
        texto.tag_configure('item', font=('Arial', 10), lmargin1=20, lmargin2=30)
        texto.tag_configure('dica', font=('Arial', 10, 'italic'), foreground='#555555')
        
        # Conteúdo do guia
        guia = [
            ("titulo", "🔬 Complete Guide — FTIR Analyzer Pro\n\n"),
            
            ("subtitulo", "1. LOADING SAMPLES\n"),
            ("item", "• Click '📂 Load Files' and select .txt, .csv or .dpt files\n"),
            ("item", "• Supports multiple files simultaneously\n"),
            ("item", "• Select samples in the list to display them on the chart\n"),
            ("dica", "  💡 Tip: Use Ctrl+click to select multiple samples\n\n"),
            
            ("subtitulo", "2. VISUALIZATION\n"),
            ("item", "• Original (Dashed): Shows raw data with a dashed line\n"),
            ("item", "• Processed (Solid): Shows data after Savitzky-Golay filter\n"),
            ("item", "• Show Values: Annotates detected peaks in cm⁻¹\n"),
            ("item", "• Normalize (0-1): Normalizes the intensity of each spectrum\n"),
            ("item", "• Waterfall Mode: Offsets spectra vertically for comparison\n"),
            ("dica", "  💡 Tip: The filter indicator shows current parameters (W, P, D)\n\n"),
            
            ("subtitulo", "3. RIGHT-CLICK (CONTEXT MENU)\n"),
            ("item", "• Right-click on a sample in the list to:\n"),
            ("item", "  🎨 Change the spectrum color\n"),
            ("item", "  📊 Change the style (solid line, dots, or both)\n"),
            ("item", "  📏 Adjust line width (thin, normal, thick)\n"),
            ("item", "  ❌ Remove the sample from the list\n\n"),
            
            ("subtitulo", "4. ENGINEERING TOOLS\n"),
            ("item", "• ⚙️ Filters: Adjust Savitzky-Golay filter parameters\n"),
            ("item", "    - Window: Smoothing window size\n"),
            ("item", "    - Polynomial: Polynomial order\n"),
            ("item", "    - Derivative: 0=Normal, 1=1st derivative, 2=2nd derivative\n"),
            ("item", "• ✂️ Crop: Removes a region from the spectrum (by wavenumber)\n"),
            ("item", "• 📐 Select Area (Mouse): Click 2 points on the chart\n"),
            ("item", "    to calculate area under the peak (trapezoidal integration)\n"),
            ("item", "• 🔍 What is this peak?: Click on a peak to identify\n"),
            ("item", "    the corresponding chemical bond\n"),
            ("item", "• 🔢 Area (Manual): Calculate area by entering the limits\n"),
            ("item", "• ↺ Reset: Undo all crops and edits\n"),
            ("item", "• ↩ Undo: Removes only the last crop\n"),
            ("item", "• 🗑️ Clear Annotations: Removes annotation balloons\n\n"),
            
            ("subtitulo", "5. IDENTIFICATION\n"),
            ("item", "• 🔍 Identify (Blind Search): Compares the sample with the entire\n"),
            ("item", "    library and shows matches by correlation\n"),
            ("item", "• 🆚 Compare with Standard: Choose a material from the library\n"),
            ("item", "    to generate a Butterfly Plot (mirrored visual comparison)\n\n"),
            
            ("subtitulo", "6. EXPORT\n"),
            ("item", "• 📊 Interactive Chart: Generates an HTML with a Plotly chart\n"),
            ("item", "• 💾 Save CSV: Exports peak positions and intensities\n"),
            ("item", "• 📸 Save Image: Saves the chart as PNG, SVG or PDF (300 DPI)\n\n"),
            
            ("subtitulo", "7. LIBRARY\n"),
            ("item", "• Use the '📚 Library' menu to manage reference spectra\n"),
            ("item", "• Import NIST spectra in .jdx format\n"),
            ("item", "• Add your own standards in .csv\n\n"),
            
            ("subtitulo", "8. CHART NAVIGATION\n"),
            ("item", "• 🖱️ Mouse wheel: Zoom in/out centered on cursor\n"),
            ("item", "• Matplotlib toolbar (below the chart):\n"),
            ("item", "    🏠 Home: Returns to the original view\n"),
            ("item", "    ◀▶ Arrows: Navigate through view history\n"),
            ("item", "    🔍 Magnifier: Select area to zoom\n"),
            ("item", "    ✋ Hand: Drag the chart\n"),
            ("item", "    💾 Disk: Save the image\n\n"),
            
            ("subtitulo", "9. ADVANCED ANALYSIS\n"),
            ("item", "• 🔄 Convert T↔A: Converts between Transmittance (%) and\n"),
            ("item", "    Absorbance. Ideal for instruments that export in %T\n"),
            ("item", "• ➖ Subtract Spectra: Subtracts one sample from another\n"),
            ("item", "    (e.g.: remove background, solvent, or matrix)\n"),
            ("item", "    Creates a new 'A - B' spectrum in the list\n"),
            ("item", "• 📊 Peak Ratio: Calculates the intensity ratio between\n"),
            ("item", "    two peaks (e.g.: Carbonyl Index C=O/CH₂)\n"),
            ("item", "    Enter the centers (cm⁻¹) and the search width\n"),
            ("item", "• 🔬 ATR Correction: Corrects the penetration depth\n"),
            ("item", "    to compare with transmission spectra\n"),
            ("item", "    Parameters: n crystal, n sample, angle\n"),
            ("dica", "  💡 Common crystals: Diamond=2.4, ZnSe=2.4, Ge=4.0\n"),
            ("item", "• 📈 Peak Deconvolution: Fits Gaussian or\n"),
            ("item", "    Lorentzian overlapping peaks for band resolution\n"),
            ("item", "    Enter centers separated by comma\n"),
            ("item", "• 📉 PCA (Multivariate): Principal Component Analysis\n"),
            ("item", "    Generates Score Plot and Scree Plot to compare samples\n"),
            ("item", "    Requires at least 3 selected samples\n"),
            ("item", "• 📄 PDF Report: Generates PDF with chart, peaks table,\n"),
            ("item", "    calculated areas and filter parameters\n"),
            ("item", "• Baseline: Choose between Polynomial, ALS (Asymmetric Least\n"),
            ("item", "    Squares) or Rubberband for baseline correction\n"),
            ("item", "• 📝 Notes: Right-click → Notes, to annotate experimental\n"),
            ("item", "    conditions (temperature, time, etc.) per sample\n"),
        ]
        
        for tag, conteudo in guia:
            texto.insert(tk.END, conteudo, tag)
        
        texto.config(state=tk.DISABLED)  # Impede edição
        ttk.Button(top, text="Close", command=top.destroy).pack(pady=10)

class JanelaPlotly(tk.Toplevel):
    def __init__(self, parent, datasets, cores):
        super().__init__(parent)
        self.title("Advanced Chart Settings")
        self.datasets = datasets
        self.cores_base = cores
        
        tk.Label(self, text="Select datasets to plot:").pack(pady=5, padx=10)
        
        self.listbox = tk.Listbox(self, selectmode=tk.MULTIPLE, height=5)
        for name in self.datasets.keys():
            self.listbox.insert(tk.END, name)
        self.listbox.pack(fill=tk.X, pady=5, padx=10)

        tk.Label(self, text="Chart Title:").pack(anchor='w', padx=10)
        self.entry_titulo = ttk.Entry(self)
        self.entry_titulo.insert(0, "Compared FTIR Spectra")
        self.entry_titulo.pack(fill=tk.X, padx=10)

        frame_picos = ttk.LabelFrame(self, text="Peak Detection Parameters")
        frame_picos.pack(fill=tk.X, pady=10, padx=10)
        tk.Label(frame_picos, text="Prominence:").grid(row=0, column=0, sticky='w')
        self.entry_prom = ttk.Entry(frame_picos, width=8); self.entry_prom.insert(0,"0.02"); self.entry_prom.grid(row=0, column=1, padx=5)
        tk.Label(frame_picos, text="Distance:").grid(row=0, column=2, sticky='w')
        self.entry_dist = ttk.Entry(frame_picos, width=8); self.entry_dist.insert(0,"10"); self.entry_dist.grid(row=0, column=3, padx=5)

        ttk.Button(self, text="Generate Plotly Chart", command=self.executar).pack(pady=10)

    def executar(self):
        selecionados = [self.listbox.get(i) for i in self.listbox.curselection()]
        if not selecionados: return
        
        cores_plotly = {nome: self.cores_base.get(nome, '#0000FF') for nome in selecionados}
        
        try:
            config = {'prominence': float(self.entry_prom.get()), 'distance': int(self.entry_dist.get())}
        except ValueError:
            messagebox.showerror("Error", "Prominence and Distance must be valid numbers.")
            return

        processamento.gerar_grafico_plotly(
            self.datasets, selecionados, config,
            self.entry_titulo.get(), cores_plotly,
            zoom_wavenumber=(None,None), zoom_absorbancia=(None,None), corte_eixo=None
        )
        self.destroy()

if __name__ == "__main__":
    app = AppFTIR()
    app.mainloop()
