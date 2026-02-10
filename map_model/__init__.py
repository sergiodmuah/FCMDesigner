# map_model/__init__.py
"""
Paquete del modelo de datos para mapas cognitivos
Contiene las clases principales para conceptos, relaciones y mapas
"""

from .concept import Concept, LabelPosition
from .relation import Relation
from .map import Map

__all__ = ['Concept', 'LabelPosition', 'Relation', 'Map']
