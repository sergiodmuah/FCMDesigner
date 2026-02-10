# interface/map_window.py COMPLETO
"""
Ventana principal de la aplicación
Migrado desde MapWindow.java
"""

import tkinter as tk
import os
from tkinter import ttk, messagebox, filedialog
from typing import Optional
from pathlib import Path

from map_model.map import Map
from algorithms.run_fcm import RunFCM, NormalizationType, InferenceType
from .map_canvas import MapCanvas, MouseMode
from .dialogs.train_pso_dialog import TrainPSODialog
from .dialogs.advanced_pso_dialog import AdvancedPSODialog
from .dialogs.delay_dialog import DelayDialog
from .dialogs.iteration_dialog import IterationDialog
from .dialogs.results_dialog import ResultsDialog
from .dialogs.pso_history_dialog import PSOHistoryDialog
from .dialogs.evaluation_dialog import EvaluationDialog


class MapWindow:
    """Ventana principal para edición y simulación de mapas"""
    
    def __init__(self, dynamic: bool = False):
        self.root = tk.Toplevel()
        self.map_obj = Map(dynamic)
        self.fcm_runner: Optional[RunFCM] = None
        
        self.setup_window()
        self.setup_interface()
        
    def setup_window(self):
        """Configuración inicial de la ventana"""
        map_type = "DFCM" if self.map_obj.is_dynamic() else "FCM"
        self.root.title(f"{map_type} Designer - Sin título")
        self.root.geometry("1000x750")
        self.root.minsize(800, 650)
        
        # Configurar cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        
    def setup_interface(self):
        """Configura la interfaz completa"""
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel de controles (izquierda)
        self.setup_control_panel(main_frame)
        
        # Canvas con scroll (centro)
        self.setup_canvas_area(main_frame)
        
        # Barra de menú
        self.setup_menu()
        
        # Barra de estado
        self.setup_status_bar()
        # Estado PSO: historial
        self._last_pso_history = None
        self._trained_normalization = None  # Normalización usada en el último entrenamiento
        self._trained_inference = None  # Inferencia usada en el último entrenamiento
    
    def setup_control_panel(self, parent):
        """Configura el panel de controles"""
        control_frame = ttk.Frame(parent, width=220)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        control_frame.pack_propagate(False)
        # Guardar referencia para insertar widgets adicionales (progreso de entrenamiento)
        self.left_panel = control_frame
        
        # Posición del ratón
        self.mouse_pos_label = ttk.Label(control_frame, text="X: 0, Y: 0", font=("Arial", 9))
        self.mouse_pos_label.pack(pady=5)
        
        # Modos del ratón
        mode_frame = ttk.LabelFrame(control_frame, text="Acciones del Ratón", padding="5")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.mouse_mode_var = tk.StringVar(value="create_concepts")
        
        modes = [
            ("Crear Conceptos", "create_concepts", MouseMode.CREATE_CONCEPTS),
            ("Crear Relaciones", "create_relations", MouseMode.CREATE_RELATIONS),
            ("Seleccionar Conceptos", "select_concepts", MouseMode.SELECT_CONCEPTS),
            ("Seleccionar Relaciones", "select_relations", MouseMode.SELECT_RELATIONS),
            ("Eliminar Conceptos", "delete_concepts", MouseMode.DELETE_CONCEPTS),
            ("Eliminar Relaciones", "delete_relations", MouseMode.DELETE_RELATIONS),
        ]
        
        for text, value, mode in modes:
            ttk.Radiobutton(
                mode_frame, 
                text=text, 
                variable=self.mouse_mode_var,
                value=value,
                command=lambda m=mode: self.canvas.set_mouse_mode(m)
            ).pack(anchor=tk.W, pady=1)
        
        # Controles de ejecución
        exec_frame = ttk.LabelFrame(control_frame, text="Ejecución", padding="5")
        exec_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.play_button = ttk.Button(exec_frame, text="Play", command=self.toggle_execution)
        self.play_button.pack(pady=5, fill=tk.X)
        
        # Visualización de iteraciones
        view_frame = ttk.LabelFrame(control_frame, text="Visualizar", padding="5")
        view_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(view_frame, text="Iteración:").pack(anchor=tk.W)
        self.iteration_label = ttk.Label(view_frame, text="0000 / 0000", font=("Arial", 10, "bold"))
        self.iteration_label.pack(pady=2)
        
        # Control de iteración
        iter_control_frame = ttk.Frame(view_frame)
        iter_control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(iter_control_frame, text="<<", width=3, command=self.prev_iteration).pack(side=tk.LEFT)
        
        self.iteration_entry = ttk.Entry(iter_control_frame, width=8, justify=tk.CENTER)
        self.iteration_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.iteration_entry.insert(0, "0")
        self.iteration_entry.bind("<Return>", lambda e: self.goto_iteration())
        
        ttk.Button(iter_control_frame, text=">>", width=3, command=self.next_iteration).pack(side=tk.LEFT)
        
        ttk.Button(view_frame, text="Ir a Iteración", command=self.goto_iteration).pack(pady=2, fill=tk.X)
        
        # Configuración rápida
        config_frame = ttk.LabelFrame(control_frame, text="Configuración", padding="5")
        config_frame.pack(fill=tk.X)
        
        # Vista proporcional
        self.view_proportional_var = tk.BooleanVar()
        ttk.Checkbutton(
            config_frame, 
            text="Vista proporcional", 
            variable=self.view_proportional_var,
            command=self.on_toggle_view_checkbox
        ).pack(anchor=tk.W)
        
        # Parar al estabilizar
        self.stabilize_var = tk.BooleanVar()
        ttk.Checkbutton(
            config_frame, 
            text="Parar al estabilizar", 
            variable=self.stabilize_var,
            command=self.toggle_stabilization
        ).pack(anchor=tk.W)
        
        # Normalización 
        norm_row = ttk.Frame(config_frame)
        norm_row.pack(fill=tk.X, pady=(8, 4))
        ttk.Label(norm_row, text="Normalización:").pack(side=tk.LEFT)
        self.norm_combo_var = tk.StringVar(value="relu")
        self.norm_combo = ttk.Combobox(
            norm_row,
            state="readonly",
            values=["syc", "sy", "bistate", "tristate", "tanh", "sigmoid", "linear", "relu"],
            textvariable=self.norm_combo_var,
            width=15,
        )
        self.norm_combo.pack(side=tk.RIGHT)
        self.norm_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._on_norm_combo_change(),
        )
        
        # Inferencia
        infer_row = ttk.Frame(config_frame)
        infer_row.pack(fill=tk.X, pady=(4, 4))
        ttk.Label(infer_row, text="Inferencia:").pack(side=tk.LEFT)
        self.infer_combo_var = tk.StringVar(value="kosko_rescaled")
        self.infer_combo = ttk.Combobox(
            infer_row,
            state="readonly",
            values=["kosko_standard", "kosko_memory", "kosko_rescaled"],
            textvariable=self.infer_combo_var,
            width=15,
        )
        self.infer_combo.pack(side=tk.RIGHT)
        self.infer_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._on_infer_combo_change(),
        )
        
        # Iteraciones (máx.)
        iter_cfg_row = ttk.Frame(config_frame)
        iter_cfg_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(iter_cfg_row, text="Iteraciones (máx.):").pack(side=tk.LEFT)
        self.max_iter_var = tk.IntVar(value=10)
        max_iter_entry = ttk.Entry(iter_cfg_row, width=6, textvariable=self.max_iter_var, justify=tk.RIGHT)
        max_iter_entry.pack(side=tk.RIGHT)
        max_iter_entry.bind("<Return>", lambda e: self._apply_max_iterations())
        max_iter_entry.bind("<FocusOut>", lambda e: self._apply_max_iterations())
        
        # Información del mapa
        info_frame = ttk.LabelFrame(control_frame, text="Información", padding="5")
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.info_label = ttk.Label(info_frame, text="Conceptos: 0\nRelaciones: 0", font=("Arial", 9))
        self.info_label.pack()
        # Botón de resultados, inicialmente deshabilitado
        self.results_button = ttk.Button(control_frame, text="Resultados...", state=tk.DISABLED, command=self.show_results_dialog)
        self.results_button.pack(fill=tk.X, pady=(8, 0))
    
    def setup_canvas_area(self, parent):
        """Configura el área del canvas con scroll"""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas con scrollbars
        self.canvas = MapCanvas(
            canvas_frame, 
            self.map_obj, 
            width=800, 
            height=600, 
            scrollregion=(0, 0, 1200, 1200),
        )
        
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        # Grid layout
        self.canvas.grid(row=0, column=0, sticky="nsew")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Configurar seguimiento del ratón (sin sobrescribir handlers del canvas)
        self.canvas.bind("<Motion>", self.update_mouse_position, add="+")
        self.canvas.bind("<B1-Motion>", self.update_mouse_position, add="+")
        
        # Inicializar RunFCM y callback al finalizar para habilitar botón de resultados
        self.fcm_runner = RunFCM(self.canvas, self.play_button, self.iteration_label, on_finish=self.on_simulation_finished)
        # Sincronizar control de iteraciones si existe
        try:
            if hasattr(self, 'max_iter_var'):
                self.max_iter_var.set(self.fcm_runner.get_max_iterations())
        except Exception:
            pass
        
        # Dibujo inicial
        self.canvas.repaint()
        self.update_info_panel()
        # Enlazar refresco ante cambios estructurales en el mapa
        self.canvas.bind("<<MapChanged>>", lambda e: self.on_map_changed())

    def on_simulation_finished(self):
        """Habilita botón de resultados tras finalizar una simulación."""
        if self.map_obj.size_concepts_data() > 1:
            try:
                self.results_button.config(state=tk.NORMAL)
            except Exception:
                pass

    def show_results_dialog(self):
        """Abre el diálogo de resultados/convergencia externo."""
        if self.map_obj.size_concepts_data() <= 1:
            messagebox.showwarning("Resultados", "No hay datos de ejecución disponibles.")
            return
        ResultsDialog(self.root, self.map_obj).show()

    

    

    

    # =====================
    # Entrada/Salida de matriz CSV
    # =====================
    def export_matrix_csv(self):
        """Exporta la matriz de adyacencia actual a un archivo CSV."""
        default_name = "adjacency.csv"
        filepath = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar matriz (CSV)",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=default_name,
        )
        if not filepath:
            return
        try:
            self.map_obj.export_adjacency_csv(filepath)
            messagebox.showinfo("Exportación", f"Matriz exportada a\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def import_matrix_csv(self):
        """Importa una matriz de adyacencia desde CSV y reconstruye el mapa.

        Establece los valores iniciales de todos los conceptos a 0.
        """
        filepath = filedialog.askopenfilename(
            parent=self.root,
            title="Importar matriz (CSV)",
            filetypes=[("CSV", "*.csv")],
        )
        if not filepath:
            return
        try:
            self.map_obj.import_adjacency_csv(filepath)
            # Reset view and repaint
            self.canvas.repaint()
            self.update_info_panel()
            messagebox.showinfo("Importación", "Matriz cargada. Los valores iniciales se han puesto a 0.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo importar: {e}")

    def export_matrix_xlsx(self):
        """Exporta la matriz de adyacencia a un archivo Excel (.xlsx)."""
        try:
            import pandas as pd
        except ImportError:
            messagebox.showerror("Dependencia faltante", "Necesitas instalar pandas y openpyxl:\npip install pandas openpyxl")
            return
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar matriz (Excel)",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="matriz.xlsx",
        )
        if not filename:
            return
        try:
            names, matrix = self.map_obj.get_adjacency_matrix()
            df = pd.DataFrame(matrix, index=names, columns=names)
            df.to_excel(filename, sheet_name="Matriz de adyacencia")
            messagebox.showinfo("Exportación", f"Matriz exportada a\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def import_matrix_xlsx(self):
        """Importa la matriz de adyacencia desde Excel (.xlsx) y reconstruye el mapa. Establece los valores iniciales de todos los conceptos a 0."""
        try:
            import pandas as pd
        except ImportError:
            messagebox.showerror("Dependencia faltante", "Necesitas instalar pandas y openpyxl:\npip install pandas openpyxl")
            return
        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Importar matriz (Excel)",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not filename:
            return
        try:
            df = pd.read_excel(filename, sheet_name=0, index_col=0)
            # Convertir a CSV temporal y usar el importador existente
            import tempfile
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
                df.to_csv(f.name, index=True)
                self.map_obj.import_adjacency_csv(f.name)
            os.unlink(f.name)
            self.canvas.repaint()
            self.update_info_panel()
            messagebox.showinfo("Importación", "Matriz cargada. Los valores iniciales se han puesto a 0.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo importar: {e}")
    
    def setup_menu(self):
        """Configura la barra de menú"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Nuevo", command=self.new_map, accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Abrir...", command=self.open_map, accelerator="Ctrl+O")
        file_menu.add_command(label="Guardar...", command=self.save_map, accelerator="Ctrl+S")
        file_menu.add_command(label="Guardar como...", command=self.save_map_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exportar matriz (CSV)...", command=self.export_matrix_csv)
        file_menu.add_command(label="Importar matriz (CSV)...", command=self.import_matrix_csv)
        file_menu.add_command(label="Exportar matriz (Excel)...", command=self.export_matrix_xlsx)
        file_menu.add_command(label="Importar matriz (Excel)...", command=self.import_matrix_xlsx)
        file_menu.add_separator()
        file_menu.add_command(label="Guardar valores iniciales (Excel)...", command=self.save_initial_values_excel)
        file_menu.add_command(label="Cargar valores iniciales (Excel)...", command=self.load_initial_values_excel)
        file_menu.add_separator()
        file_menu.add_command(label="Guardar Ejecución...", command=self.save_execution)
        file_menu.add_separator()
        file_menu.add_command(label="Cerrar", command=self.close_window, accelerator="Ctrl+W")
        
        
        # Menú Vista
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Vista", menu=view_menu)
        
        self.view_mode = tk.StringVar(value="fixed")
        view_menu.add_radiobutton(
            label="Tamaño Fijo", 
            variable=self.view_mode, 
            value="fixed", 
            command=self.change_view_mode
        )
        view_menu.add_radiobutton(
            label="Proporcional", 
            variable=self.view_mode, 
            value="proportional", 
            command=self.change_view_mode
        )
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Zoom Reset", command=self.zoom_reset, accelerator="Ctrl+0")
        
        # Menú Ejecución
        exec_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ejecución", menu=exec_menu)
        exec_menu.add_command(label="Ejecutar/Pausar", command=self.toggle_execution, accelerator="F5")
        exec_menu.add_command(label="Resetear", command=self.reset_execution, accelerator="F6")
        exec_menu.add_separator()
        exec_menu.add_command(label="Configurar Retardo...", command=self.configure_delay)
        exec_menu.add_command(label="Configurar Iteraciones...", command=self.configure_iterations)
        exec_menu.add_separator()
        
        # Submenu normalización
        norm_menu = tk.Menu(exec_menu, tearoff=0)
        exec_menu.add_cascade(label="Normalización", menu=norm_menu)
        
        self.norm_type = tk.StringVar(value="relu")
        norm_menu.add_radiobutton(
            label="Saturación (SyC)", 
            variable=self.norm_type, 
            value="syc", 
            command=self.change_normalization
        )
        norm_menu.add_radiobutton(
            label="Sigmoidal (Sy)", 
            variable=self.norm_type, 
            value="sy", 
            command=self.change_normalization
        )
        norm_menu.add_radiobutton(
            label="BiState", 
            variable=self.norm_type, 
            value="bistate", 
            command=self.change_normalization
        )
        norm_menu.add_radiobutton(
            label="TriState", 
            variable=self.norm_type, 
            value="tristate", 
            command=self.change_normalization
        )
        norm_menu.add_separator()
        norm_menu.add_radiobutton(
            label="Tanh", 
            variable=self.norm_type, 
            value="tanh", 
            command=self.change_normalization
        )
        norm_menu.add_radiobutton(
            label="Sigmoid", 
            variable=self.norm_type, 
            value="sigmoid", 
            command=self.change_normalization
        )
        norm_menu.add_radiobutton(
            label="Lineal", 
            variable=self.norm_type, 
            value="linear", 
            command=self.change_normalization
        )
        norm_menu.add_radiobutton(
            label="ReLU", 
            variable=self.norm_type, 
            value="relu", 
            command=self.change_normalization
        )
        
        # Submenú Inferencia
        infer_menu = tk.Menu(exec_menu, tearoff=0)
        exec_menu.add_cascade(label="Inferencia", menu=infer_menu)
        
        self.infer_type = tk.StringVar(value="kosko_rescaled")
        infer_menu.add_radiobutton(
            label="Kosko Estándar", 
            variable=self.infer_type, 
            value="kosko_standard", 
            command=lambda: self.change_inference("kosko_standard")
        )
        infer_menu.add_radiobutton(
            label="Kosko con Memoria (Ec. 7)", 
            variable=self.infer_type, 
            value="kosko_memory", 
            command=lambda: self.change_inference("kosko_memory")
        )
        infer_menu.add_radiobutton(
            label="Kosko Reescalada (Ec. 8)", 
            variable=self.infer_type, 
            value="kosko_rescaled", 
            command=lambda: self.change_inference("kosko_rescaled")
        )
        
        # Atajos de teclado
        self.setup_keyboard_shortcuts()

        # Menú Aprendizaje (Entrenamiento)
        train_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aprendizaje", menu=train_menu)
        train_menu.add_command(label="Entrenar (PSO)...", command=self.train_with_pso)
        train_menu.add_separator()
        # Ver evolución del mejor individuo (se habilita tras entrenar)
        self.menu_view_pso = tk.Menu(train_menu, tearoff=0)
        menubar.entryconfig('Aprendizaje')
        train_menu.add_command(label="Ver evolución PSO", command=self.show_pso_history_dialog, state=tk.DISABLED)
        train_menu.add_command(label="Evaluar...", command=self.open_evaluation_dialog)
        self._train_menu = train_menu
    
    def setup_keyboard_shortcuts(self):
        """Configura atajos de teclado"""
        self.root.bind("<Control-n>", lambda e: self.new_map())
        self.root.bind("<Control-o>", lambda e: self.open_map())
        self.root.bind("<Control-s>", lambda e: self.save_map())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_map_as())
        self.root.bind("<Control-w>", lambda e: self.close_window())
        self.root.bind("<F5>", lambda e: self.toggle_execution())
        self.root.bind("<F6>", lambda e: self.reset_execution())

        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.zoom_reset())
    
    def setup_status_bar(self):
        """Configura la barra de estado"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Separator(status_frame, orient=tk.HORIZONTAL).pack(fill=tk.X)
        
        status_content = ttk.Frame(status_frame)
        status_content.pack(fill=tk.X, padx=5, pady=2)
        
        self.status_label = ttk.Label(status_content, text="Listo")
        self.status_label.pack(side=tk.LEFT)
        
        # Información adicional en la barra de estado
        map_type = "Dinámico" if self.map_obj.is_dynamic() else "Estático"
        self.map_type_label = ttk.Label(status_content, text=f"Tipo: {map_type}")
        self.map_type_label.pack(side=tk.RIGHT)
    
    def update_mouse_position(self, event):
        """Actualiza la posición del ratón en la etiqueta"""
        self.mouse_pos_label.config(text=f"X: {event.x}, Y: {event.y}")
    
    def update_info_panel(self):
        """Actualiza el panel de información"""
        concepts_count = len(self.map_obj.get_concept_list())
        relations_count = len(self.map_obj.get_relation_list())
        info_text = f"Conceptos: {concepts_count}\nRelaciones: {relations_count}"
        self.info_label.config(text=info_text)
    
    def toggle_execution(self):
        """Alterna entre ejecutar y resetear"""
        if self.play_button['text'] == "Play":
            self.fcm_runner.run()
            self.status_label.config(text="Ejecutando simulación...")
        else:  # Reset
            self.reset_execution()

    def on_map_changed(self):
        """Se llama cuando se modifican conceptos/relaciones desde el canvas."""
        # Al cambiar la estructura, reiniciamos ejecución para evitar estados incoherentes
        try:
            self.reset_execution()
        except Exception:
            # Si aún no está listo el runner, al menos repintar
            self.canvas.repaint()
        self.update_info_panel()
        # Deshabilitar botón de resultados hasta nueva simulación
        try:
            self.results_button.config(state=tk.DISABLED)
        except Exception:
            pass
    
    def reset_execution(self):
        """Resetea la ejecución del mapa"""
        self.map_obj.reset_concepts()
        self.canvas.repaint()
        self.play_button.config(text="Play")
        self.iteration_label.config(text=self.map_obj.get_iteration_label())
        self.iteration_entry.delete(0, tk.END)
        self.iteration_entry.insert(0, "0")
        self.status_label.config(text="Ejecución reseteada")
    
    def _apply_max_iterations(self):
        """Aplica el valor de iteraciones máximas desde el panel Configuración."""
        try:
            value = int(self.max_iter_var.get())
            if value < 1:
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "Iteraciones (máx.) debe ser un entero >= 1")
            return
        try:
            self.fcm_runner.set_max_iterations(value)
            self.status_label.config(text=f"Máximo de iteraciones: {value}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo aplicar iteraciones: {e}")
    
    def prev_iteration(self):
        """Va a la iteración anterior"""
        current = self.map_obj.get_current_iteration()
        if current > 0:
            self.map_obj.set_show_iteration(current - 1)
            self.update_iteration_display()
    
    def next_iteration(self):
        """Va a la siguiente iteración"""
        current = self.map_obj.get_current_iteration()
        max_iter = self.map_obj.size_concepts_data() - 1
        if current < max_iter:
            self.map_obj.set_show_iteration(current + 1)
            self.update_iteration_display()
    
    def goto_iteration(self):
        """Va a una iteración específica"""
        try:
            iteration = int(self.iteration_entry.get())
            max_iter = self.map_obj.size_concepts_data() - 1
            if 0 <= iteration <= max_iter:
                self.map_obj.set_show_iteration(iteration)
                self.update_iteration_display()
            else:
                messagebox.showwarning("Advertencia", f"Iteración debe estar entre 0 y {max_iter}")
        except ValueError:
            messagebox.showerror("Error", "Número de iteración inválido")
    
    def update_iteration_display(self):
        """Actualiza la visualización de iteración"""
        self.canvas.repaint()
        self.iteration_label.config(text=self.map_obj.get_iteration_label())
        self.iteration_entry.delete(0, tk.END)
        self.iteration_entry.insert(0, str(self.map_obj.get_current_iteration()))
    
    def change_view_mode(self):
        """Cambia el modo de visualización (fuente de verdad: menú)."""
        proportional = (self.view_mode.get() == "proportional")
        self.canvas.draw_proportionally = proportional
        # Sincronizar checkbox
        if hasattr(self, 'view_proportional_var'):
            self.view_proportional_var.set(proportional)
        self.canvas.repaint()
        self.status_label.config(text=f"Vista: {'Proporcional' if proportional else 'Fija'}")

    def on_toggle_view_checkbox(self):
        """Handler del checkbox: actualiza view_mode y aplica cambio."""
        proportional = self.view_proportional_var.get()
        self.view_mode.set("proportional" if proportional else "fixed")
        self.change_view_mode()
    
    def _on_norm_combo_change(self):
        """Sincroniza el cambio de normalización del combo con el menú/runner."""
        try:
            selected = self.norm_combo_var.get()
            # Actualizar variable de menú y aplicar
            if hasattr(self, 'norm_type'):
                self.norm_type.set(selected)
                self.change_normalization()
        except Exception:
            pass
    
    def _on_infer_combo_change(self):
        """Sincroniza el cambio de inferencia del combo con el runner."""
        try:
            selected = self.infer_combo_var.get()
            self.change_inference(selected)
        except Exception:
            pass
    
    def change_inference(self, infer_key: str = None):
        """Cambia el tipo de inferencia"""
        from tkinter import messagebox
        
        if infer_key is None:
            infer_key = self.infer_combo_var.get() if hasattr(self, 'infer_combo_var') else "kosko_rescaled"
        
        infer_map = {
            "kosko_standard": InferenceType.KOSKO_STANDARD,
            "kosko_memory": InferenceType.KOSKO_MEMORY,
            "kosko_rescaled": InferenceType.KOSKO_RESCALED
        }
        new_infer = infer_map.get(infer_key, InferenceType.KOSKO_RESCALED)
        
        # Advertir si se cambia la inferencia después de entrenar
        if self._trained_inference is not None and new_infer != self._trained_inference:
            infer_names = {
                InferenceType.KOSKO_STANDARD: "Kosko Estándar",
                InferenceType.KOSKO_MEMORY: "Kosko con Memoria",
                InferenceType.KOSKO_RESCALED: "Kosko Reescalada",
            }
            trained_name = infer_names.get(self._trained_inference, "desconocida")
            messagebox.showwarning(
                "Advertencia de inferencia",
                f"Este mapa fue entrenado con '{trained_name}'. Los pesos aprendidos están optimizados para esa inferencia."
            )
        
        self.fcm_runner.inference_type = new_infer
        
        infer_names = {
            "kosko_standard": "Kosko Estándar",
            "kosko_memory": "Kosko con Memoria",
            "kosko_rescaled": "Kosko Reescalada"
        }
        self.status_label.config(text=f"Inferencia: {infer_names.get(infer_key, 'Kosko Reescalada')}")
    
    def change_normalization(self):
        """Cambia el tipo de normalización"""
        from tkinter import messagebox
        
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
        new_norm = norm_map.get(self.norm_type.get(), NormalizationType.RELU)
        
        # Advertir si se cambia la normalización después de entrenar
        if self._trained_normalization is not None and new_norm != self._trained_normalization:
            norm_names = {
                NormalizationType.SYC: "Saturación (SyC)",
                NormalizationType.SY: "Sigmoidal (Sy)",
                NormalizationType.BISTATE: "BiState",
                NormalizationType.TRISTATE: "TriState",
                NormalizationType.TANH: "Tanh",
                NormalizationType.SIGMOID: "Sigmoid",
                NormalizationType.LINEAR: "Lineal",
                NormalizationType.RELU: "ReLU",
            }
            trained_name = norm_names.get(self._trained_normalization, "desconocida")
            messagebox.showwarning(
                "Advertencia de normalización",
                f"Este mapa fue entrenado con '{trained_name}'.\n"
                f"Los pesos aprendidos están optimizados para esa normalización.\n"
            )
        
        self.fcm_runner.saturation_type = new_norm
        
        norm_names = {
            "syc": "Saturación (SyC)",
            "sy": "Sigmoidal (Sy)",
            "bistate": "BiState",
            "tristate": "TriState",
            "tanh": "Tanh",
            "sigmoid": "Sigmoid",
            "linear": "Lineal",
            "relu": "ReLU",
        }
        self.status_label.config(text=f"Normalización: {norm_names.get(self.norm_type.get(), 'ReLU')}")
        # Refrescar panel de información para reflejar normalización
        try:
            self.update_info_panel()
        except Exception:
            pass
        # Sincronizar combo si existe
        try:
            if hasattr(self, 'norm_combo_var'):
                self.norm_combo_var.set(self.norm_type.get())
        except Exception:
            pass
    
    def toggle_stabilization(self):
        """Activa/desactiva parada por estabilización"""
        self.fcm_runner.stop_on_stabilize = self.stabilize_var.get()
        status = "activada" if self.stabilize_var.get() else "desactivada"
        self.status_label.config(text=f"Parada por estabilización {status}")
    
    def configure_delay(self):
        """Configura el retardo de ejecución"""
        dialog = DelayDialog(self.root, self.fcm_runner.get_delay())
        result = dialog.show()
        if result is not None:
            self.fcm_runner.set_delay(result)
            self.status_label.config(text=f"Retardo configurado: {result}ms")
    
    def configure_iterations(self):
        """Configura el número máximo de iteraciones"""
        dialog = IterationDialog(self.root, self.fcm_runner.get_max_iterations())
        result = dialog.show()
        if result is not None:
            self.fcm_runner.set_max_iterations(result)
            self.status_label.config(text=f"Máximo de iteraciones: {result}")
            try:
                if hasattr(self, 'max_iter_var'):
                    self.max_iter_var.set(result)
            except Exception:
                pass
    
    def new_map(self):
        """Crea un nuevo mapa"""
        if len(self.map_obj.get_concept_list()) > 0 or len(self.map_obj.get_relation_list()) > 0:
            if not messagebox.askyesno("Nuevo Mapa", "¿Está seguro? Se perderán los cambios no guardados."):
                return
        
        self.map_obj.clear()
        self.reset_execution()
        self.update_info_panel()
        # Resetear normalización e inferencia entrenadas
        self._trained_normalization = None
        self._trained_inference = None
        if hasattr(self.map_obj, 'trained_normalization'):
            self.map_obj.trained_normalization = None
        if hasattr(self.map_obj, 'trained_inference'):
            self.map_obj.trained_inference = None
        
        map_type = "DFCM" if self.map_obj.is_dynamic() else "FCM"
        self.root.title(f"{map_type} Designer - Sin título")
        self.status_label.config(text="Nuevo mapa creado")
    
    
    def open_map(self):
        """Abre un mapa desde archivo"""
        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Abrir Mapa",
            filetypes=[("Archivos FCM", "*.fcm"), ("Archivos DFCM", "*.dfcm"), ("Todos los archivos", "*.*")],
            defaultextension=".fcm"
        )
        
        if filename:
            try:
                directory = os.path.dirname(filename)
                file = os.path.basename(filename)
                # Inferir dinámico por extensión
                ext = os.path.splitext(file)[1].lower()
                self.map_obj.dynamic = (ext == ".dfcm")
                
                self.map_obj.load(directory, file)
                self.canvas.repaint()
                self.reset_execution()
                self.update_info_panel()
                
                # Restaurar normalización entrenada si existe
                if hasattr(self.map_obj, 'trained_normalization') and self.map_obj.trained_normalization is not None:
                    self._trained_normalization = NormalizationType(self.map_obj.trained_normalization)
                    # Sincronizar UI con la normalización guardada
                    norm_reverse_map = {
                        NormalizationType.SYC: "syc",
                        NormalizationType.SY: "sy",
                        NormalizationType.BISTATE: "bistate",
                        NormalizationType.TRISTATE: "tristate",
                        NormalizationType.TANH: "tanh",
                        NormalizationType.SIGMOID: "sigmoid",
                        NormalizationType.LINEAR: "linear",
                        NormalizationType.RELU: "relu"
                    }
                    norm_key = norm_reverse_map.get(self._trained_normalization, "syc")
                    if hasattr(self, 'norm_type'):
                        self.norm_type.set(norm_key)
                    if hasattr(self, 'norm_combo_var'):
                        self.norm_combo_var.set(norm_key)
                    self.fcm_runner.saturation_type = self._trained_normalization
                else:
                    # Mapa sin entrenamiento o archivo antiguo
                    self._trained_normalization = None
                
                # Restaurar inferencia entrenada si existe
                if hasattr(self.map_obj, 'trained_inference') and self.map_obj.trained_inference is not None:
                    self._trained_inference = InferenceType(self.map_obj.trained_inference)
                    # Sincronizar UI con la inferencia guardada
                    infer_reverse_map = {
                        InferenceType.KOSKO_STANDARD: "kosko_standard",
                        InferenceType.KOSKO_MEMORY: "kosko_memory",
                        InferenceType.KOSKO_RESCALED: "kosko_rescaled"
                    }
                    infer_key = infer_reverse_map.get(self._trained_inference, "kosko_standard")
                    if hasattr(self, 'infer_type'):
                        self.infer_type.set(infer_key)
                    if hasattr(self, 'infer_combo_var'):
                        self.infer_combo_var.set(infer_key)
                    self.fcm_runner.inference_type = self._trained_inference
                else:
                    self._trained_inference = None
                
                map_type = "DFCM" if self.map_obj.is_dynamic() else "FCM"
                self.root.title(f"{map_type} Designer - {file}")
                # Actualizar etiqueta de tipo
                self.map_type_label.config(text=f"Tipo: {'Dinámico' if self.map_obj.is_dynamic() else 'Estático'}")
                self.status_label.config(text=f"Archivo cargado: {file}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar archivo:\n{str(e)}")
    
    def save_map(self):
        """Guarda el mapa actual"""
        # Verificar si ya tiene nombre de archivo
        current_title = self.root.title()
        if "Sin título" not in current_title:
            # Extraer nombre del archivo del título
            filename = current_title.split(" - ")[-1]
            if filename.endswith(".fcm") or filename.endswith(".dfcm"):
                try:
                    directory = os.getcwd()  # Usar directorio actual por defecto
                    self.map_obj.save(directory, filename)
                    self.status_label.config(text=f"Archivo guardado: {filename}")
                    return
                except Exception as e:
                    messagebox.showerror("Error", f"Error al guardar archivo:\n{str(e)}")
        
        # Si no tiene nombre, usar "Guardar como"
        self.save_map_as()
    
    def save_map_as(self):
        """Guarda el mapa con un nombre específico"""
        default_ext = ".dfcm" if self.map_obj.is_dynamic() else ".fcm"
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar Mapa",
            defaultextension=default_ext,
            filetypes=[("Archivos FCM", "*.fcm"), ("Archivos DFCM", "*.dfcm"), ("Todos los archivos", "*.*")]
        )
        
        if filename:
            try:
                directory = os.path.dirname(filename)
                file = os.path.basename(filename)
                # Asegurar extensión si falta
                name, ext = os.path.splitext(file)
                if ext.lower() not in [".fcm", ".dfcm"]:
                    ext = ".dfcm" if self.map_obj.is_dynamic() else ".fcm"
                    file = name + ext
                
                self.map_obj.save(directory, file)
                
                map_type = "DFCM" if self.map_obj.is_dynamic() else "FCM"
                self.root.title(f"{map_type} Designer - {file}")
                self.map_type_label.config(text=f"Tipo: {'Dinámico' if self.map_obj.is_dynamic() else 'Estático'}")
                self.status_label.config(text=f"Archivo guardado: {file}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar archivo:\n{str(e)}")
    
    def save_initial_values_excel(self):
        """Exporta los valores iniciales de los conceptos a un archivo Excel."""
        concepts = self.map_obj.get_concept_list()
        if not concepts:
            messagebox.showwarning("Aviso", "No hay conceptos para exportar.")
            return
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar valores iniciales",
            defaultextension=".xlsx",
            filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")]
        )
        if not filename:
            return
        try:
            import pandas as pd  # type: ignore
        except ImportError:
            messagebox.showerror(
                "Dependencia faltante",
                "Necesitas instalar pandas y openpyxl para trabajar con Excel:\n pip install pandas openpyxl",
            )
            return
        data_names = [concept.get_name() for concept in concepts]
        data_values = [concept.get_initial_value() for concept in concepts]
        df = pd.DataFrame([data_names, data_values])
        try:
            df.to_excel(filename, header=False, index=False)
            self.status_label.config(text=f"Valores iniciales guardados en {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}")
    
    def load_initial_values_excel(self):
        """Importa valores iniciales desde un archivo Excel (dos filas: nombres y valores)."""
        concepts = self.map_obj.get_concept_list()
        if not concepts:
            messagebox.showwarning("Aviso", "No hay conceptos en el mapa.")
            return
        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Cargar valores iniciales",
            filetypes=[("Archivos Excel", "*.xlsx;*.xls"), ("Todos los archivos", "*.*")]
        )
        if not filename:
            return
        try:
            import pandas as pd  # type: ignore
        except ImportError:
            messagebox.showerror(
                "Dependencia faltante",
                "Necesitas instalar pandas y openpyxl para trabajar con Excel:\n pip install pandas openpyxl",
            )
            return
        try:
            df = pd.read_excel(filename, header=None)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")
            return
        if df.shape[0] < 2:
            messagebox.showerror("Formato inválido", "Se requieren al menos dos filas (nombres y valores).")
            return
        raw_names = df.iloc[0].tolist()
        raw_values = df.iloc[1].tolist()
        concept_map = {concept.get_name(): concept for concept in concepts}
        applied = 0
        missing = []
        import math
        for name, value in zip(raw_names, raw_values):
            if name is None or (isinstance(name, float) and math.isnan(name)):
                continue
            name_str = str(name).strip()
            if not name_str:
                continue
            concept = concept_map.get(name_str)
            if concept is None:
                missing.append(name_str)
                continue
            try:
                val = float(value)
            except (TypeError, ValueError):
                missing.append(f"{name_str} (valor inválido)")
                continue
            concept.set_initial_value(val)
            concept.set_current_value(val)
            applied += 1
        if applied > 0:
            try:
                self.reset_execution()
            except Exception:
                self.canvas.repaint()
                self.update_info_panel()
            self.status_label.config(text=f"Valores iniciales cargados ({applied})")
        if missing:
            messagebox.showwarning(
                "Conceptos no actualizados",
                "No se pudieron actualizar los siguientes conceptos:\n" + "\n".join(missing)
            )
        if applied == 0 and not missing:
            messagebox.showinfo("Sin cambios", "No se aplicaron valores porque no se encontraron coincidencias.")
    
    def save_execution(self):
        """Guarda los resultados de ejecución"""
        if self.map_obj.size_concepts_data() <= 1:
            messagebox.showwarning("Advertencia", "No hay datos de ejecución para guardar.")
            return
        
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar Ejecución",
            defaultextension=".txt",
            filetypes=[("Archivos de texto", "*.txt"), ("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        
        if filename:
            try:
                directory = os.path.dirname(filename)
                file = os.path.basename(filename)
                
                self.map_obj.save_execution(directory, file)
                self.status_label.config(text=f"Ejecución guardada: {file}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar ejecución:\n{str(e)}")
    
    
    def zoom_in(self):
        """Acerca el zoom"""
        # Implementación básica de zoom
        self.canvas.scale("all", 0, 0, 1.1, 1.1)
        self.status_label.config(text="Zoom aumentado")
    
    def zoom_out(self):
        """Aleja el zoom"""
        # Implementación básica de zoom
        self.canvas.scale("all", 0, 0, 0.9, 0.9)
        self.status_label.config(text="Zoom reducido")
    
    def zoom_reset(self):
        """Resetea el zoom"""
        self.canvas.repaint()
        self.status_label.config(text="Zoom reseteado")
    
    
    

    
    def close_window(self):
        """Cierra la ventana"""
        # Verificar si hay cambios sin guardar
        if len(self.map_obj.get_concept_list()) > 0 or len(self.map_obj.get_relation_list()) > 0:
            current_title = self.root.title()
            if "Sin título" in current_title:
                response = messagebox.askyesnocancel(
                    "Cerrar Ventana", 
                    "Hay cambios sin guardar. ¿Desea guardar antes de cerrar?"
                )
                if response is True:  # Sí, guardar
                    self.save_map()
                    if "Sin título" in self.root.title():  # Si no se guardó, cancelar cierre
                        return
                elif response is None:  # Cancelar
                    return
                # Si response is False, cerrar sin guardar
        
        self.root.destroy()
    
    def show(self):
        """Muestra la ventana"""
        self.root.deiconify()
        
        # Configurar eventos adicionales después de mostrar
        self.canvas.after(100, self.update_info_panel)

    def train_with_pso(self):
        """Lanza diálogo para entrenar pesos con PSO y ejecutar el entrenamiento."""
        from trainer.pso_trainer import FCMPSOTrainer, PSOConfig
        from trainer.dataset import FCMDataset

        # Preparar opciones (el mapa podrá autogenerarse desde el CSV)
        concepts = [c.get_name() for c in self.map_obj.get_concept_list()]
        dlg = TrainPSODialog(self.root, concepts)
        params = dlg.show()
        if not params:
            return

        dataset_path = params["dataset_path"]
        try:
            import pandas as pd  # type: ignore
        except ImportError:
            messagebox.showerror(
                "Dependencia faltante",
                "Necesitas instalar pandas (y openpyxl si usas Excel):\n pip install pandas openpyxl",
            )
            return

        try:
            suffix = Path(dataset_path).suffix.lower()
            if suffix in {".xlsx", ".xls"}:
                df = pd.read_excel(dataset_path)
            else:
                df = pd.read_csv(dataset_path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo de entrenamiento:\n{e}")
            return

        if df.empty:
            messagebox.showerror("Error", "El archivo de entrenamiento no contiene datos.")
            return

        try:
            df = df.apply(pd.to_numeric, errors="raise")
        except Exception as e:
            messagebox.showerror("Error", f"El archivo contiene valores no numéricos:\n{e}")
            return

        header_cols = [str(col) for col in df.columns]
        df.columns = header_cols
        # Si existe 'count', el target es la penúltima columna (no 'count')
        if 'count' in header_cols and len(header_cols) >= 2:
            target_column = header_cols[-2] if header_cols[-1] == 'count' else header_cols[-1]
        else:
            target_column = header_cols[-1]
        target_concept = target_column
        adv = params.get("advanced", {})
        normalization = params.get("normalization", self.fcm_runner.saturation_type)
        inference = params.get("inference", self.fcm_runner.inference_type)
        num_classes = params.get("num_classes", 2)
        is_continuous = params.get("is_continuous", False)

        try:
            cfg = PSOConfig(
                swarm_size=int(adv.get("swarm_size", 30)),
                iterations=int(adv.get("iterations", 10)),
                eval_iterations=int(adv.get("eval_iterations", 10)),
                normalization=normalization,
                inference=inference,
                inertia=max(0.0, min(1.0, float(adv.get("w_value", 0.7)))),
                cognitive=float(adv.get("c1_value", 1.5)),
                social=float(adv.get("c2_value", 1.5)),
                weight_min=float(adv.get("weight_min", -1.0)),
                weight_max=float(adv.get("weight_max", 1.0)),
                velocity_clamp=float(adv.get("velocity_clamp", 0.2)),
            )
        except ValueError:
            messagebox.showerror("Error", "Parámetros de PSO inválidos.")
            return

        # Cargar dataset y, antes de entrenar, autogenerar un mapa totalmente conectado
        # (sin auto-relaciones) a partir de las columnas del CSV, con el target solo recibiendo.
        if target_column not in header_cols:
            messagebox.showerror("Error", f"La columna objetivo '{target_column}' no existe en el archivo")
            return

        # Construir lista de conceptos desde CSV (excluyendo 'count' si existe); el target solo recibirá
        concept_names = [col for col in header_cols if col != 'count']
        # Reconstruir mapa actual
        self.map_obj.clear()
        # Distribución en círculo para mayor legibilidad (como en importación de matriz)
        import math as _math
        n_nodes = len(concept_names)
        cx, cy = 500, 350
        base_radius = 220
        radius = max(160, min(360, base_radius + max(0, n_nodes - 8) * 12))
        node_r = 10
        for idx, name in enumerate(concept_names):
            angle = (2.0 * _math.pi * idx) / max(1, n_nodes)
            x = int(cx + radius * _math.cos(angle) - node_r)
            y = int(cy + radius * _math.sin(angle) - node_r)
            c = self.map_obj.add_concept(x, y, self.map_obj.is_dynamic())
            c.set_name(name)
            c.set_initial_value(0.0)
            c.set_current_value(0.0)
            # Etiqueta hacia fuera del círculo
            sin_a = _math.sin(angle)
            cos_a = _math.cos(angle)
            if abs(cos_a) >= abs(sin_a):
                c.set_label_position(1 if cos_a > 0 else 3)  # RIGHT : LEFT
            else:
                c.set_label_position(2 if sin_a > 0 else 0)  # BOTTOM : TOP
        self.map_obj.update_concepts_id()

        # Crear relaciones completamente conectadas sin auto-bucle.
        # Peso inicial bajo para evitar saturación inicial.
        initial_weight = 0.1
        # Mapa para buscar conceptos por nombre
        name_to_concept = {c.get_name(): c for c in self.map_obj.get_concept_list()}
        for src_name in concept_names:
            for dst_name in concept_names:
                if src_name == dst_name:
                    continue  # sin auto-relaciones
                if src_name == target_concept:
                    continue  # el target solo recibe
                src = name_to_concept.get(src_name)
                dst = name_to_concept.get(dst_name)
                if src and dst:
                    rel = self.map_obj.add_relation(src, dst)
                    rel.set_value(initial_weight)

        # Refrescar UI tras cambiar estructura
        try:
            self.reset_execution()
        except Exception:
            pass
        try:
            self.update_info_panel()
        except Exception:
            pass
        try:
            self.canvas.repaint()
        except Exception:
            pass

        # Detectar si existe columna 'count' para usar MSE ponderado
        has_count_column = 'count' in header_cols
        
        # Cargar dataset usando el método apropiado según si existe 'count'
        try:
            if has_count_column:
                # Usar método que detecta y maneja columna 'count' automáticamente
                dataset = FCMDataset.from_file_with_counts(dataset_path, target_column=target_column)
            else:
                # Cargar normalmente sin 'count'
                dataset = FCMDataset.from_file(dataset_path, target_column=target_column)
            
            # Normalizar según el tipo especificado por el usuario
            if is_continuous:
                # Normalización min-max para continuo: TODAS las features + target
                all_feature_names = set()
                for sample in dataset._samples:
                    all_feature_names.update(sample.features.keys())
                
                feature_stats = {}  # {feature_name: (min, max)}
                target_values = []
                
                # Calcular estadísticas
                for sample in dataset._samples:
                    target_values.append(sample.target_value)
                    for feat_name, feat_val in sample.features.items():
                        if feat_name not in feature_stats:
                            feature_stats[feat_name] = [feat_val, feat_val]
                        else:
                            feature_stats[feat_name][0] = min(feature_stats[feat_name][0], feat_val)
                            feature_stats[feat_name][1] = max(feature_stats[feat_name][1], feat_val)
                
                target_min = min(target_values)
                target_max = max(target_values)
                
                # Normalizar todas las features y target
                from trainer.dataset import Sample
                normalized_samples = []
                for sample in dataset._samples:
                    normalized_features = {}
                    for feat_name, feat_val in sample.features.items():
                        feat_min, feat_max = feature_stats.get(feat_name, (feat_val, feat_val))
                        if feat_max > feat_min:
                            normalized_val = (feat_val - feat_min) / (feat_max - feat_min)
                            normalized_features[feat_name] = max(0.0, min(1.0, normalized_val))
                        else:
                            normalized_features[feat_name] = feat_val
                    
                    # Normalizar target
                    if target_max > target_min:
                        normalized_target = (sample.target_value - target_min) / (target_max - target_min)
                        normalized_target = max(0.0, min(1.0, normalized_target))
                    else:
                        normalized_target = sample.target_value
                    
                    normalized_samples.append(Sample(
                        features=normalized_features,
                        target_value=normalized_target,
                        weight=sample.weight
                    ))
                dataset = FCMDataset(normalized_samples)
                self.status_label.config(text="Normalizando datos continuos (min-max en todas las columnas)...")
            elif num_classes and num_classes >= 3:
                # Reescalado multiclase: k/(N-1)
                scale_den = float(num_classes - 1)
                from trainer.dataset import Sample
                normalized_samples = []
                for sample in dataset._samples:
                    val = sample.target_value
                    normalized_val = val
                    try:
                        k_val = float(val)
                        if k_val.is_integer() and 0.0 <= k_val <= scale_den:
                            normalized_val = float(int(k_val)) / scale_den
                    except Exception:
                        pass
                    normalized_samples.append(Sample(
                        features=sample.features,
                        target_value=normalized_val,
                        weight=sample.weight
                    ))
                dataset = FCMDataset(normalized_samples)
                self.status_label.config(text=f"Reescalando multiclase ({num_classes} clases)...")
            else:
                # Binario (N=2): no se modifica
                self.status_label.config(text="Usando datos binarios (sin normalización)...")
            
            self.root.update_idletasks()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo preparar el dataset de entrenamiento:\n{e}")
            return

        # Entrenar
        status_prefix = "Entrenando PSO (ponderado)" if has_count_column else "Entrenando PSO"
        self.status_label.config(text=f"{status_prefix}...")
        self.root.update_idletasks()

        try:
            trainer = FCMPSOTrainer(self.map_obj, target_concept_name=target_concept, config=cfg)
            # Ejecutar entrenamiento en segundo plano y actualizar estado con progreso textual
            def _run_train():
                try:
                    def on_progress(i, total):
                        # actualizar status en hilo principal
                        self.root.after(0, lambda: self.status_label.config(text=f"{status_prefix}: iteración {i}/{total}"))
                    best, mse = trainer.fit(dataset, progress_cb=on_progress)
                    # Obtener historial completo
                    history = []
                    try:
                        history = trainer.get_best_history() or []
                    except Exception:
                        history = []
                    def _done():
                        # Guardar normalización usada en el entrenamiento
                        self._trained_normalization = cfg.normalization
                        # Guardar también en el objeto Map para persistencia
                        if hasattr(self.map_obj, 'trained_normalization'):
                            self.map_obj.trained_normalization = cfg.normalization.value
                        # Actualizar normalización del runner para garantizar consistencia entrenamiento ↔ inferencia
                        self.fcm_runner.saturation_type = cfg.normalization
                        # Sincronizar UI normalización
                        norm_reverse_map = {
                            NormalizationType.SYC: "syc",
                            NormalizationType.SY: "sy",
                            NormalizationType.BISTATE: "bistate",
                            NormalizationType.TRISTATE: "tristate",
                            NormalizationType.TANH: "tanh",
                            NormalizationType.SIGMOID: "sigmoid",
                            NormalizationType.LINEAR: "linear",
                            NormalizationType.RELU: "relu"
                        }
                        norm_key = norm_reverse_map.get(cfg.normalization, "syc")
                        if hasattr(self, 'norm_type'):
                            self.norm_type.set(norm_key)
                        if hasattr(self, 'norm_combo_var'):
                            self.norm_combo_var.set(norm_key)
                        
                        # Guardar inferencia usada en el entrenamiento
                        self._trained_inference = cfg.inference
                        if hasattr(self.map_obj, 'trained_inference'):
                            self.map_obj.trained_inference = cfg.inference.value
                        self.fcm_runner.inference_type = cfg.inference
                        # Sincronizar UI inferencia
                        infer_reverse_map = {
                            InferenceType.KOSKO_STANDARD: "kosko_standard",
                            InferenceType.KOSKO_MEMORY: "kosko_memory",
                            InferenceType.KOSKO_RESCALED: "kosko_rescaled"
                        }
                        infer_key = infer_reverse_map.get(cfg.inference, "kosko_standard")
                        if hasattr(self, 'infer_type'):
                            self.infer_type.set(infer_key)
                        if hasattr(self, 'infer_combo_var'):
                            self.infer_combo_var.set(infer_key)
                        
                        # Aplicar automáticamente los mejores pesos al mapa
                        try:
                            from trainer.simulator import FCMSimulator
                            sim = FCMSimulator(self.map_obj, normalization=cfg.normalization)
                            sim.set_weights_flat(best)
                            self.canvas.repaint()
                            self.update_info_panel()
                        except Exception as e:
                            messagebox.showerror("Error", f"No se pudieron aplicar pesos automáticamente: {e}")
                        
                        status_suffix = " (ponderado)" if has_count_column else ""
                        self.status_label.config(text=f"Entrenamiento finalizado{status_suffix}. Mejor MSE: {mse:.6f} (Norm: {norm_key}, Infer: {infer_key}). Pesos aplicados.")
                        # Guardar historial y habilitar menú "Ver evolución PSO"
                        self._last_pso_history = history
                        try:
                            self._train_menu.entryconfig("Ver evolución PSO", state=tk.NORMAL)
                        except Exception:
                            pass
                    self.root.after(0, _done)
                except Exception as ex:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Fallo en entrenamiento:\n{ex}"))
            import threading as _th
            _th.Thread(target=_run_train, daemon=True).start()
            return
        except Exception as e:
            messagebox.showerror("Error", f"Fallo en entrenamiento:\n{e}")
            return

        # El flujo asíncrono retorna antes; el resto de código se maneja en _done()

    def _save_pso_best_history_csv(self, history):
        """Guarda a CSV la evolución del mejor individuo PSO."""
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar mejor individuo PSO (CSV)",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="pso_mejor_historial.csv",
        )
        if not filename:
            return
        # Construir tabla: iteration, mse, w1, w2, ...
        import csv
        # Determinar máximo número de pesos
        max_w = 0
        for item in history:
            max_w = max(max_w, len(item.get("weights", [])))
        headers = ["iteracion", "mse"] + [f"w{i+1}" for i in range(max_w)]
        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(headers)
                for item in history:
                    row = [item.get("iteration", 0), item.get("mse", 0.0)]
                    weights = item.get("weights", [])
                    row += [f"{wval:.6f}" for wval in weights] + [""] * (max_w - len(weights))
                    w.writerow(row)
            messagebox.showinfo("PSO", f"Historial guardado en\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    
    def show_pso_history_dialog(self):
        """Abre el diálogo de evolución PSO externo."""
        history = self._last_pso_history
        if not history:
            messagebox.showwarning("PSO", "No hay historial disponible. Entrena primero.")
            return
        PSOHistoryDialog(
            self.root,
            history,
            self.map_obj,
            apply_callback=None, 
            save_history_callback=self._save_pso_best_history_csv,
        ).show()


    def open_evaluation_dialog(self):
        """Abre el diálogo de evaluación (MSE y métricas)."""
        from algorithms.run_fcm import InferenceType
        norm = self.fcm_runner.saturation_type if self.fcm_runner else NormalizationType.RELU
        inference = self.fcm_runner.inference_type if self.fcm_runner else InferenceType.KOSKO_RESCALED
        iterations = self.fcm_runner.get_max_iterations() if self.fcm_runner else 10
        from .dialogs.evaluation_dialog import EvaluationDialog as _Eval
        _Eval(self.root, self.map_obj, normalization=norm, inference=inference, iterations=iterations)
