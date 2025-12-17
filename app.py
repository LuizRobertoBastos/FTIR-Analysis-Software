import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from itertools import cycle
import processamento
# Painel Interativo Principal
class AppFTIR(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Analisador de Espectros FTIR (Versão Interativa)")
        self.geometry("1300x800")

        self.datasets_carregados = {}
        self.dataset_cores = {}  # NOVO: Para cores consistentes
        # Paleta de cores a ser usada para os gráficos
        self.cores_ciclo = cycle(["#3079ae", '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'])

        # --- Frames Principais ---
        frame_esquerda = ttk.Frame(self)
        frame_esquerda.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        frame_direita = ttk.Frame(self)
        frame_direita.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ==================================================================
        # PAINEL DE CONTROLE (ESQUERDA)
        # ==================================================================
        frame_arquivos = ttk.LabelFrame(frame_esquerda, text="1. Arquivos")
        frame_arquivos.pack(fill=tk.X, pady=5)
        ttk.Button(frame_arquivos, text="Carregar Arquivos", command=self.carregar_arquivos).pack(fill=tk.X, padx=5, pady=5)
        
        self.lista_datasets = tk.Listbox(frame_arquivos, selectmode=tk.MULTIPLE, height=10, exportselection=False)
        self.lista_datasets.pack(fill=tk.X, expand=True, padx=5, pady=5)
        # CORREÇÃO: Atualiza o gráfico ao mudar a seleção
        self.lista_datasets.bind('<<ListboxSelect>>', self.agendar_atualizacao)

        frame_visualizacao = ttk.LabelFrame(frame_esquerda, text="2. Opções de Visualização")
        frame_visualizacao.pack(fill=tk.X, pady=10)
        
        self.show_original = tk.BooleanVar(value=True)
        self.show_processado = tk.BooleanVar(value=True)
        self.show_picos = tk.BooleanVar(value=True)
        
        # CORREÇÃO: Checkboxes agora atualizam o gráfico automaticamente
        ttk.Checkbutton(frame_visualizacao, text="Mostrar Espectro Original", variable=self.show_original, command=self.atualizar_visualizacao).pack(anchor='w', padx=5)
        ttk.Checkbutton(frame_visualizacao, text="Mostrar Espectro Processado", variable=self.show_processado, command=self.atualizar_visualizacao).pack(anchor='w', padx=5)
        ttk.Checkbutton(frame_visualizacao, text="Mostrar Picos", variable=self.show_picos, command=self.atualizar_visualizacao).pack(anchor='w', padx=5)

        ttk.Button(frame_visualizacao, text="Atualizar Gráfico Manualmente", command=self.atualizar_visualizacao).pack(fill=tk.X, padx=5, pady=10)

        frame_acoes = ttk.LabelFrame(frame_esquerda, text="3. Ações")
        frame_acoes.pack(fill=tk.X, pady=5)
        ttk.Button(frame_acoes, text="Exportar Picos Selecionados", command=self.exportar_picos).pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(frame_acoes, text="Salvar Imagem do Gráfico", command=self.salvar_grafico).pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(frame_acoes, text="Gráfico Avançado (Plotly)", command=self.abrir_janela_plot_avancado).pack(fill=tk.X, padx=5, pady=5)

        # ==================================================================
        # ÁREA DE VISUALIZAÇÃO (DIREITA)
        # ==================================================================
        plot_frame = ttk.Frame(frame_direita)
        plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.figura = Figure(figsize=(8, 6))
        self.ax_plot = self.figura.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figura, master=plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        table_frame = ttk.Frame(frame_direita)
        table_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        self.tabela_picos = ttk.Treeview(table_frame, columns=('amostra', 'posicao', 'intensidade'), show='headings', height=6)
        self.tabela_picos.heading('amostra', text='Amostra')
        self.tabela_picos.heading('posicao', text='Posição (cm⁻¹)')
        self.tabela_picos.heading('intensidade', text='Intensidade')
        self.tabela_picos.column('amostra', width=150)
        self.tabela_picos.column('posicao', width=100, anchor='center')
        self.tabela_picos.column('intensidade', width=100, anchor='center')
        self.tabela_picos.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tabela_picos.yview)
        self.tabela_picos.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def agendar_atualizacao(self, event=None):
        # Pequeno atraso para garantir que a seleção da lista seja processada antes de desenhar
        self.after(50, self.atualizar_visualizacao)

