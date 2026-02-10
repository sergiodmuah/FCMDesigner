import tkinter as tk
from tkinter import ttk, filedialog
from algorithms.run_fcm import NormalizationType, InferenceType
from .advanced_pso_dialog import AdvancedPSODialog


class TrainPSODialog:
    """Diálogo para configurar entrenamiento PSO (básico).

    Pide: CSV de entrenamiento. La columna objetivo será la última columna del CSV.
    El resto de parámetros se configuran en "Opciones avanzadas...".
    """
    def __init__(self, parent, concept_names: list[str]):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Entrenar (PSO)")
        self.dialog.geometry("480x320")
        self.dialog.minsize(420, 300)
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)

        main = ttk.Frame(self.dialog, padding="12")
        main.pack(fill=tk.BOTH, expand=True)

        csv_frame = ttk.Frame(main)
        csv_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(csv_frame, text="Archivo de entrenamiento (CSV/Excel):").pack(anchor=tk.W)
        self.path_entry = ttk.Entry(csv_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(csv_frame, text="...", width=3, command=self._pick_file).pack(side=tk.LEFT)

        # La columna objetivo se tomará como la última del CSV automáticamente

        # Nº de clases / Tipo de datos
        classes_row = ttk.Frame(main)
        classes_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(classes_row, text="Nº clases:").pack(anchor=tk.W)
        self.num_classes_var = tk.StringVar(value="2")
        classes_frame = ttk.Frame(classes_row)
        classes_frame.pack(anchor=tk.W)
        self.num_classes_spin = tk.Spinbox(classes_frame, from_=2, to=20, width=6, textvariable=self.num_classes_var)
        self.num_classes_spin.pack(side=tk.LEFT)
        self.continuous_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(classes_frame, text="Autoescalado", variable=self.continuous_var, command=self._on_continuous_change).pack(side=tk.LEFT, padx=(8, 0))

        # Normalización
        norm_row = ttk.Frame(main)
        norm_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(norm_row, text="Normalización:").pack(anchor=tk.W)
        self.norm_var = tk.StringVar(value="relu")
        norm_combo = ttk.Combobox(
            norm_row,
            state="readonly",
            values=["syc", "sy", "bistate", "tristate", "tanh", "sigmoid", "linear", "relu"],
            textvariable=self.norm_var,
            width=25,
        )
        norm_combo.pack(anchor=tk.W, pady=(4, 0))

        # Inferencia
        infer_row = ttk.Frame(main)
        infer_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(infer_row, text="Inferencia:").pack(anchor=tk.W)
        self.infer_var = tk.StringVar(value="kosko_rescaled")
        infer_combo = ttk.Combobox(
            infer_row,
            state="readonly",
            values=["kosko_standard", "kosko_memory", "kosko_rescaled"],
            textvariable=self.infer_var,
            width=25,
        )
        infer_combo.pack(anchor=tk.W, pady=(4, 0))

        # Parámetros avanzados se moverán al diálogo avanzado

        buttons = ttk.Frame(main)
        buttons.pack(anchor=tk.E, pady=(8, 0))
        self.advanced_params: dict[str, str] | None = None
        ttk.Button(buttons, text="Opciones avanzadas...", command=self._open_advanced).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons, text="Aceptar", command=self.accept).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(buttons, text="Cancelar", command=self.cancel).pack(side=tk.RIGHT)

        self.dialog.bind("<Escape>", lambda e: self.cancel())
        self.dialog.bind("<Return>", lambda e: self.accept())

    def _pick_file(self):
        path = filedialog.askopenfilename(
            parent=self.dialog,
            title="Seleccionar dataset",
            filetypes=[
                ("Datos (CSV/Excel)", ("*.csv", "*.xlsx", "*.xls")),
                ("Archivos CSV", "*.csv"),
                ("Archivos Excel", ("*.xlsx", "*.xls")),
                ("Todos los archivos", "*.*"),
            ],
        )
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
    
    def _on_continuous_change(self):
        """Deshabilita/habilita el spinbox de Nº clases según el checkbox Continuo"""
        if self.continuous_var.get():
            self.num_classes_spin.configure(state="disabled")
        else:
            self.num_classes_spin.configure(state="normal")

    def accept(self):
        dataset_path = self.path_entry.get().strip()
        if not dataset_path:
            return
        norm_map = {
            "syc": NormalizationType.SYC,
            "sy": NormalizationType.SY,
            "bistate": NormalizationType.BISTATE,
            "tristate": NormalizationType.TRISTATE,
            "tanh": NormalizationType.TANH,
            "sigmoid": NormalizationType.SIGMOID,
            "linear": NormalizationType.LINEAR,
            "relu": NormalizationType.RELU,
        }
        infer_map = {
            "kosko_standard": InferenceType.KOSKO_STANDARD,
            "kosko_memory": InferenceType.KOSKO_MEMORY,
            "kosko_rescaled": InferenceType.KOSKO_RESCALED,
        }
        # Determinar número de clases o continuo
        num_classes = None
        is_continuous = self.continuous_var.get()
        if not is_continuous:
            try:
                num_classes = int(self.num_classes_var.get() or 2)
                if num_classes < 2:
                    num_classes = 2
            except (ValueError, TypeError):
                num_classes = 2
        
        self.result = {
            "dataset_path": dataset_path,
            "num_classes": num_classes,  # None si es continuo, int si es binario/multiclase
            "is_continuous": is_continuous,
            "normalization": norm_map.get(self.norm_var.get(), NormalizationType.RELU),
            "inference": infer_map.get(self.infer_var.get(), InferenceType.KOSKO_RESCALED),
            "advanced": self.advanced_params or {},
        }
        self.dialog.destroy()

    def _open_advanced(self):
        # Pasar los parámetros previos si existen
        dlg = AdvancedPSODialog(self.dialog, previous_params=self.advanced_params)
        adv = dlg.show()
        if adv is not None:
            self.advanced_params = adv

    def cancel(self):
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result


