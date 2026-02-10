import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ResultsDialog:
    """Diálogo con pestañas para mostrar resultados de convergencia.

    - Gráfico de evolución por iteraciones (si matplotlib está disponible)
    - Tabla con los valores por iteración
    - Acciones para guardar imagen y exportar CSV/Excel
    """

    def __init__(self, parent, map_obj):
        self.parent = parent
        self.map_obj = map_obj
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Resultados de inferencia")
        self.dialog.geometry("900x600")
        self.dialog.minsize(780, 520)
        self.dialog.transient(parent)
        self.dialog.resizable(True, True)

        container = ttk.Frame(self.dialog)
        container.pack(fill=tk.BOTH, expand=True)
        nb = ttk.Notebook(container)
        nb.pack(fill=tk.BOTH, expand=True)

        # Pestaña de gráfico con leyenda seleccionable
        plot_tab = ttk.Frame(nb)
        nb.add(plot_tab, text="Gráfico")
        
        self.concepts = self.map_obj.get_concept_list()
        self.max_iters = self.map_obj.size_concepts_data()
        self.concept_vars = {}  # nombre -> BooleanVar
        
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            # Frame principal horizontal
            plot_main = ttk.Frame(plot_tab)
            plot_main.pack(fill=tk.BOTH, expand=True)
            
            # Panel de checkboxes (izquierda)
            legend_frame = ttk.LabelFrame(plot_main, text="Conceptos")
            legend_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0), pady=6)
            
            # Scrollable si hay muchos conceptos
            legend_canvas = tk.Canvas(legend_frame, width=150)
            legend_scrollbar = ttk.Scrollbar(legend_frame, orient=tk.VERTICAL, command=legend_canvas.yview)
            legend_inner = ttk.Frame(legend_canvas)
            
            legend_inner.bind("<Configure>", lambda e: legend_canvas.configure(scrollregion=legend_canvas.bbox("all")))
            legend_canvas.create_window((0, 0), window=legend_inner, anchor="nw")
            legend_canvas.configure(yscrollcommand=legend_scrollbar.set)
            
            legend_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            legend_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Botones seleccionar todo / ninguno
            btn_frame = ttk.Frame(legend_inner)
            btn_frame.pack(fill=tk.X, pady=(0, 4))
            ttk.Button(btn_frame, text="Todos", width=6, command=self._select_all).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Ninguno", width=6, command=self._select_none).pack(side=tk.LEFT, padx=2)
            
            for c in self.concepts:
                var = tk.BooleanVar(value=True)
                self.concept_vars[c.get_name()] = var
                cb = ttk.Checkbutton(legend_inner, text=c.get_name(), variable=var, command=self._update_plot)
                cb.pack(anchor=tk.W, padx=4)
            
            # Gráfico (derecha)
            self.fig = Figure(figsize=(6.5, 4.5), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=plot_main)
            self.canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
            
            self._update_plot()
            
        except Exception:
            ttk.Label(plot_tab, text="Para ver el gráfico, instala matplotlib (pip install matplotlib)").pack(padx=12, pady=12)

        # Pestaña de tabla
        table_tab = ttk.Frame(nb)
        nb.add(table_tab, text="Tabla")
        cols = ["Iteración"] + [c.get_name() for c in self.map_obj.get_concept_list()]
        tree = ttk.Treeview(table_tab, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120 if col != "Iteración" else 90, anchor=tk.CENTER)
        vsb = ttk.Scrollbar(table_tab, orient=tk.VERTICAL, command=tree.yview)
        hsb = ttk.Scrollbar(table_tab, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_tab.grid_rowconfigure(0, weight=1)
        table_tab.grid_columnconfigure(0, weight=1)

        max_iters = self.map_obj.size_concepts_data()
        concepts = self.map_obj.get_concept_list()
        for it in range(max_iters):
            row_vals = []
            for c in concepts:
                v = c.get_value(it)
                if isinstance(v, float):
                    s = f"{round(v, 6):.6f}".rstrip('0').rstrip('.')
                    row_vals.append(s if s != "" else "0")
                else:
                    row_vals.append(str(v))
            tree.insert('', 'end', values=[it] + row_vals)

        actions = ttk.Frame(self.dialog)
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Guardar imagen del gráfico", command=self._plot_and_save).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(actions, text="Guardar tabla (CSV)", command=self._save_csv).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Guardar tabla (Excel)", command=self._save_xlsx).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Cerrar", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=6)

    def _select_all(self):
        """Selecciona todos los conceptos"""
        for var in self.concept_vars.values():
            var.set(True)
        self._update_plot()

    def _select_none(self):
        """Deselecciona todos los conceptos"""
        for var in self.concept_vars.values():
            var.set(False)
        self._update_plot()

    def _update_plot(self):
        """Actualiza el gráfico según los conceptos seleccionados"""
        if not hasattr(self, 'ax'):
            return
        self.ax.clear()
        xs = list(range(self.max_iters))
        for c in self.concepts:
            if self.concept_vars.get(c.get_name(), tk.BooleanVar(value=False)).get():
                ys = [c.get_value(i) for i in xs]
                self.ax.plot(xs, ys, label=c.get_name())
        self.ax.set_xlabel("Iteración")
        self.ax.set_ylabel("Valor")
        self.ax.set_title("Convergencia de conceptos")
        self.ax.grid(True, alpha=0.3)
        if any(v.get() for v in self.concept_vars.values()):
            self.ax.legend(fontsize=8, loc='best')
        self.canvas.draw()

    def _plot_and_save(self):
        try:
            import matplotlib.pyplot as plt
        except Exception:
            messagebox.showerror(
                "Dependencia faltante",
                "Necesitas instalar matplotlib para ver el gráfico.\nPrueba: pip install matplotlib"
            )
            return
        concepts = self.map_obj.get_concept_list()
        max_iters = self.map_obj.size_concepts_data()
        xs = list(range(max_iters))
        plt.figure(figsize=(7, 4))
        for c in concepts:
            ys = [c.get_value(i) for i in xs]
            plt.plot(xs, ys, label=c.get_name())
        plt.xlabel("Iteración")
        plt.ylabel("Valor")
        plt.title("Convergencia de conceptos")
        plt.grid(True, alpha=0.3)
        plt.legend(loc="best", fontsize=8)
        filename = filedialog.asksaveasfilename(
            parent=self.dialog,
            title="Guardar gráfico",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPG", "*.jpg"), ("SVG", "*.svg")],
            initialfile="convergencia.png",
        )
        if filename:
            plt.savefig(filename, bbox_inches='tight', dpi=150)
            messagebox.showinfo("Gráfico", f"Imagen guardada en\n{filename}")
        plt.close()

    def _save_xlsx(self):
        try:
            import pandas as pd
        except ImportError:
            messagebox.showerror("Dependencia faltante", "Necesitas instalar pandas y openpyxl:\npip install pandas openpyxl")
            return
        filename = filedialog.asksaveasfilename(
            parent=self.dialog,
            title="Guardar convergencia (Excel)",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="convergencia.xlsx",
        )
        if not filename:
            return
        try:
            concepts = self.map_obj.get_concept_list()
            max_iters = self.map_obj.size_concepts_data()
            data = []
            for it in range(max_iters):
                row = {"Iteración": it}
                for c in concepts:
                    row[c.get_name()] = c.get_value(it)
                data.append(row)
            df = pd.DataFrame(data)
            df.to_excel(filename, sheet_name="Convergencia", index=False)
            messagebox.showinfo("Convergencia", f"Tabla exportada a\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def _save_csv(self):
        filename = filedialog.asksaveasfilename(
            parent=self.dialog,
            title="Guardar convergencia (CSV)",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="convergencia.csv",
        )
        if not filename:
            return
        try:
            concepts = self.map_obj.get_concept_list()
            max_iters = self.map_obj.size_concepts_data()
            import csv
            with open(filename, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Iteración"] + [c.get_name() for c in concepts])
                for it in range(max_iters):
                    row = [it] + [c.get_value(it) for c in concepts]
                    w.writerow(row)
            messagebox.showinfo("Convergencia", f"Tabla exportada a\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def show(self):
        self.dialog.wait_window()


