from __future__ import annotations

import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from qiskit.primitives import StatevectorSampler
from qiskit_machine_learning.algorithms import PegasosQSVC, QSVC
from qiskit_machine_learning.algorithms.classifiers import VQC
from qiskit_machine_learning.kernels import FidelityStatevectorKernel
from qiskit_machine_learning.optimizers import COBYLA
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC

from .config import QuantumClassifierConfig
from .quantum import (
    ClassicalToQuantumEncoder,
    MulticlassInterpret,
    build_ansatz,
    build_feature_map,
    decode_predictions,
    one_hot,
)


QUANTUM_KERNEL_MODEL_TYPES = {
    "qsvc",
    "qsvc_zz_linear",
    "qsvc_zz_full",
    "qsvc_pauli",
    "pegasos_qsvc",
}
VQC_MODEL_TYPES = {
    "vqc",
    "vqc_real",
    "vqc_efficient",
}
CLASSICAL_MODEL_TYPES = {
    "svc_rbf",
    "random_forest",
    "logreg",
    "mlp",
}
QUANTUM_MODEL_TYPES = QUANTUM_KERNEL_MODEL_TYPES | VQC_MODEL_TYPES
MODEL_ORDER = [
    "svc_rbf",
    "logreg",
    "random_forest",
    "mlp",
    "qsvc",
    "qsvc_zz_full",
    "qsvc_pauli",
    "vqc_real",
    "vqc_efficient",
    "pegasos_qsvc",
]


def is_quantum_model(model_type: str) -> bool:
    return str(model_type) in QUANTUM_MODEL_TYPES


