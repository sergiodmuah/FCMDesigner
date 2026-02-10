"""
Utilidades de dataset para entrenar Mapas Cognitivos Difusos (FCM).

Este módulo ofrece un cargador ligero para crear datasets desde archivos CSV
o directamente desde estructuras en memoria, con el propósito de aprender los
pesos de las relaciones de un mapa existente mediante algoritmos de
optimización.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple, Optional
from enum import Enum


class TargetType(Enum):
    """Tipo de variable objetivo detectado automáticamente"""
    BINARY = "binary"  # Valores 0/1 o muy cercanos
    MULTICLASS = "multiclass"  # Valores enteros discretos (3+ clases)
    CONTINUOUS = "continuous"  # Valores continuos en rango amplio


@dataclass
class TargetInfo:
    """Información sobre el tipo y normalización del target"""
    target_type: TargetType
    num_classes: Optional[int] = None  # Para multiclase
    min_val: Optional[float] = None  # Para continuo (antes de normalizar)
    max_val: Optional[float] = None  # Para continuo (antes de normalizar)


@dataclass
class Sample:
    """Representa una muestra de entrenamiento para aprendizaje de FCM.

    - features: mapeo nombre_de_concepto -> activación inicial en [0,1]
    - target_value: valor objetivo deseado para el concepto objetivo en [0,1]
    """

    features: Dict[str, float]
    target_value: float
    # Peso opcional de la muestra (para MSE ponderado). Por defecto 1.0
    weight: float = 1.0


class FCMDataset:
    @staticmethod
    def _ensure_float(value, column: str) -> float:
        """Convierte un valor a float verificando NaN o valores vacíos."""
        if value is None:
            raise ValueError(f"Valor vacío en columna '{column}'")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Valor no numérico en columna '{column}': {value}") from exc
        if math.isnan(numeric):
            raise ValueError(f"Valor NaN en columna '{column}'")
        return numeric

    """Contenedor y cargador de muestras para entrenar un FCM.

    El dataset es consciente de los nombres de conceptos, por lo que el mapa
    a entrenar debe tener conceptos cuyos nombres coincidan con las claves de
    las características (features) proporcionadas.
    """

    def __init__(self, samples: Sequence[Sample]):
        self._samples: List[Sample] = list(samples)
        self._target_info: Optional[TargetInfo] = None
    
    @staticmethod
    def detect_target_type(target_values: List[float], max_sample_size: int = 10000) -> TargetInfo:
        """Detecta automáticamente el tipo de variable objetivo.
        
        Para archivos grandes, usa una muestra aleatoria para eficiencia.
        
        Args:
            target_values: Lista completa de valores del target
            max_sample_size: Tamaño máximo de muestra para detección (default: 10000)
        
        Retorna:
        - BINARY si los valores son 0/1 o muy cercanos (tolerancia 0.01)
        - MULTICLASS si son valores enteros discretos con pocos valores únicos (3-20)
        - CONTINUOUS si hay muchos valores únicos o rango amplio
        """
        if not target_values:
            return TargetInfo(TargetType.CONTINUOUS)
        
        # Para archivos grandes, usar muestra aleatoria para detección
        # (pero calcular min/max sobre TODOS los valores para normalización correcta)
        import random
        sample_values = target_values
        if len(target_values) > max_sample_size:
            sample_values = random.sample(target_values, max_sample_size)
        
        # Calcular estadísticas sobre TODOS los valores (necesario para min-max)
        min_val = min(target_values)
        max_val = max(target_values)
        
        # Detección sobre la muestra
        unique_vals = sorted(set(sample_values))
        val_range = max_val - min_val
        
        # Detectar binario: valores muy cercanos a 0 y 1
        binary_candidates = [v for v in unique_vals if abs(v - 0.0) < 0.01 or abs(v - 1.0) < 0.01]
        if len(binary_candidates) >= 2 and len(unique_vals) <= 3:
            # Verificar que la mayoría de valores sean 0 o 1
            binary_count = sum(1 for v in target_values if abs(v - 0.0) < 0.01 or abs(v - 1.0) < 0.01)
            if binary_count / len(target_values) > 0.9:
                return TargetInfo(TargetType.BINARY, num_classes=2)
        
        # Detectar multiclase: valores enteros discretos en rango pequeño
        integer_vals = [v for v in unique_vals if abs(v - round(v)) < 0.001]
        if len(integer_vals) >= 3 and len(integer_vals) <= 20:
            # Verificar que la mayoría sean enteros
            integer_count = sum(1 for v in target_values if abs(v - round(v)) < 0.001)
            if integer_count / len(target_values) > 0.9:
                min_class = int(round(min(integer_vals)))
                max_class = int(round(max(integer_vals)))
                num_classes = max_class - min_class + 1
                if num_classes >= 3 and num_classes <= 20:
                    # Guardar min y max para reescalado correcto
                    return TargetInfo(TargetType.MULTICLASS, num_classes=num_classes, min_val=float(min_class), max_val=float(max_class))
        
        # Por defecto: continuo
        return TargetInfo(TargetType.CONTINUOUS, min_val=min_val, max_val=max_val)
    
    @staticmethod
    def normalize_targets(records: List[Dict[str, float]], target_column: str, target_info: TargetInfo) -> List[Dict[str, float]]:
        """Normaliza los valores del target según su tipo detectado.
        
        - BINARY: no se modifica (ya está en [0,1])
        - MULTICLASS: reescala k -> k/(N-1) donde k es la clase (0..N-1)
        - CONTINUOUS: normalización min-max a [0,1]
        """
        normalized = []
        for rec in records:
            rec_copy = rec.copy()
            val = float(rec[target_column])
            
            if target_info.target_type == TargetType.BINARY:
                # No modificar, ya está en [0,1]
                pass
            elif target_info.target_type == TargetType.MULTICLASS:
                # Reescalar: convertir clase k a k/(N-1) donde k está en [min_class, max_class]
                if target_info.num_classes and target_info.num_classes >= 3:
                    try:
                        k = int(round(val))
                        # Ajustar k al rango [0, num_classes-1] si min_class != 0
                        if target_info.min_val is not None:
                            k_shifted = k - int(target_info.min_val)
                            if 0 <= k_shifted < target_info.num_classes:
                                rec_copy[target_column] = float(k_shifted) / float(target_info.num_classes - 1)
                    except (ValueError, TypeError):
                        pass
            elif target_info.target_type == TargetType.CONTINUOUS:
                # Normalización min-max: (x - min) / (max - min)
                if target_info.min_val is not None and target_info.max_val is not None:
                    if target_info.max_val > target_info.min_val:
                        normalized_val = (val - target_info.min_val) / (target_info.max_val - target_info.min_val)
                        rec_copy[target_column] = max(0.0, min(1.0, normalized_val))  # Clamp a [0,1]
                    else:
                        # Todos los valores son iguales
                        rec_copy[target_column] = 0.5
            
            normalized.append(rec_copy)
        return normalized
    
    def get_target_info(self) -> Optional[TargetInfo]:
        """Retorna la información del target si está disponible"""
        return self._target_info
    
    def set_target_info(self, info: TargetInfo):
        """Establece la información del target"""
        self._target_info = info

    @staticmethod
    def from_rows(rows: Iterable[Dict[str, float]], target_column: str) -> "FCMDataset":
        """Crea un dataset desde un iterable de diccionarios.

        Cada fila debe contener la `target_column` y el resto de claves se
        consideran nombres de conceptos de entrada.
        """

        samples: List[Sample] = []
        for row in rows:
            if target_column not in row:
                raise ValueError(f"Row missing target column '{target_column}'")
            features = {k: float(v) for k, v in row.items() if k != target_column}
            target_value = float(row[target_column])
            samples.append(Sample(features=features, target_value=target_value))
        return FCMDataset(samples)

    @staticmethod
    def from_csv(filepath: str, target_column: str | None = None, delimiter: str = ",") -> "FCMDataset":
        """Carga un dataset desde un archivo CSV con cabecera.

        Si `target_column` es None, se toma como objetivo la última columna del CSV.
        Todas las columnas excepto la de objetivo se interpretan como características.
        """

        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter=delimiter)
            headers = list(reader.fieldnames or [])
            if not headers:
                raise ValueError("CSV sin cabecera")
            tgt = target_column or headers[-1]
            rows: List[Dict[str, float]] = []
            for row in reader:
                rows.append({k: float(v) for k, v in row.items()})
        return FCMDataset.from_rows(rows, tgt)

    @staticmethod
    def from_excel(filepath: str, target_column: str | None = None, sheet_name: int | str = 0) -> "FCMDataset":
        """Carga un dataset desde un archivo Excel (.xlsx/.xls) con cabecera."""
        try:
            import pandas as pd  # type: ignore
        except ImportError as exc:
            raise ImportError("Necesitas instalar pandas y openpyxl para leer archivos Excel:\n pip install pandas openpyxl") from exc

        df = pd.read_excel(filepath, sheet_name=sheet_name)
        if df.empty:
            raise ValueError("Excel sin datos")

        columns = list(df.columns)
        if not columns:
            raise ValueError("Excel sin columnas")
        tgt = target_column or columns[-1]

        records: List[Dict[str, float]] = []
        for record in df.to_dict(orient="records"):
            clean: Dict[str, float] = {}
            for col in columns:
                if col not in record:
                    continue
                clean[str(col)] = FCMDataset._ensure_float(record[col], str(col))
            records.append(clean)
        return FCMDataset.from_rows(records, str(tgt))

    @staticmethod
    def from_file(filepath: str, target_column: str | None = None, delimiter: str = ",") -> "FCMDataset":
        """Carga un dataset detectando el formato por extensión (CSV/Excel)."""
        suffix = Path(filepath).suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            return FCMDataset.from_excel(filepath, target_column)
        if suffix in {".csv", ".txt"}:
            return FCMDataset.from_csv(filepath, target_column=target_column, delimiter=delimiter)
        raise ValueError(f"Formato no soportado: '{suffix}'. Usa CSV o Excel.")

    @staticmethod
    def from_csv_with_counts(filepath: str, target_column: str | None = None, delimiter: str = ",") -> "FCMDataset":
        """Carga un dataset desde CSV esperando una columna opcional 'count' como peso.

        - Si existe la columna 'count', se usa como weight de la muestra.
        - El resto de columnas (excepto target y count) son las features.
        """
        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter=delimiter)
            headers = list(reader.fieldnames or [])
            if not headers:
                raise ValueError("CSV sin cabecera")
            tgt = target_column or (headers[-2] if len(headers) >= 2 and headers[-1] == 'count' else headers[-1])
            samples: List[Sample] = []
            for row in reader:
                if tgt not in row:
                    raise ValueError(f"Row missing target column '{tgt}'")
                weight_val = 1.0
                if 'count' in row and row['count'] is not None and row['count'] != "":
                    weight_val = float(row['count'])
                features = {}
                for k, v in row.items():
                    if k == tgt or k == 'count':
                        continue
                    features[k] = float(v)
                target_value = float(row[tgt])
                samples.append(Sample(features=features, target_value=target_value, weight=weight_val))
        return FCMDataset(samples)

    @staticmethod
    def from_excel_with_counts(filepath: str, target_column: str | None = None, sheet_name: int | str = 0) -> "FCMDataset":
        """Carga dataset desde Excel esperando columna opcional 'count' como peso."""
        try:
            import pandas as pd  # type: ignore
        except ImportError as exc:
            raise ImportError("Necesitas instalar pandas y openpyxl para leer archivos Excel:\n pip install pandas openpyxl") from exc

        df = pd.read_excel(filepath, sheet_name=sheet_name)
        if df.empty:
            raise ValueError("Excel sin datos")

        columns = list(df.columns)
        if not columns:
            raise ValueError("Excel sin columnas")

        weight_col = "count" if "count" in columns else None
        if target_column:
            tgt = target_column
        elif weight_col and columns[-1] == weight_col and len(columns) >= 2:
            tgt = columns[-2]
        else:
            tgt = columns[-1]

        samples: List[Sample] = []
        for record in df.to_dict(orient="records"):
            target_value = None
            weight_val = 1.0
            features: Dict[str, float] = {}
            for col in columns:
                key = str(col)
                if key not in record:
                    continue
                if weight_col and key == weight_col:
                    weight_val = FCMDataset._ensure_float(record[key], key)
                    continue
                if key == tgt:
                    target_value = FCMDataset._ensure_float(record[key], key)
                else:
                    features[key] = FCMDataset._ensure_float(record[key], key)
            if target_value is None:
                raise ValueError(f"Fila sin columna objetivo '{tgt}' o valor inválido")
            samples.append(Sample(features=features, target_value=target_value, weight=weight_val))
        return FCMDataset(samples)

    @staticmethod
    def from_file_with_counts(filepath: str, target_column: str | None = None, delimiter: str = ",") -> "FCMDataset":
        """Versión que detecta formato (CSV/Excel) para datasets con columna 'count'."""
        suffix = Path(filepath).suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            return FCMDataset.from_excel_with_counts(filepath, target_column)
        if suffix in {".csv", ".txt"}:
            return FCMDataset.from_csv_with_counts(filepath, target_column=target_column, delimiter=delimiter)
        raise ValueError(f"Formato no soportado: '{suffix}'. Usa CSV o Excel.")

    def __len__(self) -> int:
        return len(self._samples)

    def __iter__(self):
        return iter(self._samples)

    def to_feature_target(self, concept_names: Sequence[str]) -> Tuple[List[List[float]], List[float]]:
        """Exporta características y objetivos alineados a los nombres dados.

        Si falta un concepto en una muestra se rellena con 0.0.
        Claves extra en la muestra se ignoran.
        """

        features_matrix: List[List[float]] = []
        targets: List[float] = []
        for sample in self._samples:
            row = [float(sample.features.get(name, 0.0)) for name in concept_names]
            features_matrix.append(row)
            targets.append(float(sample.target_value))
        return features_matrix, targets


