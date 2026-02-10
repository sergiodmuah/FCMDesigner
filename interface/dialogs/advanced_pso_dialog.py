import tkinter as tk
from tkinter import ttk, messagebox


class AdvancedPSODialog:
    """Diálogo de parámetros avanzados de PSO.

    Contiene: enjambre, iteraciones PSO, iteraciones simulador, w, c1, c2,
    límites de pesos y velocity clamp.
    """
    def __init__(self, parent, previous_params=None):
        """
        Args:
            parent: Ventana padre
            previous_params: Diccionario con parámetros previos (opcional).
                Claves: swarm_size, iterations, eval_iterations, w_value, c1_value, c2_value,
                weight_min, weight_max, velocity_clamp
        """
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Opciones avanzadas (PSO)")
        self.dialog.geometry("560x414")
        self.dialog.minsize(520, 368)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)

        main = ttk.Frame(self.dialog, padding="12")
        main.pack(fill=tk.BOTH, expand=True)

        # Valores por defecto o previos
        prev = previous_params or {}
        swarm_val = str(prev.get("swarm_size", 30))
        iters_val = str(prev.get("iterations", 10))
        eval_val = str(prev.get("eval_iterations", 20))
        w_val = str(prev.get("w_value", 0.7))
        c1_val = str(prev.get("c1_value", 1.5))
        c2_val = str(prev.get("c2_value", 1.5))
        min_val = str(prev.get("weight_min", -1.0))
        max_val = str(prev.get("weight_max", 1.0))
        vclamp_val = str(prev.get("velocity_clamp", 0.2))

        # Parámetros de PSO (arriba)
        pso = ttk.LabelFrame(main, text="Parámetros de PSO", padding="8")
        pso.pack(fill=tk.X)

        ttk.Label(pso, text="Enjambre").grid(row=0, column=0, sticky="w")
        ttk.Label(pso, text="Iteraciones").grid(row=0, column=1, sticky="w")
        ttk.Label(pso, text="Iter. simulador").grid(row=0, column=2, sticky="w")
        self.swarm_entry = ttk.Entry(pso, width=10)
        self.swarm_entry.insert(0, swarm_val)
        self.swarm_entry.grid(row=1, column=0, padx=(0, 8))
        self.iters_entry = ttk.Entry(pso, width=10)
        self.iters_entry.insert(0, iters_val)
        self.iters_entry.grid(row=1, column=1, padx=(0, 8))
        self.eval_entry = ttk.Entry(pso, width=12)
        self.eval_entry.insert(0, eval_val)
        self.eval_entry.grid(row=1, column=2)

        ttk.Label(pso, text="w (inercia)").grid(row=2, column=0, sticky="w", pady=(8,0))
        ttk.Label(pso, text="c1 (cognitivo)").grid(row=2, column=1, sticky="w", pady=(8,0))
        ttk.Label(pso, text="c2 (social)").grid(row=2, column=2, sticky="w", pady=(8,0))
        self.w_entry = ttk.Entry(pso, width=10)
        self.w_entry.insert(0, w_val)
        self.w_entry.grid(row=3, column=0, padx=(0, 8))
        self.c1_entry = ttk.Entry(pso, width=12)
        self.c1_entry.insert(0, c1_val)
        self.c1_entry.grid(row=3, column=1, padx=(0, 8))
        self.c2_entry = ttk.Entry(pso, width=12)
        self.c2_entry.insert(0, c2_val)
        self.c2_entry.grid(row=3, column=2)

        # Límites y clamp (abajo)
        grid = ttk.LabelFrame(main, text="Límites de peso y velocidad", padding="8")
        grid.pack(fill=tk.X, pady=8)

        ttk.Label(grid, text="Peso mínimo").grid(row=0, column=0, sticky="w")
        ttk.Label(grid, text="Peso máximo").grid(row=0, column=1, sticky="w")
        ttk.Label(grid, text="Velocity clamp").grid(row=0, column=2, sticky="w")

        self.min_entry = ttk.Entry(grid, width=10)
        self.min_entry.insert(0, min_val)
        self.min_entry.grid(row=1, column=0, padx=(0, 6))

        self.max_entry = ttk.Entry(grid, width=10)
        self.max_entry.insert(0, max_val)
        self.max_entry.grid(row=1, column=1, padx=(0, 6))

        self.vclamp_entry = ttk.Entry(grid, width=12)
        self.vclamp_entry.insert(0, vclamp_val)
        self.vclamp_entry.grid(row=1, column=2)

        # Fórmula (informativa)
        info = ttk.LabelFrame(main, text="Fórmula empleada (PSO)", padding="8")
        info.pack(fill=tk.X)
        formula_text = (
            "Actualización de velocidad y posición por iteración:\n"
            "v ← w·v + c1·r1·(pbest − x) + c2·r2·(gbest − x)\n"
            "x ← x + v\n\n"
            "Donde: w=inercia, c1=cognitivo, c2=social, r1 y r2 ∈ [0,1].\n"
            "Se aplica ‘velocity clamp’ a v y límites [peso mínimo, peso máximo] a x."
        )
        ttk.Label(
            info,
            text=formula_text,
            justify=tk.LEFT,
            foreground="#444",
            font=("Arial", 9),
            wraplength=440,
        ).pack(anchor=tk.W)

        actions = ttk.Frame(main)
        actions.pack(anchor=tk.E)
        ttk.Button(actions, text="Aceptar", command=self.accept).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(actions, text="Cancelar", command=self.cancel).pack(side=tk.RIGHT)

        self.dialog.bind("<Escape>", lambda e: self.cancel())

    def accept(self):
        try:
            self.result = {
                # PSO principales
                "swarm_size": int(self.swarm_entry.get().strip()),
                "iterations": int(self.iters_entry.get().strip()),
                "eval_iterations": int(self.eval_entry.get().strip()),
                "w_value": float(self.w_entry.get().strip()),
                "c1_value": float(self.c1_entry.get().strip()),
                "c2_value": float(self.c2_entry.get().strip()),
                # Límites
                "weight_min": float(self.min_entry.get().strip()),
                "weight_max": float(self.max_entry.get().strip()),
                "velocity_clamp": float(self.vclamp_entry.get().strip()),
            }
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Error", "Valores inválidos en opciones avanzadas")

    def cancel(self):
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result