def describe_classifier_model(model_type: str, encoding: str) -> dict[str, object]:
    normalized = str(model_type)
    descriptions: dict[str, dict[str, object]] = {
        "qsvc": {
            "family": "quantum",
            "display_name": f"QSVM ZZ Kernel Linear ({encoding})",
            "kernel_name": "Fidelity Quantum Kernel",
            "feature_map_name": "ZZFeatureMap",
            "feature_map_detail": "linear entanglement",
            "ansatz_name": "none",
            "supported_encodings": ["angle", "amplitude"],
            "summary": "Baseline quantum kernel SVM with linear ZZ entanglement.",
            "strengths": "Simple quantum-kernel benchmark and easy presentation baseline.",
            "limitations": "Often weaker than strong classical baselines on rich image features.",
        },
        "qsvc_zz_linear": {
            "family": "quantum",
            "display_name": f"QSVM ZZ Kernel Linear ({encoding})",
            "kernel_name": "Fidelity Quantum Kernel",
            "feature_map_name": "ZZFeatureMap",
            "feature_map_detail": "linear entanglement",
            "ansatz_name": "none",
            "supported_encodings": ["angle", "amplitude"],
            "summary": "Quantum kernel SVM using a linear-entanglement ZZ feature map.",
            "strengths": "Good reference point for kernel-based quantum comparison.",
            "limitations": "Can underfit richer manifolds compared with deeper or classical models.",
        },
        "qsvc_zz_full": {
            "family": "quantum",
            "display_name": f"QSVM ZZ Kernel Full ({encoding})",
            "kernel_name": "Fidelity Quantum Kernel",
            "feature_map_name": "ZZFeatureMap",
            "feature_map_detail": "full entanglement",
            "ansatz_name": "none",
            "supported_encodings": ["angle"],
            "summary": "Quantum kernel SVM with denser ZZ entanglement across qubits.",
            "strengths": "Tests whether richer entanglement improves separability.",
            "limitations": "Higher circuit complexity and slower similarity evaluation.",
        },
        "qsvc_pauli": {
            "family": "quantum",
            "display_name": f"QSVM Pauli Kernel ({encoding})",
            "kernel_name": "Fidelity Quantum Kernel",
            "feature_map_name": "PauliFeatureMap",
            "feature_map_detail": "paulis=['Z','ZZ','XX']",
            "ansatz_name": "none",
            "supported_encodings": ["angle"],
            "summary": "Quantum kernel SVM using a Pauli feature map with mixed operators.",
            "strengths": "More expressive than plain ZZ kernels for research comparison.",
            "limitations": "More expensive and not always better on compact ROI datasets.",
        },
        "pegasos_qsvc": {
            "family": "quantum",
            "display_name": f"Pegasos QSVM ({encoding})",
            "kernel_name": "Pegasos Quantum Kernel",
            "feature_map_name": "ZZFeatureMap",
            "feature_map_detail": "linear entanglement",
            "ansatz_name": "none",
            "supported_encodings": ["angle"],
            "summary": "Pegasos large-margin optimizer on top of a quantum kernel.",
            "strengths": "Can be useful for binary quantum-kernel experiments.",
            "limitations": "Current implementation supports only binary classification.",
        },
        "vqc": {
            "family": "quantum",
            "display_name": f"VQC RealAmplitudes ({encoding})",
            "kernel_name": "variational",
            "feature_map_name": "ZZFeatureMap" if encoding == "angle" else "RawFeatureVector",
            "feature_map_detail": "trainable classifier",
            "ansatz_name": "RealAmplitudes",
            "supported_encodings": ["angle", "amplitude"],
            "summary": "Trainable variational quantum classifier with RealAmplitudes ansatz.",
            "strengths": "Directly optimizes a quantum decision surface instead of only a kernel.",
            "limitations": "Training is slower and more sensitive to hyperparameters.",
        },
        "vqc_real": {
            "family": "quantum",
            "display_name": f"VQC RealAmplitudes ({encoding})",
            "kernel_name": "variational",
            "feature_map_name": "ZZFeatureMap" if encoding == "angle" else "RawFeatureVector",
            "feature_map_detail": "trainable classifier",
            "ansatz_name": "RealAmplitudes",
            "supported_encodings": ["angle", "amplitude"],
            "summary": "Variational quantum classifier with RealAmplitudes ansatz.",
            "strengths": "Reasonable first trainable quantum classifier for presentations.",
            "limitations": "Optimization noise and local minima can reduce consistency.",
        },
        "vqc_efficient": {
            "family": "quantum",
            "display_name": f"VQC EfficientSU2 ({encoding})",
            "kernel_name": "variational",
            "feature_map_name": "ZZFeatureMap" if encoding == "angle" else "RawFeatureVector",
            "feature_map_detail": "trainable classifier",
            "ansatz_name": "EfficientSU2",
            "supported_encodings": ["angle", "amplitude"],
            "summary": "Variational quantum classifier with an EfficientSU2 ansatz.",
            "strengths": "Higher expressivity for studying trainable quantum circuits.",
            "limitations": "Usually slower and more complex than simpler VQC variants.",
        },
        "svc_rbf": {
            "family": "classical",
            "display_name": "Classical SVM (RBF)",
            "kernel_name": "rbf",
            "feature_map_name": "PCA feature encoder",
            "feature_map_detail": "classical baseline",
            "ansatz_name": "none",
            "supported_encodings": ["n/a"],
            "summary": "Strong classical large-margin baseline on engineered ROI features.",
            "strengths": "Usually very strong on compact, well-separated feature spaces.",
            "limitations": "No quantum component, so it serves as the bar to beat.",
        },
        "random_forest": {
            "family": "classical",
            "display_name": "Random Forest",
            "kernel_name": "ensemble trees",
            "feature_map_name": "PCA feature encoder",
            "feature_map_detail": "classical baseline",
            "ansatz_name": "none",
            "supported_encodings": ["n/a"],
            "summary": "Tree-ensemble baseline using the same classical ROI features.",
            "strengths": "Robust and interpretable feature-importance style baseline.",
            "limitations": "Can plateau on subtle visual differences compared with SVM/MLP.",
        },
        "logreg": {
            "family": "classical",
            "display_name": "Logistic Regression",
            "kernel_name": "linear",
            "feature_map_name": "PCA feature encoder",
            "feature_map_detail": "classical baseline",
            "ansatz_name": "none",
            "supported_encodings": ["n/a"],
            "summary": "Linear classical baseline for a clean performance floor.",
            "strengths": "Fast to train and easy to explain to non-technical audiences.",
            "limitations": "Limited nonlinear capacity compared with richer baselines.",
        },
        "mlp": {
            "family": "classical",
            "display_name": "MLP Classifier",
            "kernel_name": "neural network",
            "feature_map_name": "PCA feature encoder",
            "feature_map_detail": "classical baseline",
            "ansatz_name": "none",
            "supported_encodings": ["n/a"],
            "summary": "Compact neural baseline over ROI feature vectors.",
            "strengths": "Can model nonlinearities without quantum overhead.",
            "limitations": "Still depends entirely on classical feature engineering.",
        },
    }
    return descriptions.get(
        normalized,
        {
            "family": "quantum" if is_quantum_model(normalized) else "classical",
            "display_name": normalized,
            "kernel_name": "unknown",
            "feature_map_name": "unknown",
            "feature_map_detail": "unknown",
            "ansatz_name": "unknown",
            "supported_encodings": ["angle", "amplitude"],
            "summary": "No catalog description available.",
            "strengths": "Unknown",
            "limitations": "Unknown",
        },
    )


