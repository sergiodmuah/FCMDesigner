"""
Simulador de FCM sin interfaz gráfica para entrenamiento/evaluación.

Este módulo replica el núcleo numérico de `RunFCM` sin dependencias de GUI,
permitiendo evaluar un vector/matriz de pesos sobre activaciones iniciales y
obtener la activación del concepto objetivo tras un número fijo de
iteraciones.
"""

from __future__ import annotations

from typing import Dict, Sequence

from map_model.map import Map
from map_model.concept import Concept
from map_model.relation import Relation
from algorithms.run_fcm import NormalizationType, InferenceType


class FCMSimulator:
    """Simulador numérico de un mapa FCM independiente de tkinter.

    Uso:
      - Proporciona una instancia `Map` con la estructura (conceptos y
        relaciones) ya creada. El simulador no muta la estructura, solo los
        valores de las relaciones y activaciones de conceptos.
      - Usa `set_weights_flat` para inyectar un vector plano de pesos en el
        mismo orden que `map.get_relation_list()`.
      - Llama a `run_once` con los estados iniciales para obtener la
        activación del objetivo.
    """

    def __init__(
        self,
        map_obj: Map,
        normalization: NormalizationType = NormalizationType.RELU,
        inference: InferenceType = InferenceType.KOSKO_RESCALED
    ):
        self.map = map_obj
        self.normalization = normalization
        self.inference = inference

    def set_weights_flat(self, weights: Sequence[float]) -> None:
        if len(weights) != len(self.map.get_relation_list()):
            raise ValueError("weights size must match number of relations")
        for w, relation in zip(weights, self.map.get_relation_list()):
            relation.set_value(float(w))

    def _normalize(self, y: float) -> float:
        import math
        if self.normalization == NormalizationType.BISTATE:
            return 0.0 if y <= 0.5 else 1.0
        if self.normalization == NormalizationType.TRISTATE:
            if y <= 1.0 / 3.0:
                return 0.0
            elif y <= 2.0 / 3.0:
                return 0.5
            return 1.0
        if self.normalization == NormalizationType.SY:
            # Sigmoide alrededor de 0.5
            try:
                return 1.0 / (1.0 + math.exp(-9.0 * (y - 0.5)))
            except OverflowError:
                return 1.0 if y > 0.5 else 0.0
        if self.normalization == NormalizationType.TANH:
            # Tanh escalada a [0,1]: 0.5 * tanh(2*x) + 0.5
            return 0.5 * math.tanh(2.0 * y) + 0.5
        if self.normalization == NormalizationType.SIGMOID:
            # Sigmoid suave: 1/(1+exp(-0.5*x))
            try:
                return 1.0 / (1.0 + math.exp(-0.5 * y))
            except OverflowError:
                return 1.0 if y > 0 else 0.0
        if self.normalization == NormalizationType.LINEAR:
            # Lineal saturada: clip(x, 0, 1)
            if y < 0.0:
                return 0.0
            if y > 1.0:
                return 1.0
            return y
        if self.normalization == NormalizationType.RELU:
            # ReLU limitada: clip(x, 0, 1)
            if y < 0.0:
                return 0.0
            if y > 1.0:
                return 1.0
            return y
        # SYC saturation (default)
        if y < 0.0:
            return 0.0
        if y > 1.0:
            return 1.0
        return y

    def run_once(
        self,
        initial_states: Dict[str, float],
        target_concept_name: str,
        iterations: int = 10,
    ) -> float:
        """Ejecuta el mapa un número fijo de iteraciones y devuelve el objetivo.

        - initial_states: mapeo nombre -> activación inicial en [0,1]
        - target_concept_name: nombre del concepto cuyo valor final se lee
        - iterations: número de pasos de propagación (>=1)
        """

        # Inicializar conceptos (guardando y restaurando estado para no mutar el mapa)
        name_to_concept: Dict[str, Concept] = {c.get_name(): c for c in self.map.get_concept_list()}
        saved_state = []
        for concept in self.map.get_concept_list():
            saved_state.append(
                (
                    concept.get_current_value(),
                    concept.auxiliary_value,
                    list(concept.values_history),
                )
            )
            # Obtener valor inicial, asegurando que sea numérico
            concept_name = concept.get_name()
            init_val = initial_states.get(concept_name, concept.get_initial_value())
            if not isinstance(init_val, (int, float)):
                init_val = float(init_val)
            # Usar valor inicial temporal sin tocar initial_value
            concept.set_current_value(init_val)
            concept.values_history = [init_val]
            # Asegurar que auxiliary_value esté inicializado a 0.0
            concept.auxiliary_value = 0.0

        # Ejecutar iteraciones
        for _ in range(max(1, iterations)):
            # Acumular según tipo de inferencia
            for relation in self.map.get_relation_list():
                initial_value = relation.get_initial_concept().get_last_value()
                final_concept = relation.get_final_concept()
                
                if self.inference == InferenceType.KOSKO_RESCALED:
                    # Ecuación 8: reescalar entrada a [-1,1]
                    rescaled_input = 2.0 * initial_value - 1.0
                    final_concept.auxiliary_value += rescaled_input * relation.get_value()
                else:
                    # Ecuación estándar o con memoria
                    final_concept.auxiliary_value += initial_value * relation.get_value()

            # Actualizar con normalización
            for concept in self.map.get_concept_list():
                # Agregar memoria según tipo de inferencia
                if self.inference == InferenceType.KOSKO_MEMORY:
                    # Ecuación 7: agregar A_i^(t)
                    concept.auxiliary_value += concept.get_last_value()
                elif self.inference == InferenceType.KOSKO_RESCALED:
                    # Ecuación 8: agregar (2*A_i^(t) - 1)
                    concept.auxiliary_value += 2.0 * concept.get_last_value() - 1.0
                
                normalized = self._normalize(concept.auxiliary_value)
                concept.add_last_value(normalized)
                concept.set_current_value(concept.get_last_value())
                concept.auxiliary_value = 0.0

        target = name_to_concept.get(target_concept_name)
        if target is None:
            # Restaurar antes de fallar
            for concept, state in zip(self.map.get_concept_list(), saved_state):
                concept.set_current_value(state[0])
                concept.auxiliary_value = state[1]
                concept.values_history = state[2]
            raise ValueError(f"Target concept '{target_concept_name}' not found in map")

        result = float(target.get_last_value())

        # Restaurar estado original del mapa (no mutante)
        for concept, state in zip(self.map.get_concept_list(), saved_state):
            concept.set_current_value(state[0])
            concept.auxiliary_value = state[1]
            concept.values_history = state[2]

        return result
    


