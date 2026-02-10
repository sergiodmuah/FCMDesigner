# map_model/relation.py
"""
Implementación de relaciones causales entre conceptos
Migrado desde Relation.java
"""

import math
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .concept import Concept


class Relation:
    """Representa una relación causal entre dos conceptos"""
    
    # Contador de IDs para relaciones
    _relation_id_counter = 0
    
    def __init__(self, initial_concept: 'Concept', final_concept: 'Concept', dynamic: bool = False):
        # Generar ID único
        self.identifier = Relation._relation_id_counter
        Relation._relation_id_counter += 1
        
        # Conceptos conectados
        self.initial_concept = initial_concept
        self.final_concept = final_concept
        
        # Propiedades de la relación
        self.value = 1.0
        self.dynamic = dynamic
        self.approximation_percentage = 0.8
        self.dynamic_input = 1.0
        
        # Metadatos
        self.comment = ""
        self.draw_point = [0, 0]
    
    def set_dynamic_input(self, dynamic_input: float):
        """Asigna la entrada dinámica"""
        self.dynamic_input = dynamic_input
    
    def get_dynamic_input(self) -> float:
        """Obtiene la entrada dinámica"""
        return self.dynamic_input
    
    def is_dynamic(self) -> bool:
        """Verifica si la relación es dinámica"""
        return self.dynamic
    
    def get_initial_concept(self) -> 'Concept':
        """Obtiene el concepto inicial"""
        return self.initial_concept
    
    def get_final_concept(self) -> 'Concept':
        """Obtiene el concepto final"""
        return self.final_concept
    
    def get_value(self) -> float:
        """Obtiene el valor de la relación"""
        return self.value
    
    def set_value(self, value: float):
        """Asigna el valor de la relación [-1, 1]"""
        self.value = max(-1.0, min(1.0, value))
    
    def get_approximation_percentage(self) -> float:
        """Obtiene el porcentaje de aproximación"""
        return self.approximation_percentage
    
    def set_approximation_percentage(self, percentage: float):
        """Asigna el porcentaje de aproximación [0, 1]"""
        self.approximation_percentage = max(0.0, min(1.0, percentage))
    
    def get_relation_id(self) -> int:
        """Obtiene el identificador de la relación"""
        return self.identifier
    
    def draw_relation(self, canvas):
        """Dibuja la relación en un canvas de tkinter"""
        # Obtener posiciones y radios
        init_pos = self.initial_concept.get_position()
        final_pos = self.final_concept.get_position()
        init_radius = self.initial_concept.get_radius()
        final_radius = self.final_concept.get_radius()

        # Centros de los círculos
        ci_x = init_pos[0] + init_radius
        ci_y = init_pos[1] + init_radius
        cf_x = final_pos[0] + final_radius
        cf_y = final_pos[1] + final_radius

        # Caso especial: auto-relación (self-loop)
        if self.initial_concept is self.final_concept:
            # Dibujo simplificado: línea horizontal dentro del nodo
            color = "red" if self.value < 0.0 else ("blue" if self.value > 0.0 else "gray")
            inner_margin = int(init_radius * 0.4)
            x_left = ci_x - (init_radius - inner_margin)
            x_right = ci_x + (init_radius - inner_margin)
            y_line = ci_y  # línea horizontal por el centro del nodo
            canvas.create_line(int(x_left), int(y_line), int(x_right), int(y_line), fill=color, width=2, tags="relation")
            # Posición de etiqueta ligeramente arriba de la línea
            self.draw_point = [ci_x, y_line - init_radius // 2]
            value_text = f"{self.value:.3f}"
            canvas.create_text(self.draw_point[0], self.draw_point[1], 
                              text=value_text, fill=color, font=("Arial", 8), tags="relation")
            return

        # Vector de inicio a fin y ángulo
        vx = cf_x - ci_x
        vy = cf_y - ci_y
        angle = math.atan2(vy, vx)

        # Puntos en los bordes de los círculos (desde centro hacia el otro nodo)
        pi_x = int(ci_x + init_radius * math.cos(angle))
        pi_y = int(ci_y + init_radius * math.sin(angle))
        pf_x = int(cf_x - final_radius * math.cos(angle))
        pf_y = int(cf_y - final_radius * math.sin(angle))

        # Dibujar línea principal desde borde a borde
        canvas.create_line(pi_x, pi_y, pf_x, pf_y, fill="black", tags="relation")
        
        # Calcular posición de la etiqueta
        x_diff = abs(pi_x - pf_x) * self.approximation_percentage
        if pi_x < pf_x:
            xd = pi_x + x_diff
        else:
            xd = pi_x - x_diff
        
        if pi_x == pf_x:
            y_diff = abs(pi_y - pf_y) * self.approximation_percentage
            if pi_y < pf_y:
                yd = pi_y + y_diff
            else:
                yd = pi_y - y_diff
        else:
            yd = ((pf_y - pi_y) / (pf_x - pi_x)) * xd + (pf_x * pi_y - pi_x * pf_y) / (pf_x - pi_x)
        
        self.draw_point = [int(xd), int(yd)]
        
        # Preparar texto del valor
        display_value = self.value
        value_text = f"{display_value:.3f}"
        
        # Determinar color según el valor
        if self.value < 0.0:
            color = "red"
        elif self.value > 0.0:
            color = "blue"
        else:
            color = "gray"
        
        # Dibujar flecha (punta en pf_*)
        arrow_length = 12.0
        arrow_angle = math.pi / 6.0

        ax1 = pf_x - arrow_length * math.cos(angle - arrow_angle)
        ay1 = pf_y - arrow_length * math.sin(angle - arrow_angle)
        ax2 = pf_x - arrow_length * math.cos(angle + arrow_angle)
        ay2 = pf_y - arrow_length * math.sin(angle + arrow_angle)

        canvas.create_line(pf_x, pf_y, int(ax1), int(ay1), fill=color, width=2, tags="relation")
        canvas.create_line(pf_x, pf_y, int(ax2), int(ay2), fill=color, width=2, tags="relation")
        
        # Dibujar etiqueta de valor
        canvas.create_text(self.draw_point[0], self.draw_point[1], 
                          text=value_text, fill=color, font=("Arial", 8), tags="relation")
    
    def is_inside(self, x: int, y: int) -> bool:
        """Verifica si un punto está dentro del área de la etiqueta"""
        margin = 15
        return (self.draw_point[0] - margin <= x <= self.draw_point[0] + margin and
                self.draw_point[1] - margin <= y <= self.draw_point[1] + margin)
    
    def set_comment(self, comment: str):
        """Asigna un comentario a la relación"""
        self.comment = comment.replace('\n', '&').replace('\r', ' ')
    
    def get_comment(self) -> str:
        """Obtiene el comentario de la relación"""
        return self.comment.replace('&', '\n')