def get_supported_model_catalog() -> list[dict[str, object]]:
    catalog: list[dict[str, object]] = []
    for model_type in MODEL_ORDER:
        description = describe_classifier_model(model_type, "angle")
        catalog.append(
            {
                "model_type": model_type,
                "family": description["family"],
                "display_name": description["display_name"],
                "kernel_name": description["kernel_name"],
                "feature_map_name": description["feature_map_name"],
                "feature_map_detail": description["feature_map_detail"],
                "ansatz_name": description["ansatz_name"],
                "supported_encodings": description["supported_encodings"],
                "summary": description["summary"],
                "strengths": description["strengths"],
                "limitations": description["limitations"],
            }
        )
    return catalog


@dataclass
class ClassicalFeatureEncoder:
    config: QuantumClassifierConfig
    scaler: StandardScaler | None = None
    variance_filter: VarianceThreshold | None = None
    selector: SelectKBest | None = None
    reducer: PCA | None = None

    def fit(self, features: np.ndarray, labels: np.ndarray) -> "ClassicalFeatureEncoder":
        self.scaler = StandardScaler()
        scaled = self.scaler.fit_transform(features)
        if scaled.shape[1] > 1:
            self.variance_filter = VarianceThreshold(threshold=0.0)
            selected = self.variance_filter.fit_transform(scaled)
        else:
            self.variance_filter = None
            selected = scaled
        selector_k = min(self.config.preselect_dim, selected.shape[1])
        if selector_k > 0 and selector_k < selected.shape[1]:
            self.selector = SelectKBest(score_func=f_classif, k=selector_k)
            selected = self.selector.fit_transform(selected, labels)
        else:
            self.selector = None
        target_dim = min(self.config.classical_feature_dim, selected.shape[0], selected.shape[1])
        if target_dim > 0 and target_dim < selected.shape[1]:
            self.reducer = PCA(n_components=target_dim, random_state=self.config.random_state)
            self.reducer.fit(selected)
        else:
            self.reducer = None
        return self

    def transform(self, features: np.ndarray) -> np.ndarray:
        if self.scaler is None:
            raise RuntimeError("Classical encoder must be fitted before calling transform().")
        transformed = self.scaler.transform(features)
        if self.variance_filter is not None:
            transformed = self.variance_filter.transform(transformed)
        if self.selector is not None:
            transformed = self.selector.transform(transformed)
        if self.reducer is not None:
            transformed = self.reducer.transform(transformed)
        return transformed.astype(np.float32)

    def fit_transform(self, features: np.ndarray, labels: np.ndarray) -> np.ndarray:
        self.fit(features, labels)
        return self.transform(features)


