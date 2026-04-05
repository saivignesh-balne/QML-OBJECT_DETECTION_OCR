from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import EfficientSU2, PauliFeatureMap, RealAmplitudes, StatePreparation, ZZFeatureMap
from qiskit_machine_learning.circuit.library import raw_feature_vector
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from .config import QuantumClassifierConfig


def one_hot(labels: np.ndarray, num_classes: int) -> np.ndarray:
    return np.eye(num_classes, dtype=np.float32)[labels]


def decode_predictions(predictions: np.ndarray) -> np.ndarray:
    predictions = np.asarray(predictions)
    if predictions.ndim == 2:
        return predictions.argmax(axis=1)
    return predictions.astype(int).ravel()


class MulticlassInterpret:
    def __init__(self, num_classes: int) -> None:
        self.num_classes = num_classes

    def __call__(self, bitstring_as_int: int) -> int:
        return bitstring_as_int % self.num_classes


def pad_or_truncate(vector: np.ndarray, target_dim: int) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float64).ravel()
    if vector.shape[0] >= target_dim:
        return vector[:target_dim]
    padded = np.zeros(target_dim, dtype=np.float64)
    padded[: vector.shape[0]] = vector
    return padded


def scale_to_angles(features: np.ndarray, n_qubits: int) -> np.ndarray:
    features = pad_or_truncate(features, n_qubits)
    scaler = MinMaxScaler(feature_range=(0.0, np.pi))
    transformed = scaler.fit_transform(features.reshape(-1, 1)).reshape(-1)
    return transformed.astype(np.float32)


def normalize_amplitudes(features: np.ndarray, n_qubits: int) -> np.ndarray:
    target_dim = 2**n_qubits
    vector = pad_or_truncate(features, target_dim)
    long_dtype = np.longdouble
    vector = np.asarray(vector, dtype=long_dtype)
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        vector[0] = 1.0
        norm = 1.0
    normalized = np.asarray(vector / long_dtype(norm), dtype=long_dtype)
    amplitude_sq_sum = float(np.sum(np.square(normalized), dtype=long_dtype))
    residual = 1.0 - amplitude_sq_sum
    if abs(residual) > 1e-18:
        pivot = int(np.argmax(np.abs(normalized)))
        pivot_sign = 1.0 if normalized[pivot] >= 0.0 else -1.0
        corrected_sq = max(0.0, float(normalized[pivot] ** 2) + residual)
        normalized[pivot] = long_dtype(pivot_sign) * np.sqrt(long_dtype(corrected_sq))
    final_norm = float(np.linalg.norm(normalized))
    if final_norm == 0.0:
        normalized = np.zeros(target_dim, dtype=long_dtype)
        normalized[0] = 1.0
    else:
        normalized /= long_dtype(final_norm)
    final_sq_sum = float(np.sum(np.square(normalized), dtype=long_dtype))
    if not np.isclose(final_sq_sum, 1.0, atol=1e-14):
        normalized /= np.sqrt(long_dtype(final_sq_sum))
    return np.asarray(normalized, dtype=np.float64)


def angle_encoding_circuit(features: np.ndarray, n_qubits: int) -> QuantumCircuit:
    angles = scale_to_angles(features, n_qubits)
    circuit = QuantumCircuit(n_qubits)
    for qubit, angle in enumerate(angles):
        circuit.ry(float(angle), qubit)
    for qubit in range(n_qubits - 1):
        circuit.cx(qubit, qubit + 1)
    return circuit


def amplitude_encoding_circuit(features: np.ndarray, n_qubits: int) -> QuantumCircuit:
    amplitudes = normalize_amplitudes(features, n_qubits)
    circuit = QuantumCircuit(n_qubits)
    circuit.append(StatePreparation(amplitudes), range(n_qubits))
    return circuit


