# interface/__init__.py
"""
Paquete de interfaz gráfica para FCM Designer
"""

from .map_canvas import MapCanvas, MouseMode
from .map_window import MapWindow

__all__ = ['MapCanvas', 'MouseMode', 'MapWindow']
