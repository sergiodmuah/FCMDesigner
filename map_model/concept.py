# map_model/concept.py
"""
Implementación de conceptos (nodos) para mapas cognitivos
Migrado desde Concept.java
"""

from typing import List, Tuple, Optional
from enum import IntEnum


class LabelPosition(IntEnum):
    """Posiciones de etiqueta para los conceptos"""
    TOP = 0      # ARRIBA
    RIGHT = 1    # RSIDE  
    BOTTOM = 2   # ABAJO
    LEFT = 3     # LSIDE


class Concept:
    """Representa un concepto (nodo) en el mapa cognitivo"""
    
    # Variable de clase para generar IDs únicos
    _node_id_counter = 0
    MAX_SIZE = 20
    
    def __init__(self, x: int, y: int, dynamic: bool = False):
        # Generar ID único
        self.identifier = Concept._node_id_counter
        Concept._node_id_counter += 1
        
        # Propiedades de posición y visualización
        self.position = [x, y]
        self.radius = 10
        self.label_position = LabelPosition.LEFT
        
        # Propiedades del concepto
        self.name = f"Node {self.identifier}"
        self.current_value = 1.0
        self.initial_value = self.current_value
        self.auxiliary_value = 0.0
        
        # Historia de valores
        self.values_history: List[float] = [self.initial_value]
        
        # Metadatos
        self.comment = ""
        self.dynamic = dynamic
    
    def set_name(self, name: str):
        """Asigna el nombre al concepto"""
        self.name = name
    
    def get_name(self) -> str:
        """Obtiene el nombre del concepto"""
        return self.name
    
    def get_last_value(self) -> float:
        """Retorna el último valor en la historia"""
        return self.values_history[-1] if self.values_history else 0.0
    
    def add_last_value(self, value: float):
        """Agrega un valor al final de la historia"""
        self.values_history.append(value)
        self.current_value = value
    
    def set_label_position(self, position: int):
        """Asigna la posición de la etiqueta"""
        if position in [pos.value for pos in LabelPosition]:
            self.label_position = LabelPosition(position)
        else:
            self.label_position = LabelPosition.TOP
    
    def get_label_position(self) -> int:
        """Obtiene la posición de la etiqueta"""
        return self.label_position.value
    
    def get_position(self) -> Tuple[int, int]:
        """Obtiene la posición del concepto"""
        return tuple(self.position)
    
    def set_position(self, x: int, y: int):
        """Asigna la posición del concepto con validación de límites"""
        self.position[0] = max(0, min(x, 1024 - 2 * self.radius))
        self.position[1] = max(0, min(y, 1024 - 2 * self.radius))
    
    def set_radius(self, radius: int):
        """Asigna el radio del concepto"""
        if 5 <= radius <= self.MAX_SIZE + 5:
            self.radius = radius
    
    def get_radius(self) -> int:
        """Obtiene el radio del concepto"""
        return self.radius
    
    def set_id(self, identifier: int):
        """Asigna el identificador (uso interno)"""
        self.identifier = identifier
    
    def get_concept_id(self) -> int:
        """Obtiene el identificador del concepto"""
        return self.identifier
    
    def set_initial_value(self, value: float):
        """Asigna el valor inicial y reinicia la historia"""
        # Validar rango [0,1]
        self.initial_value = max(0.0, min(1.0, value))
        
        # Reiniciar historia de valores
        self.values_history.clear()
        self.values_history.append(self.initial_value)
        self.current_value = self.initial_value
    
    def get_initial_value(self) -> float:
        """Obtiene el valor inicial"""
        return self.initial_value
    
    def set_current_value(self, value: float):
        """Asigna el valor actual (sin modificar historia)"""
        self.current_value = max(0.0, min(1.0, value))
    
    def get_current_value(self) -> float:
        """Obtiene el valor actual"""
        return self.current_value
    
    def is_inside(self, x: int, y: int) -> bool:
        """Verifica si un punto está dentro del concepto"""
        size = 2 * self.radius
        return (self.position[0] <= x <= self.position[0] + size and
                self.position[1] <= y <= self.position[1] + size)
    
    def draw_concept(self, canvas, with_value: bool = True):
        """Dibuja el concepto en un canvas de tkinter"""
        # Calcular tamaño
        if with_value:
            size = round((5 + self.MAX_SIZE * self.current_value) * 2)
        else:
            size = 20
        
        self.radius = size // 2
        
        # Coordenadas del círculo
        x1, y1 = self.position[0], self.position[1]
        x2, y2 = x1 + size, y1 + size
        
        # Dibujar círculo
        canvas.create_oval(x1, y1, x2, y2, outline="black", fill="white", tags="concept")
        
        # Calcular posición de etiqueta
        string_width = len(self.name) * 6
        center_x = x1 + self.radius
        center_y = y1 + self.radius
        
        if self.label_position == LabelPosition.BOTTOM:
            text_x = center_x
            text_y = y2 + 12
        elif self.label_position == LabelPosition.TOP:
            text_x = center_x
            text_y = y1 - 5
        elif self.label_position == LabelPosition.RIGHT:
            text_x = x2 + 5
            text_y = center_y
        else:  # LEFT
            text_x = x1 - 5
            text_y = center_y
        
        # Dibujar etiqueta
        anchor = "n" if self.label_position == LabelPosition.BOTTOM else \
                "s" if self.label_position == LabelPosition.TOP else \
                "w" if self.label_position == LabelPosition.RIGHT else "e"
        
        canvas.create_text(text_x, text_y, text=self.name, anchor=anchor, tags="concept")
    
    def reset(self):
        """Reinicia la historia de valores"""
        self.values_history.clear()
        self.values_history.append(self.initial_value)
        self.current_value = self.initial_value
    
    def get_values_size(self) -> int:
        """Obtiene el tamaño de la historia de valores"""
        return len(self.values_history)
    
    def set_current_iteration(self, iteration: int):
        """Establece la iteración actual a mostrar"""
        if 0 <= iteration < len(self.values_history):
            self.current_value = self.values_history[iteration]
    
    def get_value(self, iteration: int) -> float:
        """Obtiene el valor en una iteración específica"""
        if 0 <= iteration < len(self.values_history):
            return self.values_history[iteration]
        return 0.0
    
    def set_comment(self, comment: str):
        """Asigna un comentario al concepto"""
        self.comment = comment.replace('\n', '&').replace('\r', ' ')
    
    def get_comment(self) -> str:
        """Obtiene el comentario del concepto"""
        return self.comment.replace('&', '\n')