@dataclass
class ClassicalToQuantumEncoder:
    config: QuantumClassifierConfig
    scaler: StandardScaler | None = None
    variance_filter: VarianceThreshold | None = None
    selector: SelectKBest | None = None
    reducer: PCA | None = None
    angle_scaler: MinMaxScaler | None = None

    @property
    def target_dim(self) -> int:
        if self.config.encoding == "angle":
            return self.config.n_qubits
        return 2**self.config.n_qubits

    def fit(self, features: np.ndarray, labels: np.ndarray | None = None) -> "ClassicalToQuantumEncoder":
        self.scaler = StandardScaler()
        scaled = self.scaler.fit_transform(features)
        if scaled.shape[1] > 1:
            self.variance_filter = VarianceThreshold(threshold=0.0)
            selected = self.variance_filter.fit_transform(scaled)
        else:
            self.variance_filter = None
            selected = scaled
        selector_k = min(self.config.preselect_dim, selected.shape[1])
        if labels is not None and selector_k > self.target_dim:
            self.selector = SelectKBest(score_func=f_classif, k=selector_k)
            selected = self.selector.fit_transform(selected, np.asarray(labels))
        else:
            self.selector = None
        max_components = min(selected.shape[0], selected.shape[1], self.target_dim)
        self.reducer = PCA(n_components=max_components, random_state=self.config.random_state)
        reduced = self.reducer.fit_transform(selected)
        if self.config.encoding == "angle":
            reduced = self._post_reduce(reduced)
            self.angle_scaler = MinMaxScaler(feature_range=(0.0, np.pi))
            self.angle_scaler.fit(reduced)
        return self

    def transform(self, features: np.ndarray) -> np.ndarray:
        if self.scaler is None or self.reducer is None:
            raise RuntimeError("Encoder must be fitted before calling transform().")
        scaled = self.scaler.transform(features)
        variance_filtered = self.variance_filter.transform(scaled) if self.variance_filter is not None else scaled
        selected = self.selector.transform(variance_filtered) if self.selector is not None else variance_filtered
        reduced = self.reducer.transform(selected)
        reduced = self._post_reduce(reduced)
        if self.config.encoding == "angle":
            if self.angle_scaler is None:
                raise RuntimeError("Angle scaler is missing.")
            return self.angle_scaler.transform(reduced).astype(np.float32)
        normalized = np.stack(
            [normalize_amplitudes(sample, self.config.n_qubits) for sample in reduced],
            axis=0,
        )
        return normalized.astype(np.float64)

    def fit_transform(self, features: np.ndarray, labels: np.ndarray | None = None) -> np.ndarray:
        self.fit(features, labels=labels)
        return self.transform(features)

    def _post_reduce(self, reduced: np.ndarray) -> np.ndarray:
        target_dim = self.target_dim
        if reduced.shape[1] == target_dim:
            return reduced
        adjusted = np.zeros((reduced.shape[0], target_dim), dtype=np.float64)
        width = min(target_dim, reduced.shape[1])
        adjusted[:, :width] = reduced[:, :width]
        return adjusted


def build_feature_map(config: QuantumClassifierConfig) -> Any:
    if config.encoding == "angle":
        if config.model_type in {"qsvc_pauli"}:
            return PauliFeatureMap(
                feature_dimension=config.n_qubits,
                reps=config.feature_map_reps,
                paulis=["Z", "ZZ", "XX"],
                entanglement="full",
            )
        entanglement = "full" if config.model_type in {"qsvc_zz_full"} else "linear"
        return ZZFeatureMap(
            feature_dimension=config.n_qubits,
            reps=config.feature_map_reps,
            entanglement=entanglement,
        )
    return raw_feature_vector(feature_dimension=2**config.n_qubits)


def build_ansatz(config: QuantumClassifierConfig) -> QuantumCircuit:
    if config.model_type in {"vqc_efficient"}:
        return EfficientSU2(
            num_qubits=config.n_qubits,
            reps=config.ansatz_reps,
            entanglement="full",
        )
    return RealAmplitudes(
        num_qubits=config.n_qubits,
        reps=config.ansatz_reps,
        entanglement="linear",
    )
