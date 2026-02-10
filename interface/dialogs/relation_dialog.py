#interface/dialogs/relation_dialog.py
"""
Diálogo de opciones para relaciones
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map_model.relation import Relation
    from interface.map_canvas import MapCanvas


class RelationDialog:
    """Diálogo para editar propiedades de relaciones"""
    
    def __init__(self, parent_canvas: 'MapCanvas', relation: 'Relation'):
        self.parent_canvas = parent_canvas
        self.relation = relation
        self.dialog = None
    
    def show(self, x: int, y: int):
        """Muestra el diálogo en la posición especificada"""
        self.dialog = tk.Toplevel()
        
        initial_name = self.relation.get_initial_concept().get_name()
        final_name = self.relation.get_final_concept().get_name()
        self.dialog.title(f"Relación: {initial_name} → {final_name}")
        
        self.dialog.geometry("420x420")
        self.dialog.minsize(380, 380)
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
        
        # Información de la relación
        info_frame = ttk.LabelFrame(main_frame, text="Información", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        initial_name = self.relation.get_initial_concept().get_name()
        final_name = self.relation.get_final_concept().get_name()
        
        ttk.Label(info_frame, text=f"Desde: {initial_name}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Hacia: {final_name}").pack(anchor=tk.W)
        
        # Valor de la relación
        ttk.Label(main_frame, text="Valor de la relación (-1 a 1):").pack(anchor=tk.W)
        self.value_entry = ttk.Entry(main_frame, width=30)
        self.value_entry.pack(fill=tk.X, pady=(0, 10))
        self.value_entry.insert(0, str(self.relation.get_value()))
        
        # Entrada dinámica (solo para mapas dinámicos)
        if self.relation.is_dynamic():
            ttk.Label(main_frame, text="Entrada dinámica:").pack(anchor=tk.W)
            self.dynamic_entry = ttk.Entry(main_frame, width=30)
            self.dynamic_entry.pack(fill=tk.X, pady=(0, 10))
            self.dynamic_entry.insert(0, str(self.relation.get_dynamic_input()))
        
        # Posición de etiqueta
        ttk.Label(main_frame, text="Posición de etiqueta (0-1):").pack(anchor=tk.W)
        self.position_entry = ttk.Entry(main_frame, width=30)
        self.position_entry.pack(fill=tk.X, pady=(0, 10))
        self.position_entry.insert(0, str(self.relation.get_approximation_percentage()))
        
        # Comentario
        ttk.Label(main_frame, text="Comentario:").pack(anchor=tk.W)
        
        comment_frame = ttk.Frame(main_frame)
        comment_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.comment_text = tk.Text(comment_frame, height=4, width=30)
        comment_scroll = ttk.Scrollbar(comment_frame, orient=tk.VERTICAL, command=self.comment_text.yview)
        self.comment_text.configure(yscrollcommand=comment_scroll.set)
        
        self.comment_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        comment_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.comment_text.insert("1.0", self.relation.get_comment())
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Aceptar", command=self.accept).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=self.cancel).pack(side=tk.RIGHT)
    
    def accept(self):
        """Aplica los cambios y cierra el diálogo"""
        try:
            # Validar y aplicar valor de relación
            try:
                value = float(self.value_entry.get())
                self.relation.set_value(value)
            except ValueError:
                messagebox.showerror("Error", "El valor debe ser un número entre -1 y 1")
                return
            
            # Aplicar entrada dinámica si existe
            if hasattr(self, 'dynamic_entry'):
                try:
                    dynamic_value = float(self.dynamic_entry.get())
                    self.relation.set_dynamic_input(dynamic_value)
                except ValueError:
                    messagebox.showerror("Error", "La entrada dinámica debe ser un número")
                    return
            
            # Validar y aplicar posición de etiqueta
            try:
                position = float(self.position_entry.get())
                self.relation.set_approximation_percentage(position)
            except ValueError:
                messagebox.showerror("Error", "La posición debe ser un número entre 0 y 1")
                return
            
            # Aplicar comentario
            comment = self.comment_text.get("1.0", tk.END).strip()
            self.relation.set_comment(comment)
            
            # Repintar canvas
            self.parent_canvas.repaint()
            
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al aplicar cambios: {e}")
    
    def cancel(self):
        """Cancela sin aplicar cambios"""
        self.dialog.destroy()