# Carregar arquivos e processar dados inicialmente

    def carregar_arquivos(self):
        caminhos = filedialog.askopenfilenames(filetypes=[("Dados", "*.txt *.csv")])
        if not caminhos: return
        
        arquivos_carregados = 0
        for caminho in caminhos:
            nome_ds, df = processamento.processar_arquivo_unico(caminho)
            if df is not None:
                if nome_ds not in self.datasets_carregados:
                    self.datasets_carregados[nome_ds] = df
                    self.lista_datasets.insert(tk.END, nome_ds)
                    self.dataset_cores[nome_ds] = next(self.cores_ciclo)  # Associa cor permanente
                    arquivos_carregados += 1
        
        if arquivos_carregados > 0:
            messagebox.showinfo("Sucesso", f"{arquivos_carregados} novo(s) arquivo(s) carregado(s)!")
        else:
            messagebox.showwarning("Aviso", "Nenhum arquivo novo e válido foi carregado.")

# Gráfico de atualização com base nas seleções e opções

    def atualizar_visualizacao(self):
        indices_selecionados = self.lista_datasets.curselection()
        nomes_selecionados = [self.lista_datasets.get(i) for i in indices_selecionados]
        
        self.ax_plot.clear()
        self.tabela_picos.delete(*self.tabela_picos.get_children())
        
        if not nomes_selecionados:
            self.canvas.draw()
            return

        for nome in nomes_selecionados:
            df = self.datasets_carregados[nome]
            cor = self.dataset_cores.get(nome, 'black')  # Pega a cor associada
            
            y_processado = processamento.apply_savgol_filter(
                processamento.baseline_correction(df['absorbancia'].values)
            )
            picos, _ = processamento.detect_peaks_and_valleys(y_processado)

            if self.show_original.get():
                self.ax_plot.plot(df['wavenumber'], df['absorbancia'], label=f'Original: {nome}', color=cor, alpha=0.5, linestyle='--')
            
            if self.show_processado.get():
                self.ax_plot.plot(df['wavenumber'], y_processado, label=f'Processado: {nome}', color=cor)
            
            if self.show_picos.get():
                # MELHORIA: Picos em vermelho para melhor destaque
                self.ax_plot.plot(df['wavenumber'].iloc[picos], y_processado[picos], 'x', color='red', markersize=5)
            
            for i in picos:
                self.tabela_picos.insert('', tk.END, values=(nome, f"{df['wavenumber'].iloc[i]:.2f}", f"{y_processado[i]:.4f}"))

        self.ax_plot.set_xlabel("Número de onda (cm⁻¹)")
        self.ax_plot.set_ylabel("Absorbância")
        self.ax_plot.invert_xaxis()
        self.ax_plot.legend()
        self.ax_plot.grid(True, which='both', linestyle='--', linewidth=0.5)
        self.figura.tight_layout()
        self.canvas.draw()

    def salvar_grafico(self):
        if not self.ax_plot.has_data():
            messagebox.showwarning("Aviso", "Nenhum gráfico disponível para salvar.")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")])
        if filename:
            self.figura.savefig(filename, dpi=300)
            messagebox.showinfo("Sucesso", f"Gráfico salvo em {filename}")

# Exportar picos detectados para CSV para analisar bandas e intervalos

    def exportar_picos(self):
        indices_selecionados = self.lista_datasets.curselection()
        if not indices_selecionados:
            messagebox.showwarning("Aviso", "Selecione as amostras para exportar os picos.")
            return
        nomes_selecionados = [self.lista_datasets.get(i) for i in indices_selecionados]
        
        todos_os_picos = []
        for nome in nomes_selecionados:
            df = self.datasets_carregados[nome]
            y = processamento.apply_savgol_filter(processamento.baseline_correction(df['absorbancia'].values))
            picos, _ = processamento.detect_peaks_and_valleys(y)
            for i in picos:
                todos_os_picos.append((nome, df['wavenumber'].iloc[i], y[i]))
        
        if not todos_os_picos:
            messagebox.showinfo("Aviso", "Nenhum pico detectado nas amostras selecionadas.")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if filename:
            pd.DataFrame(todos_os_picos, columns=["Amostra", "Wavenumber", "Intensidade"]).to_csv(filename, index=False)
            messagebox.showinfo("Sucesso", f"Picos exportados para {filename}")

    def abrir_janela_plot_avancado(self):
        if not self.datasets_carregados:
            messagebox.showwarning("Aviso", "Carregue arquivos primeiro.")
            return
        janela_avancada = JanelaPlotly(self, self.datasets_carregados, self.dataset_cores)

