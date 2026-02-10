# algorithms/run_fcm.py
"""
Motor principal de ejecución de mapas cognitivos
Migrado desde RunFCM.java
"""

import threading
import time
import math
from enum import IntEnum
from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from interface.map_canvas import MapCanvas
    from tkinter import Button, Label

from .rules import Rules


class NormalizationType(IntEnum):
    """Tipos de normalización disponibles"""
    SY = 1
    SYC = 2
    TRISTATE = 3
    BISTATE = 4
    # Nuevas funciones robustas
    TANH = 5
    SIGMOID = 6
    LINEAR = 7
    RELU = 8


class InferenceType(IntEnum):
    """Tipos de función de inferencia disponibles"""
    KOSKO_STANDARD = 1      # A_i(t+1) = f(Σ w_ji * A_j(t))
    KOSKO_MEMORY = 2  # A_i(t+1) = f(Σ w_ji * A_j(t) + A_i(t))  - Ecuación 7
    KOSKO_RESCALED = 3  # A_i(t+1) = f(Σ w_ji * (2*A_j(t)-1) + (2*A_i(t)-1))  - Ecuación 8


class RunFCM:
    """Motor principal de ejecución de mapas cognitivos"""
    
    def __init__(self, map_canvas: 'MapCanvas', play_button: 'Button', iteration_label: 'Label', on_finish: Optional[Callable] = None):
        self.map_canvas = map_canvas
        self.play_button = play_button
        self.iteration_label = iteration_label
        self.on_finish = on_finish
        
        # Configuración de ejecución
        self.max_iterations = 10
        self.stop_on_stabilize = False
        self.saturation_type = NormalizationType.RELU
        self.inference_type = InferenceType.KOSKO_RESCALED
        self.delay = 0.0  # En segundos
        
        # Componentes
        self.rules = Rules()
        self.thread = None
        self._running = False
    
    def set_max_iterations(self, n: int):
        """Establece el número máximo de iteraciones"""
        if n >= 2:
            self.max_iterations = n
    
    def get_max_iterations(self) -> int:
        """Obtiene el número máximo de iteraciones"""
        return self.max_iterations
    
    def set_delay(self, milliseconds: int):
        """Establece el retardo en milisegundos"""
        if milliseconds >= 0:
            self.delay = milliseconds / 1000.0
    
    def get_delay(self) -> int:
        """Obtiene el retardo en milisegundos"""
        return int(self.delay * 1000)
    
    def bi_state_normalization(self, y: float) -> float:
        """Normalización binaria: 0 si ≤0.5, 1 si >0.5 (como en Java BiState)"""
        if y <= 0.5:
            return 0.0
        return 1.0
    
    def tri_state_normalization(self, y: float) -> float:
        """Normalización de tres estados: 0, 0.5, 1 (como en Java TriState)"""
        if y <= 1.0/3.0:
            return 0.0
        elif y <= 2.0/3.0:
            return 0.5
        return 1.0
    
    def sy_normalization(self, y: float) -> float:
        """Normalización sigmoidal: 1/(1+exp(-9*(y-0.5))) (como en Java Sy)"""
        try:
            return 1.0 / (1.0 + math.exp(-9.0 * (y - 0.5)))
        except OverflowError:
            # Manejar overflow como en Java
            return 1.0 if y > 0.5 else 0.0
    
    def syc_normalization(self, y: float) -> float:
        """Normalización por saturación: max(0, min(1, y)) (como en Java SyC)"""
        if y < 0:
            return 0.0
        elif y > 1:
            return 1.0
        else:
            return y
    
    def tanh_normalization(self, y: float) -> float:
        """Tanh escalada a [0,1]: 0.5 * tanh(2*x) + 0.5"""
        return 0.5 * math.tanh(2.0 * y) + 0.5
    
    def sigmoid_normalization(self, y: float) -> float:
        """Sigmoid suave: 1/(1+exp(-0.5*x))"""
        try:
            return 1.0 / (1.0 + math.exp(-5.0 * (y)))
        except OverflowError:
            return 1.0 if y > 0 else 0.0
    
    def linear_normalization(self, y: float) -> float:
        """
        Función tipo tangente hiperbólica:
            f4(x) = (e^(2x) - 1) / (e^(2x) + 1)
       
        """
        try:
            return 1.0 / (1.0 + math.exp(-2.0 * (y)))
        except OverflowError:
            return 1.0 if y > 0 else 0.0
    
    def relu_normalization(self, y: float) -> float:
        """
        Función sigmoide generalizada:
            f5(x) = 1 / (1 + e^(-λ (x - h)))

        """
        lamb = 5.0
        h = 0.5

        try:
            return 1.0 / (1.0 + math.exp(-lamb * (y - h)))
        except OverflowError:
            return 1.0 if y > h else 0.0
    
    def normalization(self, y: float) -> float:
        """Aplica normalización según el tipo seleccionado"""
        if self.saturation_type == NormalizationType.BISTATE:
            return self.bi_state_normalization(y)
        elif self.saturation_type == NormalizationType.TRISTATE:
            return self.tri_state_normalization(y)
        elif self.saturation_type == NormalizationType.SY:
            return self.sy_normalization(y)
        elif self.saturation_type == NormalizationType.TANH:
            return self.tanh_normalization(y)
        elif self.saturation_type == NormalizationType.SIGMOID:
            return self.sigmoid_normalization(y)
        elif self.saturation_type == NormalizationType.LINEAR:
            return self.linear_normalization(y)
        elif self.saturation_type == NormalizationType.RELU:
            return self.relu_normalization(y)
        else:  # SYC (default)
            return self.syc_normalization(y)
    
    def has_stabilized(self) -> bool:
        """Verifica si el mapa ha alcanzado estabilidad (equivalente a Estabilizo() en Java)"""
        map_obj = self.map_canvas.get_map()
        
        if map_obj.size_concepts_data() <= 1:
            return False
        
        concepts = map_obj.get_concept_list()
        data_size = map_obj.size_concepts_data()
        
        # Comparar como en Java: desde i=0 hasta sizeConceptsData()-1
        for i in range(data_size - 1):
            # Para cada iteración, verificar todos los conceptos
            for j, concept in enumerate(concepts):
                # Si hay diferencia > 0.0001, hacer break (salir del bucle de conceptos)
                if abs(concept.get_value(i) - concept.get_current_value()) > 0.0001:
                    break
                # Si llegamos al último concepto sin diferencias, estabilizó
                elif j == len(concepts) - 1:
                    pass  # Estabilidad alcanzada
                    return True
        
        return False
    
    def should_continue(self, iteration: int) -> bool:
        """Determina si debe continuar iterando"""
        if iteration >= self.max_iterations:
            return False
        if self.stop_on_stabilize:
            return not self.has_stabilized()
        return True
    
    def run(self):
        """Punto de entrada principal para la ejecución"""
        if self._running:
            return
        
        self._running = True
        self.play_button.configure(state='disabled')
        
        # Ejecutar en hilo separado
        self.thread = threading.Thread(target=self._execute, daemon=True)
        self.thread.start()
    
    def _execute(self):
        """Ejecuta la simulación"""
        try:
            if self.map_canvas.get_map().is_dynamic():
                self._run_dynamic()
            else:
                self._run_static()
        except Exception as e:
            pass  # Error en ejecución
        finally:
            self._running = False
            self.play_button.configure(text="Reset", state='normal')
            # Notificar fin de ejecución (p. ej., para mostrar resultados)
            if self.on_finish is not None:
                try:
                    # Ejecutar en hilo UI
                    self.map_canvas.after(0, self.on_finish)
                except Exception:
                    pass
    
    def _run_static(self):
        """Ejecuta el mapa como estático"""
        iteration = 1
        map_obj = self.map_canvas.get_map()
        
        while self._running:
            # Procesar relaciones según tipo de inferencia
            for relation in map_obj.get_relation_list():
                final_concept = relation.get_final_concept()
                initial_value = relation.get_initial_concept().get_last_value()
                
                if self.inference_type == InferenceType.KOSKO_RESCALED:
                    # Ecuación 8: reescalar entrada a [-1,1]
                    rescaled_input = 2.0 * initial_value - 1.0
                    final_concept.auxiliary_value += rescaled_input * relation.get_value()
                else:
                    # Ecuación estándar o con memoria
                    final_concept.auxiliary_value += initial_value * relation.get_value()
            
            # Actualizar conceptos
            for concept in map_obj.get_concept_list():
                # Agregar memoria según tipo de inferencia
                if self.inference_type == InferenceType.KOSKO_MEMORY:
                    # Ecuación 7: agregar A_i^(t)
                    concept.auxiliary_value += concept.get_last_value()
                elif self.inference_type == InferenceType.KOSKO_RESCALED:
                    # Ecuación 8: agregar (2*A_i^(t) - 1)
                    concept.auxiliary_value += 2.0 * concept.get_last_value() - 1.0
                
                normalized_value = self.normalization(concept.auxiliary_value)
                concept.add_last_value(normalized_value)
                concept.set_current_value(concept.get_last_value())
                concept.auxiliary_value = 0.0
            
            # Actualizar interfaz
            self.map_canvas.after(0, self.map_canvas.repaint)
            
            # Aplicar retardo
            if self.delay > 0:
                time.sleep(self.delay)
            
            # Actualizar iteración (como en Java: setCurrentIteration(c++))
            map_obj.set_current_iteration(iteration)
            self.iteration_label.after(0, lambda: self.iteration_label.config(
                text=map_obj.get_iteration_label()
            ))
            
            iteration += 1
            
            # Verificar si debe continuar (equivalente a Continue(c) en Java)
            if not self.should_continue(iteration):
                break
    
    def _run_dynamic(self):
        """Ejecuta el mapa como dinámico"""
        iteration = 1
        map_obj = self.map_canvas.get_map()
        
        # Usar do-while equivalente como en Java
        while self._running:
            # Procesar relaciones con reglas dinámicas
            for relation in map_obj.get_relation_list():
                self.rules.compute_relation_value(relation)
                initial_value = abs(relation.get_initial_concept().get_last_value())
                final_concept = relation.get_final_concept()
                
                if self.inference_type == InferenceType.KOSKO_RESCALED:
                    # Ecuación 8: reescalar entrada a [-1,1]
                    rescaled_input = 2.0 * initial_value - 1.0
                    final_concept.auxiliary_value += rescaled_input * relation.get_value()
                else:
                    # Ecuación estándar o con memoria
                    final_concept.auxiliary_value += initial_value * relation.get_value()
            
            # Actualizar conceptos
            for concept in map_obj.get_concept_list():
                # Agregar memoria según tipo de inferencia
                if self.inference_type == InferenceType.KOSKO_MEMORY:
                    # Ecuación 7: agregar A_i^(t)
                    concept.auxiliary_value += concept.get_last_value()
                elif self.inference_type == InferenceType.KOSKO_RESCALED:
                    # Ecuación 8: agregar (2*A_i^(t) - 1)
                    concept.auxiliary_value += 2.0 * concept.get_last_value() - 1.0
                
                normalized_value = self.normalization(concept.auxiliary_value)
                concept.add_last_value(normalized_value)
                concept.set_current_value(concept.get_last_value())
                concept.auxiliary_value = 0.0
            
            # Actualizar interfaz
            self.map_canvas.after(0, self.map_canvas.repaint)
            
            # Aplicar retardo
            if self.delay > 0:
                time.sleep(self.delay)
            
            # Actualizar iteración (como en Java: setCurrentIteration(c++))
            map_obj.set_current_iteration(iteration)
            self.iteration_label.after(0, lambda: self.iteration_label.config(
                text=map_obj.get_iteration_label()
            ))
            
            iteration += 1
            
            # Verificar si debe continuar (equivalente a Continue(c) en Java)
            if not self.should_continue(iteration):
                break