#interface/dialogs/concept_dialog.py
"""
Diálogo de opciones para conceptos
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map_model.concept import Concept, LabelPosition
    from interface.map_canvas import MapCanvas


class ConceptDialog:
    """Diálogo para editar propiedades de conceptos"""
    
    def __init__(self, parent_canvas: 'MapCanvas', concept: 'Concept'):
        self.parent_canvas = parent_canvas
        self.concept = concept
        self.dialog = None
    
    def show(self, x: int, y: int):
        """Muestra el diálogo en la posición especificada"""
        self.dialog = tk.Toplevel()
        self.dialog.title(f"Opciones - {self.concept.get_name()}")
        self.dialog.geometry("420x520")
        self.dialog.minsize(380, 460)
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent_canvas.winfo_toplevel())
        
        # Posicionar cerca del cursor
        self.dialog.geometry(f"+{x+10}+{y+10}")
        
        self.setup_interface()
        # Atajos: Enter = Aceptar, Escape = Cancelar
        self.dialog.bind("<Return>", lambda e: self.accept())
        self.dialog.bind("<Escape>", lambda e: self.cancel())
        
    def setup_interface(self):
        """Configura la interfaz del diálogo"""
        # Frame principal
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Nombre
        ttk.Label(main_frame, text="Nombre:").pack(anchor=tk.W)
        self.name_entry = ttk.Entry(main_frame, width=30)
        self.name_entry.pack(fill=tk.X, pady=(0, 10))
        self.name_entry.insert(0, self.concept.get_name())
        
        # Valor inicial (etiqueta + botones 0/1 en la misma línea)
        init_header = ttk.Frame(main_frame)
        init_header.pack(fill=tk.X)
        ttk.Label(init_header, text="Valor inicial (0-1):").pack(side=tk.LEFT)
        ttk.Button(init_header, text="0", width=3, command=lambda: self._set_init_value(0.0)).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(init_header, text="1", width=3, command=lambda: self._set_init_value(1.0)).pack(side=tk.RIGHT)
        # Campo de entrada debajo
        init_row = ttk.Frame(main_frame)
        init_row.pack(fill=tk.X, pady=(2, 10))
        self.value_entry = ttk.Entry(init_row, width=30)
        self.value_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.value_entry.insert(0, str(self.concept.get_initial_value()))
        
        # Valor actual (según iteración mostrada)
        ttk.Label(main_frame, text=f"Valor actual: {self.concept.get_current_value():.6f}").pack(anchor=tk.W, pady=(0, 10))

        # Posición de etiqueta
        ttk.Label(main_frame, text="Posición de etiqueta:").pack(anchor=tk.W)
        self.label_pos_var = tk.StringVar()
        
        pos_frame = ttk.Frame(main_frame)
        pos_frame.pack(fill=tk.X, pady=(0, 10))
        
        positions = [("Arriba", "0"), ("Derecha", "1"), ("Abajo", "2"), ("Izquierda", "3")]
        current_pos = str(self.concept.get_label_position())
        
        for text, value in positions:
            ttk.Radiobutton(
                pos_frame, 
                text=text, 
                variable=self.label_pos_var,
                value=value,
            ).pack(anchor=tk.W)
        
        self.label_pos_var.set(current_pos)
        
        # Comentario
        ttk.Label(main_frame, text="Comentario:").pack(anchor=tk.W)
        
        comment_frame = ttk.Frame(main_frame)
        comment_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.comment_text = tk.Text(comment_frame, height=6, width=30)
        comment_scroll = ttk.Scrollbar(comment_frame, orient=tk.VERTICAL, command=self.comment_text.yview)
        self.comment_text.configure(yscrollcommand=comment_scroll.set)
        
        self.comment_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        comment_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.comment_text.insert("1.0", self.concept.get_comment())
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Aceptar", command=self.accept).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=self.cancel).pack(side=tk.RIGHT)
    
    def accept(self):
        """Valida y aplica los cambios al pulsar Aceptar."""
        try:
            # Nombre
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "El nombre no puede estar vacío")
                return
            # Valor inicial
            try:
                value = float(self.value_entry.get())
            except ValueError:
                messagebox.showerror("Error", "El valor inicial debe estar entre 0 y 1")
                return
            if not (0 <= value <= 1):
                messagebox.showerror("Error", "El valor inicial debe estar entre 0 y 1")
                return
            # Posición etiqueta
            try:
                pos = int(self.label_pos_var.get())
            except ValueError:
                messagebox.showerror("Error", "La posición de etiqueta es inválida")
                return
            # Comentario
            comment = self.comment_text.get("1.0", tk.END).strip()

            # Aplicar al modelo
            self.concept.set_name(name)
            self.concept.set_initial_value(value)
            self.concept.set_current_value(value)
            self.concept.set_label_position(pos)
            self.concept.set_comment(comment)

            # Repintar
            self.parent_canvas.repaint()

            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron aplicar los cambios: {e}")

    def cancel(self):
        """Cierra sin aplicar cambios."""
        try:
            self.dialog.destroy()
        except Exception:
            pass

    def _set_init_value(self, value: float):
        """Actualiza el campo de valor inicial sin aplicar cambios al modelo."""
        try:
            self.value_entry.delete(0, tk.END)
            self.value_entry.insert(0, str(float(value)))
        except Exception:
            pass