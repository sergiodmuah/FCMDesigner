import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List, Tuple

from trainer.dataset import FCMDataset
from trainer.simulator import FCMSimulator
from algorithms.run_fcm import NormalizationType, InferenceType


class EvaluationDialog:
    """Diálogo para evaluar el mapa con un CSV de validación.

    Funcionalidad:
    - Métricas de clasificación binaria y multiclase
    - MSE básico
    - La simulación se realiza sin UI, reutilizando la topología y pesos del mapa
      actual y el número de iteraciones configurado.
    """

    def __init__(self, parent, map_obj, normalization: NormalizationType, inference: InferenceType, iterations: int):
        self.parent = parent
        self.map_obj = map_obj
        self.normalization = normalization
        self.inference = inference
        self.iterations = max(1, iterations)

        # Ventana de diálogo (modal con respecto a la ventana padre)
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Evaluar mapa")
        self.dialog.transient(parent)
        self.dialog.minsize(600, 500)
        self.dialog.resizable(True, True)

        self._build_ui()
        self.dialog.bind("<Return>", lambda e: self.on_evaluate())
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

    def _build_ui(self) -> None:
        frm = ttk.Frame(self.dialog, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # Selector de archivo (ruta del dataset de evaluación)
        csv_row = ttk.Frame(frm)
        csv_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(csv_row, text="Dataset:").pack(side=tk.LEFT)
        self.csv_var = tk.StringVar()
        ttk.Entry(csv_row, textvariable=self.csv_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
        ttk.Button(csv_row, text="...", width=3, command=self._browse_file).pack(side=tk.RIGHT)

        # Número de clases (auto-cálculo de cortes)
        cls_row = ttk.Frame(frm)
        cls_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(cls_row, text="Nº clases:").pack(side=tk.LEFT)
        self.mc_classes_var = tk.IntVar(value=2)
        self.mc_classes_spin = tk.Spinbox(cls_row, from_=2, to=20, width=5, textvariable=self.mc_classes_var)
        self.mc_classes_spin.pack(side=tk.LEFT, padx=(6, 0))
        self.mc_classes_var.trace_add("write", lambda *args: self._on_mc_classes_change())

        # Umbrales multi-clase (K clases => K-1 cortes en [0,1])
        mc_row = ttk.Frame(frm)
        mc_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(mc_row, text="Cortes (binario/multiclase):").pack(side=tk.LEFT)
        self.mc_thr_var = tk.StringVar(value="0.5")
        ttk.Entry(mc_row, textvariable=self.mc_thr_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        ttk.Label(mc_row, text="ej.: 0.5 | 0.33, 0.66").pack(side=tk.LEFT, padx=(6, 0))

        # Checkbox para normalizar datos (min-max)
        normalize_row = ttk.Frame(frm)
        normalize_row.pack(fill=tk.X, pady=(0, 10))
        self.normalize_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            normalize_row, 
            text="Normalizar datos (min-max en todas las columnas)", 
            variable=self.normalize_var
        ).pack(anchor=tk.W)

        # Botones principales (Calcular y Cerrar)
        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X, pady=(0, 10))
        self.eval_btn = ttk.Button(btn_row, text="Calcular", command=self.on_evaluate)
        self.eval_btn.pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Cerrar", command=self.dialog.destroy).pack(side=tk.RIGHT)

        ttk.Separator(frm).pack(fill=tk.X, pady=8)

        # Zona de resultados
        results_frame = ttk.Frame(frm)
        results_frame.pack(fill=tk.BOTH, expand=True)

        self.mse_var = tk.StringVar(value="MSE: -")
        self.cls_metrics_var = tk.StringVar(value="Clasificación: -")
        self.cm_var = tk.StringVar(value="Matriz de confusión: -")

        ttk.Label(results_frame, textvariable=self.mse_var).pack(anchor=tk.W)
        ttk.Label(results_frame, textvariable=self.cls_metrics_var).pack(anchor=tk.W, pady=(6, 0))
        ttk.Label(results_frame, textvariable=self.cm_var).pack(anchor=tk.W, pady=(6, 0))

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.dialog, 
            title="Seleccionar Dataset", 
            filetypes=[
                ("CSV", "*.csv"), 
                ("Excel", "*.xlsx;*.xls"), 
                ("Todos", "*.*")
            ]
        )
        if path:
            self.csv_var.set(path)

    def on_evaluate(self) -> None:
        """Valida entradas y lanza la evaluación en un hilo de fondo."""
        file_path = self.csv_var.get().strip()
        if not file_path:
            messagebox.showwarning("Falta archivo", "Seleccione un archivo de evaluación (CSV o Excel).", parent=self.dialog)
            return

        self.eval_btn.configure(state="disabled")
        threading.Thread(target=self._run_eval_thread, args=(file_path,), daemon=True).start()

    def _parse_multiclass_thresholds(self, text: str) -> List[float]:
        """Convierte "a,b,c" en lista ordenada de floats dentro de (0,1), sin duplicados."""
        cuts: List[float] = []
        for part in text.split(','):
            s = part.strip().replace(' ', '')
            if not s:
                continue
            try:
                # Soporta fracciones tipo 1/3
                if '/' in s:
                    num, den = s.split('/', 1)
                    v = float(num) / float(den)
                else:
                    v = float(s)
            except Exception:
                continue
            if 0.0 < v < 1.0:
                cuts.append(v)
        # Ordenar y eliminar duplicados cercanos
        cuts = sorted(set(round(v, 6) for v in cuts))
        return cuts

    def _on_mc_classes_change(self) -> None:
        """Si el usuario indica N clases, autocalcular cortes en los puntos medios."""
        try:
            n = int(self.mc_classes_var.get())
        except Exception:
            return
        if n <= 1:
            return
        if n == 2:
            self.mc_thr_var.set("0.5")
            return
        # Para N clases, hay N-1 cortes que dividen [0,1] en N rangos iguales
        denom = float(n)
        cuts = [i / denom for i in range(1, n)]
        cuts_str = ", ".join(f"{c:.6f}".rstrip('0').rstrip('.') for c in cuts)
        self.mc_thr_var.set(cuts_str)

    def _run_eval_thread(self, file_path: str) -> None:
        """Carga el dataset y calcula métricas de clasificación y MSE."""
        try:
            # Detectar tipo de archivo y cargar dataset
            from pathlib import Path
            suffix = Path(file_path).suffix.lower()
            
            # Determinar nombre de la columna objetivo (última columna)
            if suffix in {".xlsx", ".xls"}:
                try:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    headers = list(df.columns)
                    if not headers:
                        raise ValueError("Archivo sin columnas")
                    target = headers[-1]
                    # Cargar dataset desde Excel
                    dataset = FCMDataset.from_excel(file_path, None)
                except ImportError:
                    raise ImportError("Necesitas instalar pandas y openpyxl para leer archivos Excel:\n pip install pandas openpyxl")
            else:
                # CSV
                import csv as _csv
                with open(file_path, "r", encoding="utf-8") as _f:
                    _reader = _csv.DictReader(_f)
                    headers = list(_reader.fieldnames or [])
                    if not headers:
                        raise ValueError("CSV sin cabecera")
                    target = headers[-1]
                # Cargar dataset desde CSV
                dataset = FCMDataset.from_csv(file_path, None)

            # Verificar si se debe normalizar (igual que en entrenamiento con autoescalado)
            should_normalize = self.normalize_var.get()
            normalization_stats = None
            if should_normalize:
                # Calcular estadísticos min/max para todas las columnas (features + target)
                # Igual que en train_with_pso cuando is_continuous=True
                normalization_stats = {}
                all_values = {col: [] for col in headers}
                
                # Recopilar todos los valores por columna
                for sample in dataset:
                    for col in headers:
                        if col == target:
                            all_values[col].append(float(sample.target_value))
                        else:
                            all_values[col].append(float(sample.features.get(col, 0.0)))
                
                # Calcular min/max por columna
                for col in headers:
                    if all_values[col]:
                        col_min = min(all_values[col])
                        col_max = max(all_values[col])
                        normalization_stats[col] = (col_min, col_max)

            # Preparar simulador con el mapa actual, normalización e inferencia indicadas
            simulator = FCMSimulator(self.map_obj, normalization=self.normalization, inference=self.inference)

            # Orden consistente de nombres de conceptos (columnas esperadas)
            concept_names = [c.get_name() for c in self.map_obj.get_concept_list()]

            # Acumuladores para MSE
            total = 0
            sq_error_sum = 0.0

            # Acumuladores para clasificación
            mc_cuts = self._parse_multiclass_thresholds(self.mc_thr_var.get())
            n_classes = 0
            try:
                n_classes = max(2, int(self.mc_classes_var.get()))
            except Exception:
                n_classes = 2
            if len(mc_cuts) == 0 and n_classes >= 2:
                if n_classes == 2:
                    mc_cuts = [0.5]
                else:
                    denom = float(n_classes - 1)
                    mc_cuts = [(i + 0.5) / denom for i in range(n_classes - 1)]
            mc_classes = len(mc_cuts) + 1 if len(mc_cuts) > 0 else 2
            mc_matrix: List[List[int]] = [[0 for _ in range(max(0, mc_classes))] for _ in range(max(0, mc_classes))]
            mc_counted = 0

            for sample in dataset:
                # Construye el vector de entrada, rellenando faltantes con 0.0
                features_row = {}
                for name in concept_names:
                    val = sample.features.get(name, 0.0)
                    # Aplicar normalización min-max si está activada (igual que en entrenamiento)
                    if should_normalize and normalization_stats and name in normalization_stats:
                        col_min, col_max = normalization_stats[name]
                        if col_max > col_min:
                            val = (val - col_min) / (col_max - col_min)
                            val = max(0.0, min(1.0, val))
                    features_row[name] = val
                
                pred = simulator.run_once(features_row, target, iterations=self.iterations)
                y = float(sample.target_value)
                # Normalizar target también si está activada la normalización
                if should_normalize and normalization_stats and target in normalization_stats:
                    col_min, col_max = normalization_stats[target]
                    if col_max > col_min:
                        y = (y - col_min) / (col_max - col_min)
                        y = max(0.0, min(1.0, y))
                
                # Métricas de MSE
                err = (pred - y)
                sq = err * err
                sq_error_sum += sq
                total += 1

                # Clasificación general (binaria/multiclase) con cortes definidos
                if mc_classes > 0:
                    # Discretiza pred a clase 0..mc_classes-1 usando cortes ordenados
                    c_pred = 0
                    for cut in mc_cuts:
                        if pred > cut:
                            c_pred += 1
                        else:
                            break
                    # Discretizar y (target) usando los mismos cortes que pred
                    # Esto es necesario especialmente cuando los datos están normalizados
                    c_true = 0
                    for cut in mc_cuts:
                        if y > cut:
                            c_true += 1
                        else:
                            break
                    # Validar que ambas clases estén en rango válido
                    if 0 <= c_true < mc_classes and 0 <= c_pred < mc_classes:
                        mc_matrix[c_true][c_pred] += 1
                        mc_counted += 1

            # Calcular MSE
            mse = (sq_error_sum / max(1, total)) if total > 0 else float("nan")

            # Calcular métricas de clasificación
            accuracy = precision = recall = f1 = None
            if mc_counted > 0 and mc_classes == 2:
                tp = mc_matrix[1][1] if len(mc_matrix) > 1 else 0
                fp = mc_matrix[0][1] if len(mc_matrix) > 0 else 0
                tn = mc_matrix[0][0] if len(mc_matrix) > 0 else 0
                fn = mc_matrix[1][0] if len(mc_matrix) > 1 else 0
                denom = max(1, tp + tn + fp + fn)
                accuracy = (tp + tn) / denom
                precision = tp / max(1, tp + fp)
                recall = tp / max(1, tp + fn)
                if precision + recall > 0:
                    f1 = 2 * precision * recall / (precision + recall)

            # Exactitud multi-clase general si corresponde (diagonal / total)
            mc_accuracy = None
            mc_precision = mc_recall = mc_f1 = None
            if mc_counted > 0:
                diag = 0
                for i in range(len(mc_matrix)):
                    diag += mc_matrix[i][i]
                mc_accuracy = diag / mc_counted
                # Precision, Recall y F1 macro para multiclase (promedio por clase)
                if mc_classes >= 3:
                    k = len(mc_matrix)
                    precs, recs, f1s = [], [], []
                    for i in range(k):
                        tp_i = mc_matrix[i][i]
                        fp_i = sum(mc_matrix[j][i] for j in range(k) if j != i)
                        fn_i = sum(mc_matrix[i][j] for j in range(k) if j != i)
                        p_i = tp_i / max(1, tp_i + fp_i)
                        r_i = tp_i / max(1, tp_i + fn_i)
                        precs.append(p_i)
                        recs.append(r_i)
                        f1s.append(2 * p_i * r_i / max(1e-9, p_i + r_i))
                    mc_precision = sum(precs) / k
                    mc_recall = sum(recs) / k
                    mc_f1 = sum(f1s) / k

            # Actualiza la UI con los resultados (en el hilo principal)
            def update():
                self.eval_btn.configure(state="normal")
                
                # Actualizar MSE (indicar si se usó normalización)
                mse_msg = f"MSE: {mse:.6f} (n={total})"
                if should_normalize:
                    mse_msg += " [datos normalizados]"
                self.mse_var.set(mse_msg)
                
                # Actualizar clasificación
                if mc_accuracy is not None and mc_classes >= 3:
                    k = len(mc_matrix)
                    prec_str = f", Prec={mc_precision:.3f}" if mc_precision is not None else ""
                    rec_str = f", Rec={mc_recall:.3f}" if mc_recall is not None else ""
                    f1_str = f", F1={mc_f1:.3f}" if mc_f1 is not None else ""
                    self.cls_metrics_var.set(
                        f"Multi-clase: clases={k}, Acc={mc_accuracy:.3f}{prec_str}{rec_str}{f1_str} (cortes {mc_cuts})"
                    )
                    rows = ["[" + ", ".join(str(mc_matrix[i][j]) for j in range(k)) + "]" for i in range(k)]
                    self.cm_var.set("Matriz (verdad x pred): [" + ", ".join(rows) + "]")
                elif accuracy is not None and mc_classes == 2:
                    f1_str = "-" if f1 is None else f"{f1:.3f}"
                    self.cls_metrics_var.set(
                        f"Binario (corte {mc_cuts[0]:.2f}): Acc={accuracy:.3f}, Prec={precision:.3f}, Rec={recall:.3f}, F1={f1_str}"
                    )
                    self.cm_var.set(f"Matriz 2x2: TP={tp} FP={fp} TN={tn} FN={fn}")
                else:
                    self.cls_metrics_var.set("Clasificación: sin datos válidos")
                    self.cm_var.set("Matriz de confusión: -")

            self.dialog.after(0, update)
        except Exception as e:
            # Muestra error y restablece controles
            def show_err(err=e):
                self.eval_btn.configure(state="normal")
                messagebox.showerror("Error al evaluar", str(err), parent=self.dialog)
            self.dialog.after(0, show_err)
