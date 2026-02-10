"""
Entrenador basado en PSO para aprender los pesos de relaciones en un FCM.

Dada una estructura `Map` y un dataset de pares (entradas -> objetivo), este
entrenador busca el vector de pesos que minimiza el error de predicción del
simulador sobre el concepto objetivo.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Sequence, Tuple, Dict, Any, Optional, Callable

from map_model.map import Map
from .dataset import FCMDataset
from .simulator import FCMSimulator
from algorithms.run_fcm import NormalizationType, InferenceType


def clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


@dataclass
class PSOConfig:
    swarm_size: int = 30
    iterations: int = 200
    inertia: float = 0.7
    cognitive: float = 1.5 #
    social: float = 1.5 #
    weight_min: float = -1.0
    weight_max: float = 1.0
    velocity_clamp: float = 0.2
    eval_iterations: int = 10  # iteraciones del simulador por muestra
    normalization: NormalizationType = NormalizationType.RELU
    inference: InferenceType = InferenceType.KOSKO_RESCALED


class FCMPSOTrainer:
    """Entrenador PSO (Particle Swarm Optimization) para pesos de FCM."""

    def __init__(self, map_obj: Map, target_concept_name: str, config: PSOConfig | None = None):
        self.map = map_obj
        self.target_concept_name = target_concept_name
        self.config = config or PSOConfig()
        self.num_weights = len(self.map.get_relation_list())
        self.sim = FCMSimulator(
            self.map, 
            normalization=self.config.normalization,
            inference=self.config.inference
        )
        # Historial del mejor individuo: lista de dicts con iteración, mse y pesos
        self.best_history: List[Dict[str, Any]] = []

    def _evaluate_weights(self, weights: Sequence[float], dataset: FCMDataset) -> float:
        """Evalúa MSE; si el dataset trae pesos (Sample.weight), usa MSE ponderado."""
        self.sim.set_weights_flat(weights)
        weighted_sum = 0.0
        weight_total = 0.0
        count_samples = 0
        for sample in dataset:
            y_pred = self.sim.run_once(
                initial_states=sample.features,
                target_concept_name=self.target_concept_name,
                iterations=self.config.eval_iterations,
            )
            err = y_pred - float(sample.target_value)
            w = getattr(sample, 'weight', 1.0) or 1.0
            weighted_sum += w * (err * err)
            weight_total += w
            count_samples += 1
        if weight_total > 0:
            return weighted_sum / weight_total
        # Fallback por si no hay pesos válidos
        return weighted_sum / max(1, count_samples)

    def fit(self, dataset: FCMDataset, progress_cb: Optional[Callable[[int, int], None]] = None) -> Tuple[List[float], float]:
        n = self.num_weights
        if n == 0:
            raise ValueError("Map has no relations; nothing to learn")

        rnd = random.Random(42)
        c = self.config

        # Inicializar enjambre
        swarm: List[List[float]] = [
            [rnd.uniform(c.weight_min, c.weight_max) for _ in range(n)] for _ in range(c.swarm_size)
        ]
        velocities: List[List[float]] = [
            [rnd.uniform(-abs(c.weight_max - c.weight_min), abs(c.weight_max - c.weight_min)) * 0.1 for _ in range(n)]
            for _ in range(c.swarm_size)
        ]

        personal_best = [w[:] for w in swarm]
        personal_best_score = [math.inf for _ in range(c.swarm_size)]

        global_best = swarm[0][:]
        global_best_score = math.inf

        # Evaluar enjambre inicial
        for i in range(c.swarm_size):
            score = self._evaluate_weights(swarm[i], dataset)
            personal_best_score[i] = score
            personal_best[i] = swarm[i][:]
            if score < global_best_score:
                global_best_score = score
                global_best = swarm[i][:]
        
        # Registrar estado inicial
        self.best_history.append({
            "iteration": 0,
            "mse": global_best_score,
            "weights": global_best[:],
        })

        # Bucle principal
        for it in range(c.iterations):
            if progress_cb is not None:
                try:
                    progress_cb(it + 1, c.iterations)
                except Exception:
                    pass
            for i in range(c.swarm_size):
                # Actualizar velocidad y posición
                for d in range(n):
                    r1 = rnd.random()
                    r2 = rnd.random()
                    cognitive_term = c.cognitive * r1 * (personal_best[i][d] - swarm[i][d])
                    social_term = c.social * r2 * (global_best[d] - swarm[i][d])
                    velocities[i][d] = (
                        c.inertia * velocities[i][d] + cognitive_term + social_term
                    )
                    # Limitar velocidad
                    velocities[i][d] = clamp(velocities[i][d], -c.velocity_clamp, c.velocity_clamp)
                    # Actualizar posición y limitar a rangos de peso
                    swarm[i][d] = clamp(swarm[i][d] + velocities[i][d], c.weight_min, c.weight_max)

                # Evaluar
                score = self._evaluate_weights(swarm[i], dataset)
                if score < personal_best_score[i]:
                    personal_best_score[i] = score
                    personal_best[i] = swarm[i][:]
                    if score < global_best_score:
                        global_best_score = score
                        global_best = swarm[i][:]
                        # Registrar mejora del mejor individuo
                        self.best_history.append({
                            "iteration": it,
                            "mse": global_best_score,
                            "weights": global_best[:],
                        })
            
            # Registrar cada 10 iteraciones para tener más puntos en el gráfico
            if (it + 1) % 10 == 0:
                self.best_history.append({
                    "iteration": it + 1,
                    "mse": global_best_score,
                    "weights": global_best[:],
                })

        # Devolver mejores pesos y su puntuación
        return global_best, global_best_score

    def get_best_history(self) -> List[Dict[str, Any]]:
        """Devuelve el historial de mejoras del mejor individuo.

        Cada elemento contiene: iteration (int), mse (float), weights (List[float]).
        """
        return self.best_history


