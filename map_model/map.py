# map_model/map.py
"""
Contenedor principal del mapa cognitivo
Migrado desde Map.java
"""

from typing import List, Optional, Tuple
import os
import csv
from .concept import Concept
from .relation import Relation


class Map:
    """Contenedor principal del mapa cognitivo"""
    
    def __init__(self, dynamic: bool = False):
        self.current_iteration = 0
        self.concepts_list: List[Concept] = []
        self.relations_list: List[Relation] = []
        self.dynamic = dynamic
        # Metadatos: normalización usada en entrenamiento (si existe)
        self.trained_normalization: Optional[int] = None  # NormalizationType como int
    
    def is_dynamic(self) -> bool:
        """Verifica si el mapa es dinámico"""
        return self.dynamic
    
    def add_concept(self, x: int, y: int, dynamic: bool = None) -> Concept:
        """Agrega un concepto al mapa"""
        if dynamic is None:
            dynamic = self.dynamic
        concept = Concept(x, y, dynamic)
        self.concepts_list.append(concept)
        return concept
    
    def add_relation(self, initial_concept: Concept, final_concept: Concept) -> Relation:
        """Agrega una relación al mapa"""
        # Evitar duplicados (misma pareja origen-destino)
        for rel in self.relations_list:
            if rel.get_initial_concept() is initial_concept and rel.get_final_concept() is final_concept:
                return rel
        relation = Relation(initial_concept, final_concept, self.dynamic)
        self.relations_list.append(relation)
        return relation
    
    def find_concept(self, x: int = None, y: int = None, concept_id: int = None) -> Optional[Concept]:
        """Busca un concepto por posición o ID"""
        if concept_id is not None:
            for concept in self.concepts_list:
                if concept.get_concept_id() == concept_id:
                    return concept
        elif x is not None and y is not None:
            for concept in self.concepts_list:
                if concept.is_inside(x, y):
                    return concept
        return None
    
    def find_relation(self, x: int, y: int) -> Optional[Relation]:
        """Busca una relación por posición"""
        for relation in self.relations_list:
            if relation.is_inside(x, y):
                return relation
        return None
    
    def delete_relation(self, relation: Relation):
        """Elimina una relación del mapa"""
        if relation in self.relations_list:
            self.relations_list.remove(relation)
    
    def delete_concept(self, concept: Concept):
        """Elimina un concepto y todas sus relaciones"""
        if concept in self.concepts_list:
            self.concepts_list.remove(concept)
        
        # Eliminar relaciones asociadas
        relations_to_remove = [
            rel for rel in self.relations_list
            if rel.get_initial_concept() == concept or rel.get_final_concept() == concept
        ]
        
        for relation in relations_to_remove:
            self.relations_list.remove(relation)
    
    def draw_map(self, canvas, with_value: bool = True):
        """Dibuja todo el mapa en el canvas"""
        # Limpiar canvas
        canvas.delete("concept")
        canvas.delete("relation")
        
        # Dibujar conceptos
        for concept in self.concepts_list:
            concept.draw_concept(canvas, with_value)
        
        # Dibujar relaciones
        for relation in self.relations_list:
            relation.draw_relation(canvas)
    
    def clear(self):
        """Elimina todo el contenido del mapa"""
        self.relations_list.clear()
        self.concepts_list.clear()
        self.current_iteration = 0
    
    def update_concepts_id(self):
        """Actualiza los identificadores de los conceptos"""
        for i, concept in enumerate(self.concepts_list):
            concept.set_id(i)
    
    def save(self, directory: str, filename: str):
        """Guarda el mapa en un archivo"""
        self.update_concepts_id()
        filepath = os.path.join(directory, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                # Escribir información general
                file.write(f"{len(self.concepts_list)}\n")
                file.write(f"{len(self.relations_list)}\n")
                
                # Escribir conceptos
                for concept in self.concepts_list:
                    pos = concept.get_position()
                    file.write(f"{concept.get_name()}\n")
                    file.write(f"{concept.get_concept_id()}\n")
                    file.write(f"{pos[0]}\n")
                    file.write(f"{pos[1]}\n")
                    file.write(f"{concept.get_radius()}\n")
                    file.write(f"{concept.get_initial_value()}\n")
                    file.write(f"{concept.get_label_position()}\n")
                    file.write(f"{concept.comment}\n")
                
                # Escribir relaciones
                for relation in self.relations_list:
                    file.write(f"{relation.get_initial_concept().get_concept_id()}\n")
                    file.write(f"{relation.get_final_concept().get_concept_id()}\n")
                    file.write(f"{relation.get_value()}\n")
                    file.write(f"{relation.get_approximation_percentage()}\n")
                    file.write(f"{relation.get_dynamic_input()}\n")
                    file.write(f"{relation.comment}\n")
                
                # Metadatos (compatibilidad hacia atrás: al final, con marcador)
                if self.trained_normalization is not None:
                    file.write("__METADATA__\n")
                    file.write(f"trained_normalization={self.trained_normalization}\n")
        
        except IOError as e:
            pass  # Error saving file
            raise
    
    def load(self, directory: str, filename: str):
        """Carga el mapa desde un archivo"""
        self.current_iteration = 0
        self.clear()
        filepath = os.path.join(directory, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                lines = [line.strip() for line in file.readlines()]
                line_index = 0
                
                # Leer información general
                num_concepts = int(lines[line_index])
                line_index += 1
                num_relations = int(lines[line_index])
                line_index += 1
                
                # Leer conceptos
                for _ in range(num_concepts):
                    concept = Concept(0, 0, self.dynamic)
                    
                    concept.set_name(lines[line_index])
                    line_index += 1
                    concept.set_id(int(lines[line_index]))
                    line_index += 1
                    x = int(lines[line_index])
                    line_index += 1
                    y = int(lines[line_index])
                    line_index += 1
                    concept.set_position(x, y)
                    concept.set_radius(int(lines[line_index]))
                    line_index += 1
                    initial_value = float(lines[line_index])
                    line_index += 1
                    concept.set_initial_value(initial_value)
                    concept.set_current_value(initial_value)
                    concept.set_label_position(int(lines[line_index]))
                    line_index += 1
                    concept.set_comment(lines[line_index])
                    line_index += 1
                    
                    self.concepts_list.append(concept)
                
                # Leer relaciones
                for _ in range(num_relations):
                    initial_id = int(lines[line_index])
                    line_index += 1
                    final_id = int(lines[line_index])
                    line_index += 1
                    
                    initial_concept = self.find_concept(concept_id=initial_id)
                    final_concept = self.find_concept(concept_id=final_id)
                    
                    if initial_concept and final_concept:
                        relation = Relation(initial_concept, final_concept, self.dynamic)
                        relation.set_value(float(lines[line_index]))
                        line_index += 1
                        relation.set_approximation_percentage(float(lines[line_index]))
                        line_index += 1
                        relation.set_dynamic_input(float(lines[line_index]))
                        line_index += 1
                        relation.set_comment(lines[line_index])
                        line_index += 1
                        
                        self.relations_list.append(relation)
                
                # Leer metadatos (si existen, formato compatible hacia atrás)
                self.trained_normalization = None
                if line_index < len(lines) and lines[line_index] == "__METADATA__":
                    line_index += 1
                    while line_index < len(lines):
                        line = lines[line_index].strip()
                        if line.startswith("trained_normalization="):
                            try:
                                self.trained_normalization = int(line.split("=")[1])
                            except (ValueError, IndexError):
                                pass
                        line_index += 1
        
        except (IOError, IndexError, ValueError) as e:
            pass  # Error loading file
            raise
    
    def get_relation_list(self) -> List[Relation]:
        """Obtiene la lista de relaciones"""
        return self.relations_list
    
    def get_concept_list(self) -> List[Concept]:
        """Obtiene la lista de conceptos"""
        return self.concepts_list
    
    def reset_concepts(self):
        """Reinicia todos los conceptos"""
        for concept in self.concepts_list:
            concept.reset()
        self.set_show_iteration(0)
    
    def size_concepts_data(self) -> int:
        """Obtiene el tamaño de la historia de datos"""
        if not self.concepts_list:
            return 1
        return max(concept.get_values_size() for concept in self.concepts_list)
    
    def set_show_iteration(self, iteration: int):
        """Establece la iteración a mostrar"""
        max_iteration = self.size_concepts_data() - 1
        if 0 <= iteration <= max_iteration:
            for concept in self.concepts_list:
                concept.set_current_iteration(iteration)
            self.current_iteration = iteration
    
    def get_current_iteration(self) -> int:
        """Obtiene la iteración actual"""
        return self.current_iteration
    
    def set_current_iteration(self, iteration: int):
        """Establece la iteración actual (uso interno de RunFCM)"""
        self.current_iteration = iteration
    
    def get_iteration_label(self) -> str:
        """Obtiene la etiqueta de iteración"""
        max_iter = self.size_concepts_data() - 1
        return f"{self.current_iteration:04d} / {max_iter:04d}"
    
    def save_execution(self, directory: str, filename: str):
        """Guarda la ejecución del mapa en formato matriz"""
        self.update_concepts_id()
        filepath = os.path.join(directory, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                # Crear matriz de adyacencia
                size = len(self.concepts_list)
                matrix = [[0.0 for _ in range(size)] for _ in range(size)]
                
                # Llenar matriz con valores de relaciones
                for relation in self.relations_list:
                    i = relation.get_initial_concept().get_concept_id()
                    j = relation.get_final_concept().get_concept_id()
                    matrix[i][j] = relation.get_value()
                
                # Escribir matriz
                for row in matrix:
                    file.write(" ".join(f"{val:.6f}" for val in row) + "\n")
                
                # Escribir nombres de conceptos
                for concept in self.concepts_list:
                    file.write(f"{concept.get_name()}\n")
                
                # Escribir valores de iteraciones
                file.write("C = [\n")
                for i in range(self.size_concepts_data()):
                    values = [concept.get_value(i) for concept in self.concepts_list]
                    file.write(" ".join(f"{val:.6f}" for val in values) + "\n")
                file.write("]\n")
        
        except IOError as e:
            pass  # Error saving execution
            raise
        
    # ==============================
    # Entrada/Salida de matriz (CSV)
    # ==============================
    def get_adjacency_matrix(self) -> Tuple[List[str], List[List[float]]]:
        """Devuelve (nombres_de_conceptos, matriz_adyacencia) usando los IDs actuales.

        La matriz es de tamaño N x N donde la entrada [i][j] es el peso de i → j.
        """
        self.update_concepts_id()
        names = [c.get_name() for c in self.concepts_list]
        size = len(self.concepts_list)
        matrix = [[0.0 for _ in range(size)] for _ in range(size)]
        for relation in self.relations_list:
            i = relation.get_initial_concept().get_concept_id()
            j = relation.get_final_concept().get_concept_id()
            matrix[i][j] = relation.get_value()
        return names, matrix

    def export_adjacency_csv(self, filepath: str):
        """Exporta la matriz de adyacencia a CSV con cabeceras de nombres."""
        names, matrix = self.get_adjacency_matrix()
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([""] + names)
                def fmt(x: float) -> str:
                    # Redondear a 6 decimales y quitar ceros/decimal sobrantes
                    s = f"{round(x, 6):.6f}"
                    s = s.rstrip('0').rstrip('.')
                    return s if s != "-0" and s != "" else "0"
                for name, row in zip(names, matrix):
                    writer.writerow([name] + [fmt(val) for val in row])
        except OSError as e:
            pass  # Error exporting CSV
            raise

    def import_adjacency_csv(self, filepath: str):
        """Importa la matriz de adyacencia desde un CSV y reconstruye conceptos/relaciones.

        - La primera fila es cabecera con nombres de conceptos; la primera columna puede
          contener los nombres de fila (se ignora).
        - Todos los valores iniciales/actuales de los conceptos se ponen a 0.
        - Cualquier celda numérica no vacía se interpreta como peso (float).
        """
        try:
            with open(filepath, "r", newline="", encoding="utf-8") as f:
                reader = list(csv.reader(f))
        except OSError as e:
            pass  # Error reading CSV
            raise

        if not reader or len(reader) < 2:
            raise ValueError("CSV vacío o con formato inválido")

        header = reader[0][1:]
        size = len(header)

        # Reiniciar mapa
        self.clear()

        # Crear conceptos distribuidos en círculo para maximizar legibilidad de etiquetas
        # Centro fijo y radio adaptable para evitar solapamientos de nombres
        import math
        cx, cy = 500, 350
        # Radio base en función de N; crecer ligeramente con el número de conceptos
        base_radius = 220
        radius = max(160, min(360, base_radius + max(0, size - 8) * 12))

        for idx, name in enumerate(header):
            angle = (2.0 * math.pi * idx) / max(1, size)
            # La posición del concepto es la esquina superior izquierda del círculo del nodo
            # Usamos un radio visual aproximado de 10 px para centrar
            node_r = 10
            x = int(cx + radius * math.cos(angle) - node_r)
            y = int(cy + radius * math.sin(angle) - node_r)

            c = self.add_concept(x, y, self.dynamic)
            c.set_name(name if name else f"C{idx}")
            c.set_initial_value(0.0)
            c.set_current_value(0.0)

            # Colocar la etiqueta hacia fuera del círculo según el ángulo
            # Aproximación a TOP/RIGHT/BOTTOM/LEFT por cuadrante
            sin_a = math.sin(angle)
            cos_a = math.cos(angle)
            if abs(cos_a) >= abs(sin_a):
                # Lados izquierdo/derecho
                c.set_label_position(1 if cos_a > 0 else 3)  # RIGHT : LEFT
            else:
                # Arriba/abajo
                c.set_label_position(2 if sin_a > 0 else 0)  # BOTTOM : TOP

        # Asegurar IDs consecutivos 0..N-1 para poder indexar por ID
        self.update_concepts_id()

        # Construir relaciones a partir de las filas de la matriz
        for i, csv_row in enumerate(reader[1:1+size]):
            # Allow optional first column row name
            values = csv_row[1:] if len(csv_row) >= size else csv_row
            # Rellenar a tamaño N por si faltan celdas
            if len(values) < size:
                values = values + ["0"] * (size - len(values))
            for j in range(size):
                try:
                    w = float(values[j]) if values[j] != "" else 0.0
                except ValueError:
                    w = 0.0
                if abs(w) > 0.0:
                    init_concept = self.find_concept(concept_id=i)
                    final_concept = self.find_concept(concept_id=j)
                    if init_concept and final_concept:
                        rel = self.add_relation(init_concept, final_concept)
                        rel.set_value(w)
