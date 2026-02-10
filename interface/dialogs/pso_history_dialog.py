import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class PSOHistoryDialog:
    """Diálogo para mostrar la evolución del mejor individuo (PSO).

    Pestañas:
    - Gráfico MSE (%).
    - Tabla de pesos por iteración.
    - Referencia de mapeo w_k a relaciones del mapa actual (opcional).
    """

    def __init__(self, parent, history, map_obj, apply_callback=None, save_history_callback=None):
        self.parent = parent
        self.history = history or []
        self.map_obj = map_obj
        self.save_history_callback = save_history_callback

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Evolución del mejor individuo (PSO)")
        self.dialog.geometry("900x600")
        self.dialog.minsize(780, 520)
        self.dialog.transient(parent)
        self.dialog.resizable(True, True)

        nb = ttk.Notebook(self.dialog)
        nb.pack(fill=tk.BOTH, expand=True)

        # Gráfico
        plot_tab = ttk.Frame(nb)
        nb.add(plot_tab, text="Gráfico MSE")
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            fig = Figure(figsize=(6.8, 3.8), dpi=100)
            ax = fig.add_subplot(111)
            xs = [item.get("iteration", 0) for item in self.history]
            ys_raw = [float(item.get("mse", 0.0)) for item in self.history]
            ys = [y * 100.0 for y in ys_raw]
            ax.plot(xs, ys, marker='o')
            ax.set_xlabel("Iteración")
            ax.set_ylabel("MSE (%)")
            ax.set_title("Mejor MSE por iteración (porcentaje)")
            ax.grid(True, alpha=0.3)
            canvas = FigureCanvasTkAgg(fig, master=plot_tab)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception:
            ttk.Label(plot_tab, text="Instala matplotlib para ver el gráfico (pip install matplotlib)").pack(padx=12, pady=12)

        # Tabla de pesos
        table_tab = ttk.Frame(nb)
        nb.add(table_tab, text="Tabla de pesos")
        max_w = 0
        for item in self.history:
            max_w = max(max_w, len(item.get("weights", [])))
        cols = ["Iteración", "MSE (%)"] + [f"w{i+1}" for i in range(max_w)]
        tree = ttk.Treeview(table_tab, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=90 if col in ("Iteración","MSE (%)") else 80, anchor=tk.CENTER)
        vsb = ttk.Scrollbar(table_tab, orient=tk.VERTICAL, command=tree.yview)
        hsb = ttk.Scrollbar(table_tab, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_tab.grid_rowconfigure(0, weight=1)
        table_tab.grid_columnconfigure(0, weight=1)

        for item in self.history:
            mse_pct = float(item.get('mse',0.0)) * 100.0
            row = [item.get("iteration", 0), f"{mse_pct:.2f}%"]
            ws = item.get("weights", [])
            row += [f"{float(w):.6f}".rstrip('0').rstrip('.') for w in ws]
            tree.insert('', 'end', values=row)

        # Referencia w_k → relaciones del mapa
        ref_tab = ttk.Frame(nb)
        nb.add(ref_tab, text="Referencia")
        wrapper = ttk.Frame(ref_tab)
        wrapper.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        rels = self.map_obj.get_relation_list()
        cols_map = ["w_k", "Origen", "Destino", "Peso entrenado"]
        map_tree = ttk.Treeview(wrapper, columns=cols_map, show="headings")
        for col in cols_map:
            map_tree.heading(col, text=col)
            map_tree.column(col, width=120 if col not in ("w_k",) else 60, anchor=tk.CENTER)
        vsb3 = ttk.Scrollbar(wrapper, orient=tk.VERTICAL, command=map_tree.yview)
        map_tree.configure(yscrollcommand=vsb3.set)
        map_tree.grid(row=0, column=0, sticky="nsew")
        vsb3.grid(row=0, column=1, sticky="ns")
        wrapper.grid_rowconfigure(0, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        best_weights = None
        if self.history and isinstance(self.history[-1], dict):
            best_weights = self.history[-1].get("weights")
        for idx, r in enumerate(rels, start=1):
            best_str = ""
            if best_weights is not None and idx-1 < len(best_weights):
                try:
                    best_str = f"{float(best_weights[idx-1]):.6f}".rstrip('0').rstrip('.')
                except Exception:
                    best_str = ""
            map_tree.insert('', 'end', values=[f"w{idx}", r.get_initial_concept().get_name(), r.get_final_concept().get_name(), best_str])

        # Acciones
        actions = ttk.Frame(self.dialog)
        actions.pack(fill=tk.X)
        if callable(self.save_history_callback):
            ttk.Button(actions, text="Guardar CSV", command=lambda: self.save_history_callback(self.history)).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(actions, text="Cerrar", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=6)

    def show(self):
        self.dialog.wait_window()


