"""
Paquete de entrenamiento para FCM Designer
Incluye cargador de datasets, simulador numérico y entrenador PSO.
"""

from .dataset import FCMDataset, Sample
from .simulator import FCMSimulator
from .pso_trainer import FCMPSOTrainer, PSOConfig

__all__ = [
    "FCMDataset",
    "Sample",
    "FCMSimulator",
    "FCMPSOTrainer",
    "PSOConfig",
]