# Janela para o Plotly Avançado(para manter o código organizado)

class JanelaPlotly(tk.Toplevel):
    def __init__(self, parent, datasets, cores):
        super().__init__(parent)
        self.title("Configurações Avançadas de Gráfico")
        self.datasets = datasets
        self.cores_base = cores
        self.caminho_logo = None  # Variável para armazenar o caminho da imagem
        
        tk.Label(self, text="Selecione os datasets para plotar:").pack(pady=5, padx=10)
        
        self.listbox = tk.Listbox(self, selectmode=tk.MULTIPLE, height=5)
        for name in self.datasets.keys():
            self.listbox.insert(tk.END, name)
        self.listbox.pack(fill=tk.X, pady=5, padx=10)

        tk.Label(self, text="Título do Gráfico:").pack(anchor='w', padx=10)
        self.entry_titulo = ttk.Entry(self)
        self.entry_titulo.insert(0, "Espectros FTIR Comparados")
        self.entry_titulo.pack(fill=tk.X, padx=10)

        # Área para Upload de Logo  ----
        frame_logo = ttk.LabelFrame(self, text="Logo / Marca D'água")
        frame_logo.pack(fill=tk.X, pady=5, padx=10)
        
        btn_carregar = ttk.Button(frame_logo, text="Escolher Imagem...", command=self.escolher_logo)
        btn_carregar.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.lbl_logo_status = tk.Label(frame_logo, text="Nenhuma imagem selecionada", fg="gray")
        self.lbl_logo_status.pack(side=tk.LEFT, padx=5)
        # --------------------------------------

        frame_picos = ttk.LabelFrame(self, text="Parâmetros de Detecção de Picos")
        frame_picos.pack(fill=tk.X, pady=10, padx=10)
        tk.Label(frame_picos, text="Prominência:").grid(row=0, column=0, sticky='w')
        self.entry_prom = ttk.Entry(frame_picos, width=8); self.entry_prom.insert(0,"0.02"); self.entry_prom.grid(row=0, column=1, padx=5)
        tk.Label(frame_picos, text="Distância:").grid(row=0, column=2, sticky='w')
        self.entry_dist = ttk.Entry(frame_picos, width=8); self.entry_dist.insert(0,"10"); self.entry_dist.grid(row=0, column=3, padx=5)

        ttk.Button(self, text="Gerar Gráfico Plotly", command=self.executar).pack(pady=10)
# Salvar e armaznar logos -----
    def escolher_logo(self):
        caminho = filedialog.askopenfilename(filetypes=[("Imagens", "*.png *.jpg *.jpeg *.svg")])
        if caminho:
            self.caminho_logo = caminho
            self.lbl_logo_status.config(text=f"Logo: ...{caminho[-20:]}", fg="green")

# ---------

    def executar(self):
        selecionados = [self.listbox.get(i) for i in self.listbox.curselection()]
        if not selecionados: return
        
        cores_plotly = {nome: self.cores_base.get(nome, '#0000FF') for nome in selecionados}
        
        try:
            config = {'prominence': float(self.entry_prom.get()), 'distance': int(self.entry_dist.get())}
        except ValueError:
            messagebox.showerror("Erro", "Prominência e Distância devem ser números válidos.")
            return
        
        processamento.gerar_grafico_plotly(
            self.datasets, selecionados, config,
            self.entry_titulo.get(), cores_plotly,
            zoom_wavenumber=(None,None), zoom_absorbancia=(None,None), corte_eixo=None,
            logo_path=self.caminho_logo  # <--- Passando a logo para o backend
        )
        self.destroy()
        
if __name__ == "__main__":
    app = AppFTIR()
    app.mainloop()