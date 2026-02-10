# interface/map_canvas.py
"""
Canvas principal para renderizado e interacción con mapas
"""

import tkinter as tk
from enum import IntEnum
from typing import Optional, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from map_model.map import Map
    from map_model.concept import Concept


class MouseMode(IntEnum):
    """Modos de interacción del ratón"""
    CREATE_CONCEPTS = 0
    CREATE_RELATIONS = 1
    SELECT_CONCEPTS = 2
    SELECT_RELATIONS = 3
    DELETE_CONCEPTS = 4
    DELETE_RELATIONS = 5


class MapCanvas(tk.Canvas):
    """Canvas principal para renderizado e interacción con mapas"""
    
    def __init__(self, parent, map_obj: 'Map', **kwargs):
        super().__init__(parent, bg="white", **kwargs)
        
        self.map_obj = map_obj
        self.mouse_mode = MouseMode.CREATE_CONCEPTS
        self.draw_proportionally = False
        
        # Estado para creación de relaciones
        self.creating_relation = False
        self.starting_concept: Optional['Concept'] = None
        self.mouse_point = [0, 0]
        
        # Estado para arrastrar conceptos
        self.dragging_concept: Optional['Concept'] = None
        self.drag_offset = (0, 0)  # desplazamiento cursor -> esquina superior izda del concepto
        
        # Configurar eventos
        self.bind("<Button-1>", self.on_left_click)
        self.bind("<Button-3>", self.on_right_click)
        self.bind("<Motion>", self.on_mouse_move)
        self.bind("<B1-Motion>", self.on_mouse_drag)
        self.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.bind("<Leave>", self.on_mouse_leave)

        
        # Configurar para recibir focus
        self.focus_set()
        
    def get_map(self) -> 'Map':
        """Obtiene el mapa asociado"""
        return self.map_obj
    
    def set_mouse_mode(self, mode: MouseMode):
        """Establece el modo del ratón"""
        self.mouse_mode = mode
        if mode != MouseMode.CREATE_RELATIONS:
            self.cancel_relation_creation()
    
    def get_mouse_mode(self) -> MouseMode:
        """Obtiene el modo actual del ratón"""
        return self.mouse_mode
    
    def cancel_relation_creation(self):
        """Cancela la creación de relación en progreso"""
        if self.creating_relation:
            self.creating_relation = False
            self.starting_concept = None
            self.repaint()
    
    def repaint(self):
        """Redibuja el canvas"""
        self.delete("all")
        
        # Dibujar el mapa
        self.map_obj.draw_map(self, self.draw_proportionally)
        
        # Dibujar línea temporal para relación en creación
        if self.creating_relation and self.starting_concept:
            self.draw_temp_relation()
    
    def draw_temp_relation(self):
        """Dibuja la línea temporal durante creación de relación"""
        if not self.starting_concept:
            return
            
        start_pos = self.starting_concept.get_position()
        start_radius = self.starting_concept.get_radius()
        
        # Calcular punto de inicio de la línea
        dx = start_pos[0] - self.mouse_point[0]
        dy = start_pos[1] - self.mouse_point[1]
        angle = math.atan2(dy, dx)
        
        start_x = int(start_pos[0] - start_radius * math.cos(angle) + start_radius)
        start_y = int(start_pos[1] - start_radius * math.sin(angle) + start_radius)
        
        # Dibujar línea temporal
        self.create_line(
            start_x, start_y, 
            self.mouse_point[0], self.mouse_point[1],
            fill="gray", dash=(5, 5), tags="temp"
        )
    
    def on_left_click(self, event):
        """Maneja clics izquierdos"""
        # Convertir a coordenadas del canvas (importante con scroll/scrollregion)
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        
        if self.mouse_mode == MouseMode.CREATE_CONCEPTS:
            # Si clicamos sobre un concepto, iniciamos arrastre; si no, creamos uno nuevo
            concept = self.map_obj.find_concept(x, y)
            if concept:
                self.dragging_concept = concept
                pos_x, pos_y = concept.get_position()
                self.drag_offset = (x - pos_x, y - pos_y)
            else:
                self.create_concept(x, y)
            
        elif self.mouse_mode == MouseMode.CREATE_RELATIONS:
            self.handle_relation_creation(x, y)
            
        elif self.mouse_mode == MouseMode.SELECT_CONCEPTS:
            # Iniciar arrastre si se hace clic sobre un concepto
            self.dragging_concept = self.map_obj.find_concept(x, y)
            if self.dragging_concept:
                # No movemos aún; el movimiento se hará en <B1-Motion>
                # Guardamos offset por si se requiere, pero priorizaremos restar radio como en Java
                pos_x, pos_y = self.dragging_concept.get_position()
                self.drag_offset = (x - pos_x, y - pos_y)

        elif self.mouse_mode == MouseMode.DELETE_CONCEPTS:
            self.delete_concept_at(x, y)
            
        elif self.mouse_mode == MouseMode.DELETE_RELATIONS:
            self.delete_relation_at(x, y)
    
    def on_right_click(self, event):
        """Maneja clics derechos (opciones)"""
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        
        if self.mouse_mode in [MouseMode.SELECT_CONCEPTS, MouseMode.CREATE_CONCEPTS]:
            concept = self.map_obj.find_concept(x, y)
            if concept:
                self.show_concept_options(concept, event)
                
        elif self.mouse_mode in [MouseMode.SELECT_RELATIONS, MouseMode.CREATE_RELATIONS]:
            relation = self.map_obj.find_relation(x, y)
            if relation:
                self.show_relation_options(relation, event)
    
    def on_mouse_move(self, event):
        """Maneja movimiento del ratón"""
        self.mouse_point = [self.canvasx(event.x), self.canvasy(event.y)]
        
        if self.creating_relation:
            self.repaint()
            # Si movemos fuera de cualquier concepto, podemos mostrar una guía temporal
    
    def on_mouse_drag(self, event):
        """Maneja arrastre del ratón"""
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        if self.mouse_mode in (MouseMode.SELECT_CONCEPTS, MouseMode.CREATE_CONCEPTS):
            if not self.dragging_concept:
                self.dragging_concept = self.map_obj.find_concept(x, y)
            if self.dragging_concept:
                # Replicar lógica Java: posicionar por centro restando radio
                radius = self.dragging_concept.get_radius()
                new_x = int(x - radius)
                new_y = int(y - radius)
                self.dragging_concept.set_position(new_x, new_y)
                self.repaint()
    
    def on_mouse_release(self, event):
        """Maneja liberación del ratón"""
        self.dragging_concept = None
        self.drag_offset = (0, 0)
    
    def on_mouse_leave(self, event):
        """Maneja salida del ratón del canvas"""
        self.dragging_concept = None
        self.cancel_relation_creation()
    
    def create_concept(self, x: int, y: int):
        """Crea un nuevo concepto"""
        self.map_obj.add_concept(x, y)
        self.repaint()
        # Notificar cambios al mapa (actualizar panel/info y reset de simulación)
        try:
            self.event_generate("<<MapChanged>>", when="tail")
        except Exception:
            pass
    
    def handle_relation_creation(self, x: int, y: int):
        """Maneja la creación de relaciones"""
        concept = self.map_obj.find_concept(x, y)
        
        if concept and not self.creating_relation:
            # Iniciar creación de relación
            self.starting_concept = concept
            self.creating_relation = True
            
        elif concept and self.creating_relation:
            # Completar relación
            # Permitir auto-relaciones (self-loop) y relaciones normales
            self.map_obj.add_relation(self.starting_concept, concept)
            self.cancel_relation_creation()
            self.repaint()
            # Notificar cambio estructural
            try:
                self.event_generate("<<MapChanged>>", when="tail")
            except Exception:
                pass
    
    def delete_concept_at(self, x: int, y: int):
        """Elimina concepto en la posición especificada"""
        concept = self.map_obj.find_concept(x, y)
        if concept:
            self.map_obj.delete_concept(concept)
            self.repaint()
            try:
                self.event_generate("<<MapChanged>>", when="tail")
            except Exception:
                pass
    
    def delete_relation_at(self, x: int, y: int):
        """Elimina relación en la posición especificada"""
        relation = self.map_obj.find_relation(x, y)
        if relation:
            self.map_obj.delete_relation(relation)
            self.repaint()
            try:
                self.event_generate("<<MapChanged>>", when="tail")
            except Exception:
                pass
    
    def show_concept_options(self, concept, event):
        """Muestra opciones de concepto"""
        from .dialogs.concept_dialog import ConceptDialog
        dialog = ConceptDialog(self, concept)
        dialog.show(event.x_root, event.y_root)
    
    def show_relation_options(self, relation, event):
        """Muestra opciones de relación"""
        from .dialogs.relation_dialog import RelationDialog
        dialog = RelationDialog(self, relation)
        dialog.show(event.x_root, event.y_root)