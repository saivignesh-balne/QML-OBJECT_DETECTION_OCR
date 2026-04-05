from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

DetectorBackend = Literal["yolo", "faster_rcnn"]
QuantumEncoding = Literal["angle", "amplitude"]
ClassifierModelType = Literal[
    "qsvc",
    "qsvc_zz_linear",
    "qsvc_zz_full",
    "qsvc_pauli",
    "pegasos_qsvc",
    "vqc",
    "vqc_real",
    "vqc_efficient",
    "svc_rbf",
    "random_forest",
    "logreg",
    "mlp",
]
OCRBackend = Literal["tesseract", "trocr", "ensemble"]


@dataclass
class DetectorConfig:
    backend: DetectorBackend = "yolo"
    weights_path: str | Path = "weights/yolo_custom.pt"
    confidence_threshold: float = 0.35
    image_size: int = 960
    device: str = "cpu"
    max_detections: int = 32


@dataclass
class FeatureExtractorConfig:
    use_cnn_embeddings: bool = True
    use_hog: bool = True
    use_lbp: bool = True
    use_color_histogram: bool = True
    cnn_backbone: str = "resnet18"
    device: str = "cpu"
    image_size: tuple[int, int] = (224, 224)


@dataclass
class QuantumClassifierConfig:
    class_names: list[str]
    model_type: ClassifierModelType = "qsvc"
    encoding: QuantumEncoding = "angle"
    n_qubits: int = 6
    feature_map_reps: int = 2
    ansatz_reps: int = 2
    maxiter: int = 50
    random_state: int = 42
    preselect_dim: int = 256
    classical_feature_dim: int = 128
    artifact_path: str | Path = "artifacts/hybrid_qml_classifier.pkl"


@dataclass
class OCRConfig:
    backend: OCRBackend = "ensemble"
    tesseract_cmd: str | None = None
    tesseract_psm: int = 6
    trocr_model_name: str = "microsoft/trocr-base-printed"
    device: str = "cpu"
    max_new_tokens: int = 64


@dataclass
class OutputConfig:
    save_visualization: bool = True
    output_dir: str | Path = "outputs"


@dataclass
class PipelineConfig:
    class_names: list[str] = field(
        default_factory=lambda: ["chip_packet", "medicine_box", "bottle"]
    )
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    features: FeatureExtractorConfig = field(default_factory=FeatureExtractorConfig)
    classifier: QuantumClassifierConfig | None = None
    ocr: OCRConfig = field(default_factory=OCRConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def __post_init__(self) -> None:
        if self.classifier is None:
            self.classifier = QuantumClassifierConfig(class_names=list(self.class_names))
