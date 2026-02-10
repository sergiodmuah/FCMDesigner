# algorithms/rules.py
"""
Implementación de reglas de lógica difusa para mapas dinámicos
Migrado desde Rules.java
"""

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map_model.relation import Relation


class Rules:
    """Maneja las reglas de lógica difusa para mapas cognitivos dinámicos"""
    
    @staticmethod
    def is_high(v: float) -> bool:
        """Determina si un valor es alto (> 2/3)"""
        return v > 2.0/3.0
    
    @staticmethod
    def is_low(v: float) -> bool:
        """Determina si un valor es bajo (≤ 1/3)"""
        return v <= 1.0/3.0
    
    @staticmethod
    def is_medium(v: float) -> bool:
        """Determina si un valor es medio (1/3, 2/3]"""
        return 1.0/3.0 < v <= 2.0/3.0
    
    @staticmethod
    def compute_relation_value(relation: 'Relation') -> float:
        """Calcula el valor de una relación según las reglas específicas"""
        initial_name = relation.get_initial_concept().get_name()
        final_name = relation.get_final_concept().get_name()
        
        if initial_name == "b/A" and final_name == "H":
            relation.set_value(relation.get_dynamic_input())
        elif initial_name == "a/A" and final_name == "H":
            final_value = relation.get_final_concept().get_current_value()
            relation.set_value(-1.0 * math.sqrt(max(0, final_value)))
        else:
            relation.set_value(1.0)
        
        # Aplicar entrada dinámica
        current_value = relation.get_value()
        dynamic_input = relation.get_dynamic_input()
        relation.set_value(current_value * dynamic_input)
        
        return relation.get_value()