class BaseHybridQuantumClassifier(ABC):
    def __init__(self, config: QuantumClassifierConfig) -> None:
        self.config = config
        self.label_encoder = LabelEncoder().fit(config.class_names)
        self.model = None

    @property
    def model_type(self) -> str:
        return str(self.config.model_type)

    @property
    def model_family(self) -> str:
        return "quantum" if is_quantum_model(self.model_type) else "classical"

    @property
    def model_display_name(self) -> str:
        description = describe_classifier_model(self.model_type, self.config.encoding)
        return str(description["display_name"])

    @abstractmethod
    def fit(self, features: np.ndarray, labels: list[str] | np.ndarray) -> "BaseHybridQuantumClassifier":
        raise NotImplementedError

    @abstractmethod
    def predict(self, features: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def save(self, artifact_path: str | Path | None = None) -> Path:
        target = Path(artifact_path or self.config.artifact_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            pickle.dump(self, handle)
        return target

    @classmethod
    def load(cls, artifact_path: str | Path) -> "BaseHybridQuantumClassifier":
        with Path(artifact_path).open("rb") as handle:
            return pickle.load(handle)


class QuantumKernelSVMClassifier(BaseHybridQuantumClassifier):
    def __init__(self, config: QuantumClassifierConfig) -> None:
        super().__init__(config)
        self.encoder = ClassicalToQuantumEncoder(config)

    def fit(self, features: np.ndarray, labels: list[str] | np.ndarray) -> "QuantumKernelSVMClassifier":
        encoded_labels = self.label_encoder.transform(np.asarray(labels))
        quantum_inputs = self.encoder.fit_transform(np.asarray(features, dtype=np.float32), encoded_labels)
        feature_map = build_feature_map(self.config)
        quantum_kernel = FidelityStatevectorKernel(feature_map=feature_map)
        if self.config.model_type == "pegasos_qsvc":
            if len(np.unique(encoded_labels)) != 2:
                raise ValueError("PegasosQSVC only supports binary classification datasets.")
            self.model = PegasosQSVC(
                quantum_kernel=quantum_kernel,
                C=10.0,
                num_steps=max(1000, int(quantum_inputs.shape[0] * 3)),
                seed=self.config.random_state,
            )
        else:
            self.model = QSVC(quantum_kernel=quantum_kernel)
        self.model.fit(quantum_inputs, encoded_labels)
        return self

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model must be fitted or loaded before calling predict().")
        quantum_inputs = self.encoder.transform(np.asarray(features, dtype=np.float32))
        predicted_indices = self.model.predict(quantum_inputs)
        return self.label_encoder.inverse_transform(np.asarray(predicted_indices).astype(int))


class VariationalQuantumClassifier(BaseHybridQuantumClassifier):
    def __init__(self, config: QuantumClassifierConfig) -> None:
        super().__init__(config)
        self.encoder = ClassicalToQuantumEncoder(config)

    def fit(self, features: np.ndarray, labels: list[str] | np.ndarray) -> "VariationalQuantumClassifier":
        encoded_labels = self.label_encoder.transform(np.asarray(labels))
        quantum_inputs = self.encoder.fit_transform(np.asarray(features, dtype=np.float32), encoded_labels)
        feature_map = build_feature_map(self.config)
        ansatz = build_ansatz(self.config)
        sampler = StatevectorSampler()
        self.model = VQC(
            feature_map=feature_map,
            ansatz=ansatz,
            loss="cross_entropy",
            optimizer=COBYLA(maxiter=self.config.maxiter),
            sampler=sampler,
            interpret=MulticlassInterpret(num_classes=len(self.config.class_names)),
            output_shape=len(self.config.class_names),
        )
        self.model.fit(
            quantum_inputs,
            one_hot(encoded_labels, num_classes=len(self.config.class_names)),
        )
        return self

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model must be fitted or loaded before calling predict().")
        quantum_inputs = self.encoder.transform(np.asarray(features, dtype=np.float32))
        raw_predictions = self.model.predict(quantum_inputs)
        predicted_indices = decode_predictions(raw_predictions)
        return self.label_encoder.inverse_transform(predicted_indices.astype(int))


class BaseClassicalClassifier(BaseHybridQuantumClassifier):
    def __init__(self, config: QuantumClassifierConfig) -> None:
        super().__init__(config)
        self.encoder = ClassicalFeatureEncoder(config)

    @abstractmethod
    def build_model(self) -> object:
        raise NotImplementedError

    def fit(self, features: np.ndarray, labels: list[str] | np.ndarray) -> "BaseClassicalClassifier":
        encoded_labels = self.label_encoder.transform(np.asarray(labels))
        transformed = self.encoder.fit_transform(np.asarray(features, dtype=np.float32), encoded_labels)
        self.model = self.build_model()
        self.model.fit(transformed, encoded_labels)
        return self

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model must be fitted or loaded before calling predict().")
        transformed = self.encoder.transform(np.asarray(features, dtype=np.float32))
        predicted_indices = self.model.predict(transformed)
        return self.label_encoder.inverse_transform(np.asarray(predicted_indices).astype(int))


class ClassicalSVMClassifier(BaseClassicalClassifier):
    def build_model(self) -> object:
        return SVC(C=6.0, gamma="scale", kernel="rbf")


class RandomForestROIClassifier(BaseClassicalClassifier):
    def build_model(self) -> object:
        return RandomForestClassifier(
            n_estimators=400,
            max_depth=None,
            min_samples_leaf=1,
            random_state=self.config.random_state,
            n_jobs=1,
        )


class LogisticRegressionROIClassifier(BaseClassicalClassifier):
    def build_model(self) -> object:
        return LogisticRegression(
            max_iter=1500,
            C=2.0,
            random_state=self.config.random_state,
        )


class MLPROIClassifier(BaseClassicalClassifier):
    def build_model(self) -> object:
        return MLPClassifier(
            hidden_layer_sizes=(256, 128),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            batch_size=64,
            learning_rate_init=1e-3,
            max_iter=600,
            early_stopping=True,
            n_iter_no_change=20,
            random_state=self.config.random_state,
        )


def build_classifier(config: QuantumClassifierConfig) -> BaseHybridQuantumClassifier:
    if config.model_type in QUANTUM_KERNEL_MODEL_TYPES:
        return QuantumKernelSVMClassifier(config)
    if config.model_type in VQC_MODEL_TYPES:
        return VariationalQuantumClassifier(config)
    if config.model_type == "svc_rbf":
        return ClassicalSVMClassifier(config)
    if config.model_type == "random_forest":
        return RandomForestROIClassifier(config)
    if config.model_type == "logreg":
        return LogisticRegressionROIClassifier(config)
    if config.model_type == "mlp":
        return MLPROIClassifier(config)
    raise ValueError(f"Unsupported classifier model type: {config.model_type}")
