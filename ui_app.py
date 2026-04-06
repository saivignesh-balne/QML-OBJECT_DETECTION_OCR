from __future__ import annotations

import base64
import importlib
import json
import numpy as np
import re
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
WEIGHTS_DIR = PROJECT_ROOT / "weights"
RUNS_DIR = PROJECT_ROOT / "runs"
UPLOAD_DIR = PROJECT_ROOT / "ui_uploads"
OUTPUT_DIR = PROJECT_ROOT / "ui_outputs"
BENCHMARK_REPORT_PATH = ARTIFACTS_DIR / "benchmark_report.json"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
SUPPORTED_CLASSES = ["chip_packet", "medicine_box", "bottle"]

for directory in (ARTIFACTS_DIR, WEIGHTS_DIR, UPLOAD_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)


@dataclass
class DependencyStatus:
    name: str
    available: bool
    detail: str


@dataclass
class ArtifactInventory:
    detector_weights: list[dict[str, str]]
    classifier_artifacts: list[dict[str, str]]
    benchmark_report: str | None


@dataclass
class PipelineRecommendation:
    ready: bool
    mode: str
    source: str
    detector_backend: str | None
    detector_weights: str | None
    classifier_artifact: str | None
    classifier_name: str
    classifier_family: str
    ocr_backend: str
    notes: list[str]


@dataclass
class TrainingState:
    training: bool = False
    job_type: str = ""
    title: str = ""
    started_at: float = 0.0
    return_code: int | None = None
    active_item: str = ""
    progress_current: int = 0
    progress_total: int = 0
    progress_status: str = ""
    status_messages: list[str] | None = None

    def __post_init__(self) -> None:
        if self.status_messages is None:
            self.status_messages = []


PROJECT_BRIEF = {
    "executive_summary": {
        "title": "Executive Summary",
        "points": [
            "This project is a QML object-detection research and development platform with detection, classification, OCR, and benchmarking in one workflow.",
            "The current benchmark domain uses bottles, chip packets, and medicine boxes as experimental object classes, not as the project definition itself.",
            "The main research question is which approach gives the best tradeoff between accuracy, cost, speed, and innovation value when classical and hybrid quantum models are compared fairly.",
        ],
    },
    "problem_statement": {
        "title": "Problem Statement",
        "points": [
            "Real object-detection images are visually noisy: lighting changes, reflections, cluttered backgrounds, and small printed text all reduce reliability.",
            "A useful solution must localize the object, classify it correctly, and extract readable text while staying measurable enough for research comparison.",
            "Because raw images are high-dimensional, any realistic quantum experiment in this domain must currently be hybrid rather than purely quantum.",
        ],
    },
    "approach_definitions": {
        "title": "Approach Definitions",
        "points": [
            "Classical: the full decision path stays in standard machine learning, using engineered ROI features and classical classifiers such as SVM, Random Forest, Logistic Regression, or MLP.",
            "Hybrid Quantum: classical preprocessing and feature extraction remain, but the final decision model uses a quantum kernel or variational circuit on a compressed feature space.",
            "Pure Quantum: an end-to-end quantum image pipeline would try to encode and classify the image directly in quantum space, which is not practical for this project today.",
        ],
    },
    "quantum_value": {
        "title": "Why Hybrid Quantum Is Worth Testing",
        "points": [
            "Quantum kernels can capture nonlinear similarity relationships that may be difficult to express with simpler classical boundaries.",
            "Hybrid quantum models give the project a research dimension without replacing the reliable classical vision and OCR components that are needed in practice.",
            "Even when quantum is not the top production choice, it still provides measurable comparison value and helps answer whether quantum adds signal on this dataset.",
        ],
    },
    "quantum_limits": {
        "title": "Where Quantum Still Falls Short",
        "points": [
            "Quantum models still depend on classical preprocessing because current qubit counts are too limited for raw image inputs at useful resolution.",
            "Training and simulation cost can be higher, while gains are not guaranteed against strong classical baselines.",
            "A hybrid or quantum result is only meaningful if it improves accuracy, robustness, interpretability, or strategic differentiation enough to justify the added complexity.",
        ],
    },
    "decision_guidance": {
        "title": "What Is Better To Do",
        "points": [
            "For immediate deployment, use the top benchmark winner from the UI because it is selected from measured accuracy, macro F1, and runtime data.",
            "For research presentation, position the hybrid quantum pipeline as an innovation track that is compared fairly against strong classical baselines rather than assumed to be better.",
            "For long-term improvement, keep the detector and OCR production-ready while continuing quantum experiments only if they provide a clear measurable advantage.",
        ],
    },
    "manager_talking_points": {
        "title": "Manager Talking Points",
        "points": [
            "The UI saves trained artifacts and benchmark summaries, so results are reusable and reproducible instead of requiring retraining every session.",
            "All model families are evaluated on the same ROI dataset and benchmark logic, which makes the comparison defensible in a review meeting.",
            "The final output is presentation-ready: one clean full-image result, extracted text, benchmarking charts, and a table comparing all evaluated models.",
        ],
    },
    "comparison_method": {
        "title": "How To Read The Comparison",
        "points": [
            "Classical, hybrid quantum, and quantum-oriented models all consume the same ROI feature extractor so the benchmark is more fair than comparing unrelated pipelines.",
            "Benchmark accuracy and macro F1 come from the same held-out split, while runtime charts come from the live uploaded image analyzed in the UI.",
            "If a classical model wins, that is still a strong outcome because it defines the real production baseline that any quantum approach must beat or complement.",
        ],
    },
    "approach_comparison": {
        "title": "Approach Comparison",
        "columns": ["Approach", "How It Works Here", "Advantages", "Disadvantages", "Best Use"],
        "rows": [
            {
                "approach": "Classical",
                "how": "OpenCV preprocessing + ROI features + classical classifier",
                "advantages": "Fast, strong baselines, easier to explain, easier to deploy",
                "disadvantages": "Less research novelty, may miss value of quantum-style similarity learning",
                "best_use": "Best current production candidate",
            },
            {
                "approach": "Hybrid Quantum",
                "how": "Classical preprocessing + compressed features + quantum kernel or VQC classifier",
                "advantages": "Good innovation story, realistic near-term quantum setup, fair research comparison",
                "disadvantages": "More complexity, slower training, benefit must be proven",
                "best_use": "Best research and innovation track",
            },
            {
                "approach": "Pure Quantum",
                "how": "Direct quantum image encoding and decision making",
                "advantages": "High novelty and long-term vision value",
                "disadvantages": "Not practical for this image pipeline today because of dimensionality and hardware limits",
                "best_use": "Conceptual future direction only",
            },
        ],
    },
}


app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "ui_templates"),
    static_folder=str(PROJECT_ROOT / "ui_static"),
)
app.config["SECRET_KEY"] = "hybrid-qml-ocr-ui"
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
_RUNTIME_CACHE: dict[tuple[str, ...], Any] = {}
_TRAINING_LOCK = threading.RLock()
_TRAINING_STATE = TrainingState()
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def safe_import(module_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        normalized = str(path.resolve(strict=False))
        if normalized not in seen:
            seen.add(normalized)
            unique.append(path)
    return unique


def build_path_candidates(raw_value: str, base_paths: list[Path]) -> list[Path]:
    cleaned = raw_value.strip().strip("'\"")
    if not cleaned:
        return []
    raw_path = Path(cleaned)
    if raw_path.is_absolute():
        return [raw_path]
    return unique_paths([(base / raw_path).resolve() for base in base_paths])


def load_yaml_mapping(yaml_path: Path) -> dict[str, Any]:
    text = yaml_path.read_text(encoding="utf-8")
    try:
        yaml_mod = importlib.import_module("yaml")
        payload = yaml_mod.safe_load(text) or {}
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass

    mapping: dict[str, Any] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        mapping[key.strip()] = value.strip().strip("'\"")
    return mapping


def pick_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def count_files_by_suffix(directory: Path | None, suffixes: set[str]) -> int:
    if directory is None or not directory.exists() or not directory.is_dir():
        return 0
    return sum(1 for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def derive_label_dir(image_dir: Path | None) -> Path | None:
    if image_dir is None:
        return None
    parts = list(image_dir.parts)
    if "images" in parts:
        index = parts.index("images")
        return Path(*parts[:index], "labels", *parts[index + 1 :])
    if image_dir.parent.exists():
        return image_dir.parent.parent / "labels" / image_dir.name
    return None


def inspect_detector_dataset(dataset_yaml_value: str | None = None) -> dict[str, Any]:
    dataset_yaml_input = (dataset_yaml_value or suggested_paths()["detector_dataset_yaml"]).strip()
    dataset_yaml_path = resolve_project_path(dataset_yaml_input)
    status: dict[str, Any] = {
        "dataset_yaml": str(dataset_yaml_path),
        "yaml_exists": dataset_yaml_path.exists(),
        "root_dir": "",
        "train_dir": "",
        "val_dir": "",
        "train_labels_dir": "",
        "val_labels_dir": "",
        "train_images": 0,
        "val_images": 0,
        "train_labels": 0,
        "val_labels": 0,
        "ready": False,
        "message": "",
    }

    if not dataset_yaml_path.exists():
        status["message"] = (
            f"Detector dataset YAML was not found at {dataset_yaml_path}. "
            "Skip detector training for now, or add a full YOLO scene dataset before retrying."
        )
        return status

    dataset_config = load_yaml_mapping(dataset_yaml_path)
    root_raw = str(dataset_config.get("path", "") or "").strip()
    root_candidates = (
        build_path_candidates(root_raw, [PROJECT_ROOT, dataset_yaml_path.parent])
        if root_raw
        else [dataset_yaml_path.parent.resolve()]
    )
    root_dir = pick_existing_path(root_candidates)
    train_dir = pick_existing_path(
        build_path_candidates(
            str(dataset_config.get("train", "") or ""),
            [root_dir or PROJECT_ROOT, PROJECT_ROOT, dataset_yaml_path.parent],
        )
    )
    val_dir = pick_existing_path(
        build_path_candidates(
            str(dataset_config.get("val", "") or ""),
            [root_dir or PROJECT_ROOT, PROJECT_ROOT, dataset_yaml_path.parent],
        )
    )
    train_labels_dir = derive_label_dir(train_dir)
    val_labels_dir = derive_label_dir(val_dir)
    train_images = count_files_by_suffix(train_dir, ALLOWED_EXTENSIONS)
    val_images = count_files_by_suffix(val_dir, ALLOWED_EXTENSIONS)
    train_labels = count_files_by_suffix(train_labels_dir, {".txt"})
    val_labels = count_files_by_suffix(val_labels_dir, {".txt"})

    status.update(
        {
            "root_dir": str(root_dir) if root_dir else "",
            "train_dir": str(train_dir) if train_dir else "",
            "val_dir": str(val_dir) if val_dir else "",
            "train_labels_dir": str(train_labels_dir) if train_labels_dir else "",
            "val_labels_dir": str(val_labels_dir) if val_labels_dir else "",
            "train_images": train_images,
            "val_images": val_images,
            "train_labels": train_labels,
            "val_labels": val_labels,
        }
    )

    if train_images == 0 or val_images == 0:
        status["message"] = (
            "Detector training is blocked because the YOLO scene dataset is empty. "
            "Add full-image training photos to data/detection/images/train and data/detection/images/val, "
            "or skip this step and use ROI classifier mode."
        )
        return status
    if train_labels == 0 or val_labels == 0:
        status["message"] = (
            "Detector images were found, but YOLO label .txt files are missing in labels/train or labels/val. "
            "Each full-scene image needs a matching bounding-box label file before detector training can start."
        )
        return status

    status["ready"] = True
    status["message"] = (
        f"Detector dataset ready: {train_images} train images, {val_images} val images, "
        f"{train_labels} train labels, {val_labels} val labels."
    )
    return status


def inspect_classifier_dataset(dataset_dir_value: str | None = None) -> dict[str, Any]:
    dataset_dir_input = (dataset_dir_value or suggested_paths()["classifier_dataset_dir"]).strip()
    dataset_dir = resolve_project_path(dataset_dir_input)
    class_counts = {
        class_name: count_files_by_suffix(dataset_dir / class_name, ALLOWED_EXTENSIONS)
        for class_name in SUPPORTED_CLASSES
    }
    missing_classes = [class_name for class_name, count in class_counts.items() if count == 0]
    total_images = sum(class_counts.values())
    ready = dataset_dir.exists() and not missing_classes and total_images > 0

    if not dataset_dir.exists():
        message = f"ROI dataset folder was not found at {dataset_dir}. Add cropped images before training the classifier."
    elif missing_classes:
        missing_display = ", ".join(missing_classes)
        message = (
            f"ROI dataset is incomplete. Add cropped images for: {missing_display}. "
            "Each image should mostly contain a single bottle, chip packet, or medicine box."
        )
    else:
        message = f"ROI classifier dataset ready with {total_images} cropped images across {len(SUPPORTED_CLASSES)} classes."

    return {
        "dataset_dir": str(dataset_dir),
        "class_counts": class_counts,
        "total_images": total_images,
        "ready": ready,
        "message": message,
    }


def collect_dependency_status() -> list[DependencyStatus]:
    dependency_specs = [
        ("Flask", "flask"),
        ("OpenCV", "cv2"),
        ("PyTorch", "torch"),
        ("Torchvision", "torchvision"),
        ("Ultralytics", "ultralytics"),
        ("Qiskit", "qiskit"),
        ("Qiskit ML", "qiskit_machine_learning"),
        ("Transformers", "transformers"),
        ("pytesseract", "pytesseract"),
    ]
    statuses: list[DependencyStatus] = []
    for label, module_name in dependency_specs:
        available, detail = safe_import(module_name)
        statuses.append(DependencyStatus(name=label, available=available, detail=detail))
    try:
        pytesseract = importlib.import_module("pytesseract")
        version = str(pytesseract.get_tesseract_version())
        statuses.append(DependencyStatus(name="Tesseract Binary", available=True, detail=version))
    except Exception as exc:
        statuses.append(DependencyStatus(name="Tesseract Binary", available=False, detail=str(exc)))
    return statuses


def discover_inventory() -> ArtifactInventory:
    detector_weights: list[dict[str, str]] = []
    detector_candidates = list(WEIGHTS_DIR.glob("*.pt")) + list(ARTIFACTS_DIR.glob("*.pt"))
    detector_candidates += list(RUNS_DIR.glob("**/weights/best.pt"))
    detector_candidates += list(RUNS_DIR.glob("**/weights/last.pt"))
    seen_detector_paths: set[str] = set()
    for path in sorted(detector_candidates):
        resolved = str(path.resolve())
        if resolved in seen_detector_paths:
            continue
        seen_detector_paths.add(resolved)
        name = path.name.lower()
        backend = "faster_rcnn" if "faster" in name else "yolo"
        detector_weights.append(
            {
                "name": str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else path.name,
                "path": str(path),
                "backend": backend,
            }
        )
    classifier_artifacts = [
        {"name": path.name, "path": str(path)}
        for path in sorted(ARTIFACTS_DIR.glob("*.pkl"))
    ]
    benchmark_report = str(BENCHMARK_REPORT_PATH) if BENCHMARK_REPORT_PATH.exists() else None
    return ArtifactInventory(
        detector_weights=detector_weights,
        classifier_artifacts=classifier_artifacts,
        benchmark_report=benchmark_report,
    )


def load_benchmark_report() -> dict[str, Any]:
    if not BENCHMARK_REPORT_PATH.exists():
        return {}
    try:
        return json.loads(BENCHMARK_REPORT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_classifier_summary_for_artifact(artifact_path: str | None) -> dict[str, Any]:
    if not artifact_path:
        return {}
    artifact_resolved = str(resolve_project_path(artifact_path))
    for path in sorted(ARTIFACTS_DIR.glob("*.summary.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("kind") != "classifier":
            continue
        summary_artifact = str(resolve_project_path(str(payload.get("artifact_path", ""))))
        if summary_artifact == artifact_resolved:
            return payload
    return {}


def load_classifier_summaries() -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for path in sorted(ARTIFACTS_DIR.glob("*.summary.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("kind") == "classifier":
            summaries.append(payload)
    return summaries


def build_model_catalog() -> list[dict[str, Any]]:
    hybrid_models_mod = importlib.import_module("hybrid_qml_ocr.hybrid_models")
    return hybrid_models_mod.get_supported_model_catalog()


def build_available_classifier_entries(
    inventory: ArtifactInventory,
    benchmark_report: dict[str, Any],
    recommended_artifact: str | None = None,
) -> list[dict[str, Any]]:
    hybrid_models_mod = importlib.import_module("hybrid_qml_ocr.hybrid_models")
    describe_classifier_model = hybrid_models_mod.describe_classifier_model

    benchmark_rows: dict[str, dict[str, Any]] = {}
    for row in benchmark_report.get("classifier_benchmarks", []):
        artifact_path = str(row.get("artifact_path", "")).strip()
        if artifact_path:
            benchmark_rows[str(resolve_project_path(artifact_path))] = row

    entries: list[dict[str, Any]] = []
    recommended_resolved = str(resolve_project_path(recommended_artifact)) if recommended_artifact else ""
    for artifact in inventory.classifier_artifacts:
        artifact_resolved = str(resolve_project_path(artifact["path"]))
        summary = load_classifier_summary_for_artifact(artifact_resolved)
        benchmark_row = benchmark_rows.get(artifact_resolved, {})
        model_type = str(benchmark_row.get("model") or summary.get("model_type") or Path(artifact_resolved).stem)
        raw_encoding = str(benchmark_row.get("encoding") or summary.get("encoding") or "classical_projection")
        descriptor = describe_classifier_model(model_type, "angle" if raw_encoding == "classical_projection" else raw_encoding)
        model_family = str(
            benchmark_row.get("model_family")
            or summary.get("model_family")
            or descriptor.get("family")
            or infer_classifier_family(model_type)
        )
        entries.append(
            {
                "artifact_path": artifact_resolved,
                "artifact_name": artifact["name"],
                "summary_path": str(summary.get("summary_path", "")),
                "display_name": str(benchmark_row.get("name") or summary.get("model_name") or descriptor["display_name"]),
                "model_type": model_type,
                "model_family": model_family,
                "encoding": "n/a" if raw_encoding == "classical_projection" else raw_encoding,
                "n_qubits": int(benchmark_row.get("n_qubits") or summary.get("n_qubits") or 0),
                "accuracy": float(benchmark_row.get("accuracy", summary.get("accuracy", 0.0) or 0.0)),
                "macro_f1": float(benchmark_row.get("macro_f1", summary.get("macro_f1", 0.0) or 0.0)),
                "weighted_f1": float(benchmark_row.get("weighted_f1", summary.get("weighted_f1", 0.0) or 0.0)),
                "train_time_seconds": float(
                    benchmark_row.get("train_time_seconds", summary.get("train_time_seconds", 0.0) or 0.0)
                ),
                "kernel_name": str(benchmark_row.get("kernel_name") or summary.get("kernel_name") or descriptor["kernel_name"]),
                "feature_map_name": str(
                    benchmark_row.get("feature_map_name") or summary.get("feature_map_name") or descriptor["feature_map_name"]
                ),
                "feature_map_detail": str(
                    benchmark_row.get("feature_map_detail")
                    or summary.get("feature_map_detail")
                    or descriptor["feature_map_detail"]
                ),
                "ansatz_name": str(benchmark_row.get("ansatz_name") or summary.get("ansatz_name") or descriptor["ansatz_name"]),
                "summary": str(benchmark_row.get("summary") or summary.get("model_summary") or descriptor["summary"]),
                "strengths": str(
                    benchmark_row.get("strengths") or summary.get("model_strengths") or descriptor["strengths"]
                ),
                "limitations": str(
                    benchmark_row.get("limitations") or summary.get("model_limitations") or descriptor["limitations"]
                ),
                "recommended": artifact_resolved == recommended_resolved,
            }
        )
    entries.sort(
        key=lambda item: (
            float(item.get("accuracy", 0.0)),
            float(item.get("macro_f1", 0.0)),
            item.get("display_name", ""),
        ),
        reverse=True,
    )
    return entries


def infer_classifier_family(model_type: str | None) -> str:
    hybrid_models_mod = importlib.import_module("hybrid_qml_ocr.hybrid_models")
    return "quantum" if hybrid_models_mod.is_quantum_model(str(model_type or "").strip()) else "classical"


def sort_benchmark_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            float(row.get("accuracy", row.get("Accuracy", 0.0))),
            float(row.get("macro_f1", row.get("Macro F1", 0.0))),
        ),
        reverse=True,
    )


def choose_pipeline(inventory: ArtifactInventory, benchmark_report: dict[str, Any]) -> PipelineRecommendation:
    notes: list[str] = []
    recommended = benchmark_report.get("recommended_pipeline", {})
    detector_weights_raw = str(recommended.get("detector_weights") or "").strip()
    classifier_artifact_raw = str(recommended.get("classifier_artifact") or "").strip()
    detector_weights = str(resolve_project_path(detector_weights_raw)) if detector_weights_raw else None
    detector_backend = recommended.get("detector_backend")
    classifier_artifact = str(resolve_project_path(classifier_artifact_raw)) if classifier_artifact_raw else None
    classifier_name = recommended.get("classifier_name", "No classifier artifact available")
    classifier_family = str(recommended.get("classifier_family") or "unknown")
    source = "benchmark_report" if recommended else "best_available_default"

    available_detector_paths = {item["path"]: item for item in inventory.detector_weights}
    available_classifier_paths = {item["path"]: item for item in inventory.classifier_artifacts}

    if detector_weights not in available_detector_paths:
        yolo_candidates = [item for item in inventory.detector_weights if item["backend"] == "yolo"]
        detector_item = yolo_candidates[0] if yolo_candidates else (inventory.detector_weights[0] if inventory.detector_weights else None)
        detector_weights = detector_item["path"] if detector_item else None
        detector_backend = detector_item["backend"] if detector_item else None
        if detector_item is not None:
            notes.append("Using the first available detector weight because a benchmark-selected detector was not found.")
    if classifier_artifact not in available_classifier_paths:
        classifier_item = inventory.classifier_artifacts[0] if inventory.classifier_artifacts else None
        classifier_artifact = classifier_item["path"] if classifier_item else None
        classifier_name = classifier_item["name"] if classifier_item else "No classifier artifact available"
        if classifier_item is not None:
            notes.append("Using the first available classifier artifact because a benchmark-selected classifier was not found.")
    classifier_summary = load_classifier_summary_for_artifact(classifier_artifact)
    if classifier_summary:
        classifier_name = str(classifier_summary.get("model_name", classifier_name))
        classifier_family = str(
            classifier_summary.get("model_family")
            or infer_classifier_family(classifier_summary.get("model_type"))
            or classifier_family
        )

    if not benchmark_report:
        notes.append("Benchmark report not found. Accuracy leaderboard will populate after you add artifacts/benchmark_report.json.")

    if classifier_artifact is None:
        notes.append("No classifier artifact found. Train the ROI classifier and place the .pkl file in artifacts/.")
        mode = "unavailable"
        ready = False
    elif detector_weights is None:
        notes.append("No detector weight found. ROI upload mode is enabled, so you can still classify already-cropped single-object images.")
        detector_backend = "classifier_only_roi_mode"
        classifier_name = classifier_name or "ROI Classifier"
        mode = "classifier_only"
        ready = True
    else:
        mode = "full_pipeline"
        ready = True

    return PipelineRecommendation(
        ready=ready,
        mode=mode,
        source=source,
        detector_backend=detector_backend,
        detector_weights=detector_weights,
        classifier_artifact=classifier_artifact,
        classifier_name=classifier_name,
        classifier_family=classifier_family,
        ocr_backend=recommended.get("ocr_backend", "ensemble"),
        notes=notes,
    )


def build_recommendation_for_classifier(
    base_recommendation: PipelineRecommendation,
    classifier_entry: dict[str, Any] | None,
) -> PipelineRecommendation:
    if not classifier_entry:
        return base_recommendation
    mode = "classifier_only" if not base_recommendation.detector_weights else base_recommendation.mode
    detector_backend = (
        "classifier_only_roi_mode"
        if mode == "classifier_only"
        else base_recommendation.detector_backend
    )
    return PipelineRecommendation(
        ready=True,
        mode=mode,
        source="user_selected_model",
        detector_backend=detector_backend,
        detector_weights=base_recommendation.detector_weights if mode != "classifier_only" else None,
        classifier_artifact=str(classifier_entry["artifact_path"]),
        classifier_name=str(classifier_entry["display_name"]),
        classifier_family=str(classifier_entry["model_family"]),
        ocr_backend=base_recommendation.ocr_backend,
        notes=list(base_recommendation.notes) + [f'Using classifier override: {classifier_entry["display_name"]}.'],
    )


def resolve_inference_models(
    inventory: ArtifactInventory,
    benchmark_report: dict[str, Any],
    recommendation: PipelineRecommendation,
    inference_mode: str,
    classifier_artifact: str,
) -> tuple[PipelineRecommendation, list[dict[str, Any]], str]:
    available_models = build_available_classifier_entries(
        inventory,
        benchmark_report,
        recommended_artifact=recommendation.classifier_artifact,
    )
    if not available_models:
        return recommendation, [], "recommended"

    mode = str(inference_mode or "recommended").strip().lower()
    by_artifact = {str(item["artifact_path"]): item for item in available_models}
    recommended_model = by_artifact.get(str(resolve_project_path(recommendation.classifier_artifact))) if recommendation.classifier_artifact else None
    selected_model = by_artifact.get(str(resolve_project_path(classifier_artifact))) if classifier_artifact else None

    if mode == "all":
        primary = selected_model or recommended_model or available_models[0]
        ordered = [primary] + [item for item in available_models if item["artifact_path"] != primary["artifact_path"]]
        return build_recommendation_for_classifier(recommendation, primary), ordered, "all"
    if mode == "selected" and selected_model is not None:
        return build_recommendation_for_classifier(recommendation, selected_model), [selected_model], "selected"
    primary = recommended_model or selected_model or available_models[0]
    return build_recommendation_for_classifier(recommendation, primary), [primary], "recommended"


def image_to_data_uri(image: Any) -> str:
    cv2 = importlib.import_module("cv2")
    success, buffer = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("Unable to encode UI preview image.")
    return "data:image/png;base64," + base64.b64encode(buffer.tobytes()).decode("utf-8")


def wrap_overlay_text(text: str, width: int = 22) -> list[str]:
    words = text.split()
    if not words:
        return ["No label"]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines[:3]


def expand_bbox(
    box: tuple[int, int, int, int],
    image_shape: tuple[int, int] | tuple[int, int, int],
    padding_ratio: float = 0.04,
) -> tuple[int, int, int, int]:
    height, width = image_shape[:2]
    x1, y1, x2, y2 = box
    pad_x = int((x2 - x1) * padding_ratio)
    pad_y = int((y2 - y1) * padding_ratio)
    return (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(width, x2 + pad_x),
        min(height, y2 + pad_y),
    )


def estimate_text_boxes(roi_bgr: np.ndarray, preprocess_mod: Any) -> list[dict[str, object]]:
    if roi_bgr.size == 0:
        return []
    cv2 = importlib.import_module("cv2")
    binary = preprocess_mod.preprocess_roi_for_ocr(roi_bgr)
    border = 12
    scale = 3.0
    if binary.shape[0] > (2 * border) and binary.shape[1] > (2 * border):
        binary = binary[border:-border, border:-border]
    inverted = 255 - binary
    kernel_width = max(15, inverted.shape[1] // 18)
    kernel_height = max(3, inverted.shape[0] // 80)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, kernel_height))
    connected = cv2.morphologyEx(inverted, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    roi_height, roi_width = roi_bgr.shape[:2]
    min_area = max(120, int(roi_height * roi_width * 0.002))
    boxes: list[dict[str, object]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if (w * h) < min_area or w < 18 or h < 10:
            continue
        x1 = max(0, int(round(x / scale)))
        y1 = max(0, int(round(y / scale)))
        x2 = min(roi_width, int(round((x + w) / scale)))
        y2 = min(roi_height, int(round((y + h) / scale)))
        if x2 <= x1 or y2 <= y1:
            continue
        boxes.append(
            {
                "bbox": [x1, y1, x2, y2],
                "left": x1,
                "top": y1,
                "right": x2,
                "bottom": y2,
                "source": "estimated",
            }
        )
    boxes.sort(key=lambda item: (int(item["top"]), int(item["left"])))
    return boxes[:3]


def select_text_boxes(
    selected_ocr: Any,
    raw_ocr_results: list[Any],
    roi_bgr: np.ndarray,
    preprocess_mod: Any,
) -> list[dict[str, object]]:
    candidate_lists = [getattr(selected_ocr, "boxes", None)]
    candidate_lists.extend(getattr(result, "boxes", None) for result in raw_ocr_results)
    for candidate in candidate_lists:
        if not candidate:
            continue
        normalized: list[dict[str, object]] = []
        for box in candidate:
            bbox_values = box.get("bbox") if isinstance(box, dict) else None
            if not isinstance(bbox_values, list) or len(bbox_values) != 4:
                continue
            x1, y1, x2, y2 = [int(value) for value in bbox_values]
            if x2 <= x1 or y2 <= y1:
                continue
            normalized.append(
                {
                    "bbox": [x1, y1, x2, y2],
                    "left": x1,
                    "top": y1,
                    "right": x2,
                    "bottom": y2,
                    "source": str(box.get("source", "ocr")) if isinstance(box, dict) else "ocr",
                }
            )
        if normalized:
            return normalized
    if getattr(selected_ocr, "text", "").strip():
        return estimate_text_boxes(roi_bgr, preprocess_mod)
    return []


def project_text_boxes_to_image(
    text_boxes: list[dict[str, object]],
    roi_box: tuple[int, int, int, int],
    image_shape: tuple[int, int] | tuple[int, int, int],
) -> list[dict[str, object]]:
    image_height, image_width = image_shape[:2]
    roi_x1, roi_y1, _, _ = roi_box
    projected: list[dict[str, object]] = []
    for box in text_boxes:
        bbox_values = box.get("bbox")
        if not isinstance(bbox_values, list) or len(bbox_values) != 4:
            continue
        x1 = max(0, min(image_width, roi_x1 + int(bbox_values[0])))
        y1 = max(0, min(image_height, roi_y1 + int(bbox_values[1])))
        x2 = max(0, min(image_width, roi_x1 + int(bbox_values[2])))
        y2 = max(0, min(image_height, roi_y1 + int(bbox_values[3])))
        if x2 <= x1 or y2 <= y1:
            continue
        projected.append(
            {
                "bbox": [x1, y1, x2, y2],
                "left": x1,
                "top": y1,
                "right": x2,
                "bottom": y2,
                "source": box.get("source", "ocr"),
            }
        )
    return projected


def draw_result_summary_box(
    canvas: Any,
    anchor_box: tuple[int, int, int, int],
    object_label: str,
    extracted_text: str,
) -> None:
    cv2 = importlib.import_module("cv2")
    x1, y1, x2, y2 = anchor_box
    text_lines = [f"Label: {object_label}"] + wrap_overlay_text(f"Text: {extracted_text}", width=30)
    line_height = 22
    box_height = 12 + (len(text_lines) * line_height)
    max_line_length = max(len(line) for line in text_lines)
    box_width = min(max(250, max_line_length * 10), canvas.shape[1] - 8)
    left = min(max(4, x1), max(4, canvas.shape[1] - box_width - 4))
    top = y1 - box_height - 8
    if top < 4:
        top = min(max(4, y2 + 8), max(4, canvas.shape[0] - box_height - 4))
    cv2.rectangle(canvas, (left, top), (left + box_width, top + box_height), (255, 255, 255), -1)
    cv2.rectangle(canvas, (left, top), (left + box_width, top + box_height), (10, 158, 110), 2)
    for line_index, line in enumerate(text_lines):
        color = (10, 90, 70) if line_index == 0 else (30, 30, 30)
        scale = 0.6 if line_index == 0 else 0.5
        cv2.putText(
            canvas,
            line,
            (left + 8, top + 20 + (line_index * line_height)),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            2,
            cv2.LINE_AA,
        )


def save_uploaded_file(file_storage: Any) -> Path:
    suffix = Path(file_storage.filename).suffix.lower()
    filename = f"{uuid4().hex}{suffix}"
    target = UPLOAD_DIR / secure_filename(filename)
    file_storage.save(target)
    return target


def reset_training_state(job_type: str, title: str) -> None:
    with _TRAINING_LOCK:
        _TRAINING_STATE.training = True
        _TRAINING_STATE.job_type = job_type
        _TRAINING_STATE.title = title
        _TRAINING_STATE.started_at = time.time()
        _TRAINING_STATE.return_code = None
        _TRAINING_STATE.active_item = ""
        _TRAINING_STATE.progress_current = 0
        _TRAINING_STATE.progress_total = 0
        _TRAINING_STATE.progress_status = "starting"
        _TRAINING_STATE.status_messages = [f"Started {title}"]


def update_training_progress(
    *,
    active_item: str | None = None,
    progress_current: int | None = None,
    progress_total: int | None = None,
    progress_status: str | None = None,
) -> None:
    with _TRAINING_LOCK:
        if active_item is not None:
            _TRAINING_STATE.active_item = active_item
        if progress_current is not None:
            _TRAINING_STATE.progress_current = progress_current
        if progress_total is not None:
            _TRAINING_STATE.progress_total = progress_total
        if progress_status is not None:
            _TRAINING_STATE.progress_status = progress_status


def ingest_training_marker(message: str) -> bool:
    if message.startswith("SUITE_TOTAL|"):
        parts = message.split("|", 2)
        if len(parts) >= 3:
            try:
                total = int(parts[1])
            except ValueError:
                return True
            update_training_progress(progress_total=total, progress_status=f"suite profile: {parts[2]}")
        return True
    if message.startswith("SUITE_PROGRESS|"):
        parts = message.split("|", 4)
        if len(parts) == 5:
            try:
                current = int(parts[1])
                total = int(parts[2])
            except ValueError:
                return True
            slug = parts[3].replace("_", " ")
            state = parts[4]
            label_map = {
                "start": "training",
                "done": "completed",
                "failed": "failed",
            }
            update_training_progress(
                active_item=slug,
                progress_current=current,
                progress_total=total,
                progress_status=label_map.get(state, state),
            )
        return True
    if message.startswith("Reusing compatible classifier artifact:"):
        artifact_name = Path(message.split(":", 1)[1].strip()).stem.replace("_", " ")
        update_training_progress(active_item=artifact_name, progress_status="reused")
    elif message.startswith("Saved classifier artifact to:"):
        artifact_name = Path(message.split(":", 1)[1].strip()).stem.replace("_", " ")
        update_training_progress(active_item=artifact_name, progress_status="saved")
    elif message.startswith("Started Detector Training"):
        update_training_progress(active_item="detector", progress_status="training")
    elif message.startswith("Detector Training finished with exit code 0"):
        update_training_progress(active_item="detector", progress_status="completed")
    return False


def append_training_log(message: str) -> None:
    if ingest_training_marker(message):
        return
    with _TRAINING_LOCK:
        _TRAINING_STATE.status_messages.append(message)
        _TRAINING_STATE.status_messages = _TRAINING_STATE.status_messages[-80:]


def finish_training_state(return_code: int) -> None:
    with _TRAINING_LOCK:
        _TRAINING_STATE.training = False
        _TRAINING_STATE.return_code = return_code
        if return_code == 0 and _TRAINING_STATE.progress_total > 0:
            _TRAINING_STATE.progress_current = _TRAINING_STATE.progress_total
            if _TRAINING_STATE.progress_status not in {"reused", "saved"}:
                _TRAINING_STATE.progress_status = "completed"
        elif return_code != 0:
            _TRAINING_STATE.progress_status = "failed"


def get_training_state_payload() -> dict[str, Any]:
    with _TRAINING_LOCK:
        return {
            "training": _TRAINING_STATE.training,
            "job_type": _TRAINING_STATE.job_type,
            "title": _TRAINING_STATE.title,
            "started_at": _TRAINING_STATE.started_at,
            "return_code": _TRAINING_STATE.return_code,
            "active_item": _TRAINING_STATE.active_item,
            "progress_current": _TRAINING_STATE.progress_current,
            "progress_total": _TRAINING_STATE.progress_total,
            "progress_status": _TRAINING_STATE.progress_status,
            "status_messages": list(_TRAINING_STATE.status_messages or []),
        }


def start_background_job(
    job_type: str,
    title: str,
    command: list[str],
    *,
    active_item: str = "",
    progress_current: int = 0,
    progress_total: int = 0,
    progress_status: str = "starting",
) -> tuple[bool, str]:
    with _TRAINING_LOCK:
        if _TRAINING_STATE.training:
            return False, "Another training job is already running."
        reset_training_state(job_type, title)
        _TRAINING_STATE.active_item = active_item
        _TRAINING_STATE.progress_current = progress_current
        _TRAINING_STATE.progress_total = progress_total
        _TRAINING_STATE.progress_status = progress_status

    thread = threading.Thread(
        target=run_background_job,
        args=(job_type, title, command),
        daemon=True,
    )
    thread.start()
    return True, f"{title} started."


def run_streaming_command(command: list[str], title: str) -> int:
    append_training_log(f"Command: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        cleaned = ANSI_ESCAPE_RE.sub("", line).rstrip()
        if cleaned:
            append_training_log(cleaned)
    process.wait()
    append_training_log(f"{title} finished with exit code {process.returncode}.")
    return int(process.returncode)


def run_background_job(job_type: str, title: str, command: list[str]) -> None:
    try:
        return_code = run_streaming_command(command, title)
        if return_code == 0 and job_type in {"detector", "classifier", "suite"}:
            append_training_log("Refreshing benchmark report from newly generated summaries.")
            report_code = run_streaming_command(
                [sys.executable, "-u", "build_benchmark_report.py"],
                "Benchmark report refresh",
            )
            if report_code != 0:
                append_training_log("Benchmark report refresh failed. Check the logs above.")
        _RUNTIME_CACHE.clear()
        finish_training_state(return_code)
    except Exception as exc:
        append_training_log(str(exc))
        append_training_log(traceback.format_exc(limit=1))
        finish_training_state(1)


def suggested_paths() -> dict[str, str]:
    return {
        "detector_dataset_yaml": "data/custom_objects.yaml",
        "detector_base_model": "yolov8n.pt",
        "detector_project": "runs",
        "detector_name": "qml_ocr_detector",
        "classifier_dataset_dir": "data/roi_classifier",
        "classifier_artifact_path": "artifacts/hybrid_qml_classifier.pkl",
        "classifier_summary_path": "artifacts/hybrid_qml_classifier.summary.json",
        "classifier_suite_artifacts_dir": "artifacts",
    }


def ui_flow_steps() -> list[dict[str, str]]:
    return [
        {
            "title": "1. Prepare ROI Dataset",
            "text": "Put cropped single-object images into roi_classifier/chip_packet, roi_classifier/medicine_box, and roi_classifier/bottle.",
        },
        {
            "title": "2. Train Comparison Models",
            "text": "From the UI, train and compare classical baselines and hybrid quantum classifiers on the same ROI dataset.",
        },
        {
            "title": "3. Build Benchmarks",
            "text": "Generate the benchmark report so the UI can select the strongest available detector, classifier family, and OCR stack.",
        },
        {
            "title": "4. Run Inference",
            "text": "Upload a cropped image for ROI mode, or a full image after detector training. You can run the recommended model, pick a specific saved model, or compare all saved classifiers on the same upload.",
        },
        {
            "title": "5. Optional Full Detection Later",
            "text": "If you add YOLO detector data or weights, the same UI upgrades to full-scene detection while keeping the classifier comparison board.",
        },
    ]


def build_benchmark_context(benchmark_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "overall": sort_benchmark_rows(benchmark_report.get("leaderboard", benchmark_report.get("overall_leaderboard", []))),
        "detectors": sort_benchmark_rows(benchmark_report.get("detector_benchmarks", [])),
        "classifiers": sort_benchmark_rows(benchmark_report.get("classifier_benchmarks", [])),
        "ocr": sort_benchmark_rows(benchmark_report.get("ocr_benchmarks", [])),
        "family_summary": benchmark_report.get("classifier_family_summary", []),
        "charts": benchmark_report.get("chart_series", {}),
        "notes": benchmark_report.get("notes", []),
        "generated_at": benchmark_report.get("generated_at", ""),
        "has_report": bool(benchmark_report),
    }


def predict_label_for_classifier(
    classifier: Any,
    classifier_entry: dict[str, Any],
    feature_matrix: np.ndarray,
    num_views: int,
    supported_class_set: set[str],
) -> tuple[str, dict[str, Any], float]:
    started = time.perf_counter()
    view_predictions = classifier.predict(feature_matrix)
    runtime_ms = (time.perf_counter() - started) * 1000.0
    unique_labels, vote_counts = np.unique(view_predictions, return_counts=True)
    predicted_label = str(unique_labels[np.argmax(vote_counts)])
    object_label = predicted_label if predicted_label in supported_class_set else "unidentified object detected"
    summary = {
        "status": "completed",
        "model_name": classifier_entry.get("display_name", getattr(classifier, "model_display_name", "classifier")),
        "artifact_path": classifier_entry.get("artifact_path", ""),
        "model_type": getattr(classifier.config, "model_type", classifier_entry.get("model_type", "unknown")),
        "model_family": getattr(classifier, "model_family", classifier_entry.get("model_family", "unknown")),
        "encoding": classifier_entry.get("encoding", getattr(classifier.config, "encoding", "unknown")),
        "n_qubits": int(classifier_entry.get("n_qubits", getattr(classifier.config, "n_qubits", 0) or 0)),
        "kernel_name": classifier_entry.get("kernel_name", ""),
        "feature_map_name": classifier_entry.get("feature_map_name", ""),
        "ansatz_name": classifier_entry.get("ansatz_name", ""),
        "accuracy": float(classifier_entry.get("accuracy", 0.0)),
        "macro_f1": float(classifier_entry.get("macro_f1", 0.0)),
        "target_dimension": getattr(getattr(classifier, "encoder", None), "target_dim", "unknown"),
        "tta_views": num_views,
    }
    return object_label, summary, runtime_ms


def analyze_image(
    upload_path: Path,
    recommendation: PipelineRecommendation,
    classifier_entries: list[dict[str, Any]] | None = None,
    comparison_mode: str = "recommended",
) -> dict[str, Any]:
    if not recommendation.ready:
        raise RuntimeError("Inference is not ready yet. Add detector weights and a trained classifier artifact first.")

    cv2 = importlib.import_module("cv2")
    preprocess_mod = importlib.import_module("hybrid_qml_ocr.preprocess")

    selected_models = list(classifier_entries or [])
    if not selected_models and recommendation.classifier_artifact:
        selected_models = [
            {
                "artifact_path": recommendation.classifier_artifact,
                "display_name": recommendation.classifier_name,
                "model_family": recommendation.classifier_family,
                "model_type": "unknown",
                "encoding": "n/a",
                "n_qubits": 0,
                "accuracy": 0.0,
                "macro_f1": 0.0,
                "kernel_name": "",
                "feature_map_name": "",
                "ansatz_name": "",
            }
        ]
    if not selected_models:
        raise RuntimeError("No trained classifier artifacts are available for inference.")

    detector, feature_extractor, ocr_executor = get_shared_runtime_components(recommendation)
    runtime_classifiers = {
        str(model["artifact_path"]): get_classifier_for_artifact(str(model["artifact_path"]))
        for model in selected_models
    }

    total_started = time.perf_counter()
    preprocess_started = time.perf_counter()
    original = preprocess_mod.read_image(upload_path)
    preprocessed = preprocess_mod.preprocess_for_detection(original)
    preprocess_ms = (time.perf_counter() - preprocess_started) * 1000.0

    detect_started = time.perf_counter()
    if recommendation.mode == "classifier_only" or detector is None:
        height, width = preprocessed.contrast_bgr.shape[:2]
        detections = [{"label": "roi_upload", "confidence": 1.0, "bbox": (0, 0, width, height)}]
    else:
        detections = detector.detect(preprocessed.contrast_bgr)
    detect_ms = (time.perf_counter() - detect_started) * 1000.0

    classification_ms_values: list[float] = []
    ocr_ms_values: list[float] = []
    model_runtime_totals = {str(item["artifact_path"]): 0.0 for item in selected_models}
    model_predictions_overall = {str(item["artifact_path"]): [] for item in selected_models}
    roi_results: list[dict[str, Any]] = []
    supported_class_set = set(SUPPORTED_CLASSES)

    for detection in detections:
        bbox = detection["bbox"] if isinstance(detection, dict) else detection.bbox
        detector_label = detection["label"] if isinstance(detection, dict) else detection.label
        detector_confidence = detection["confidence"] if isinstance(detection, dict) else detection.confidence
        roi_box = expand_bbox(bbox, preprocessed.contrast_bgr.shape)
        roi = preprocess_mod.crop_roi(preprocessed.contrast_bgr, bbox)
        classification_views = preprocess_mod.build_classification_views(roi)
        feature_matrix = None
        model_predictions: list[dict[str, Any]] = []

        if recommendation.mode != "classifier_only" and detector_label not in supported_class_set:
            object_label = "unidentified object detected"
            quantum_summary = {
                "status": "skipped",
                "reason": "Detector output is outside the supported class list.",
            }
        else:
            feature_matrix = feature_extractor.encode_images(classification_views)
            for classifier_entry in selected_models:
                classifier = runtime_classifiers[str(classifier_entry["artifact_path"])]
                predicted_label, summary, runtime_ms = predict_label_for_classifier(
                    classifier=classifier,
                    classifier_entry=classifier_entry,
                    feature_matrix=feature_matrix,
                    num_views=len(classification_views),
                    supported_class_set=supported_class_set,
                )
                model_runtime_totals[str(classifier_entry["artifact_path"])] += runtime_ms
                model_predictions_overall[str(classifier_entry["artifact_path"])].append(predicted_label)
                model_predictions.append(
                    {
                        **summary,
                        "prediction": predicted_label,
                        "runtime_ms": round(runtime_ms, 2),
                        "is_primary": str(classifier_entry["artifact_path"]) == str(selected_models[0]["artifact_path"]),
                    }
                )
            classification_ms = float(sum(item["runtime_ms"] for item in model_predictions))
            classification_ms_values.append(classification_ms)
            primary_prediction = next((item for item in model_predictions if item["is_primary"]), model_predictions[0])
            object_label = primary_prediction["prediction"]
            quantum_summary = primary_prediction

        ocr_started = time.perf_counter()
        selected_ocr, raw_ocr_results = ocr_executor.run(roi)
        ocr_ms = (time.perf_counter() - ocr_started) * 1000.0
        ocr_ms_values.append(ocr_ms)

        extracted_text = selected_ocr.text.strip() if selected_ocr.text else ""
        roi_text_boxes = select_text_boxes(
            selected_ocr=selected_ocr,
            raw_ocr_results=raw_ocr_results,
            roi_bgr=roi,
            preprocess_mod=preprocess_mod,
        )
        full_text_boxes = project_text_boxes_to_image(roi_text_boxes, roi_box, original.shape)
        roi_results.append(
            {
                "detector_label": detector_label,
                "detector_confidence": detector_confidence,
                "bbox": bbox,
                "roi_bbox": roi_box,
                "object_label": object_label,
                "extracted_text": extracted_text if extracted_text else "No label",
                "ocr_backend": selected_ocr.backend,
                "ocr_candidates": [asdict(item) for item in raw_ocr_results],
                "quantum_summary": quantum_summary,
                "model_predictions": model_predictions,
                "text_boxes": full_text_boxes,
                "text_box_count": len(full_text_boxes),
            }
        )

    detection_canvas = original.copy()
    result_canvas = original.copy()
    for item in roi_results:
        x1, y1, x2, y2 = item["bbox"]
        cv2.rectangle(detection_canvas, (x1, y1), (x2, y2), (10, 158, 110), 2)
        label = f'{item["object_label"]} | {item["detector_confidence"]:.2f}'
        cv2.putText(
            detection_canvas,
            label,
            (x1, max(18, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (10, 158, 110),
            2,
            cv2.LINE_AA,
        )
        cv2.rectangle(result_canvas, (x1, y1), (x2, y2), (10, 158, 110), 2)
        cv2.putText(
            result_canvas,
            item["object_label"],
            (x1, max(18, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (10, 158, 110),
            2,
            cv2.LINE_AA,
        )
        for text_box in item["text_boxes"]:
            tx1, ty1, tx2, ty2 = text_box["bbox"]
            cv2.rectangle(result_canvas, (tx1, ty1), (tx2, ty2), (26, 115, 232), 2)
        draw_result_summary_box(
            result_canvas,
            (x1, y1, x2, y2),
            item["object_label"],
            item["extracted_text"],
        )

    total_ms = (time.perf_counter() - total_started) * 1000.0
    model_comparison = []
    for item in selected_models:
        artifact_path = str(item["artifact_path"])
        model_comparison.append(
            {
                **item,
                "avg_runtime_ms": round(model_runtime_totals.get(artifact_path, 0.0) / max(1, len(roi_results)), 2),
                "predictions": model_predictions_overall.get(artifact_path, []),
                "is_primary": artifact_path == str(selected_models[0]["artifact_path"]),
            }
        )

    analysis_payload = {
        "upload_name": upload_path.name,
        "steps": [
            {
                "name": "Noise Reduction",
                "summary": "Fast non-local means denoising to stabilize object surfaces and small text regions.",
                "duration_ms": round(preprocess_ms, 2),
            },
            {
                "name": "Contrast Enhancement",
                "summary": "CLAHE-based contrast enhancement to make object structure and printed text more distinct.",
                "duration_ms": round(preprocess_ms, 2),
            },
            {
                "name": "Binarization",
                "summary": "Adaptive thresholding used internally to support OCR-friendly text-region analysis.",
                "duration_ms": round(preprocess_ms, 2),
            },
            {
                "name": "Detection",
                "summary": (
                    "ROI upload mode: detector skipped and the full uploaded image is treated as one object."
                    if recommendation.mode == "classifier_only"
                    else f"{len(roi_results)} object(s) detected with annotated bounding boxes."
                ),
                "duration_ms": round(detect_ms, 2),
            },
            {
                "name": "OCR and Result Rendering",
                "summary": "The system extracts text, highlights the recognized text region, and renders the predicted label on the full image.",
                "duration_ms": round(sum(ocr_ms_values), 2),
            },
        ],
        "runtime_benchmarks": [
            {"label": "Preprocessing", "value_ms": round(preprocess_ms, 2)},
            {"label": "Detection", "value_ms": round(detect_ms, 2)},
            {"label": "Classification", "value_ms": round(sum(classification_ms_values), 2)},
            {"label": "OCR", "value_ms": round(sum(ocr_ms_values), 2)},
            {"label": "End-to-End", "value_ms": round(total_ms, 2)},
        ],
        "model_runtime_breakdown": [
            {
                "label": item["display_name"],
                "value_ms": round(model_runtime_totals.get(str(item["artifact_path"]), 0.0), 2),
                "family": item["model_family"],
            }
            for item in selected_models
        ],
        "comparison_mode": comparison_mode,
        "model_comparison": model_comparison,
        "roi_results": roi_results,
        "original_preview": image_to_data_uri(original),
        "annotated_preview": image_to_data_uri(detection_canvas),
        "final_output_preview": image_to_data_uri(result_canvas),
        "text_overlay_preview": image_to_data_uri(result_canvas),
        "num_detections": len(roi_results),
        "pipeline_used": {
            "mode": recommendation.mode,
            "comparison_mode": comparison_mode,
            "detector_backend": recommendation.detector_backend,
            "detector_weights": recommendation.detector_weights,
            "classifier_artifact": recommendation.classifier_artifact,
            "classifier_name": recommendation.classifier_name,
            "classifier_family": recommendation.classifier_family,
            "evaluated_models": [item["display_name"] for item in selected_models],
            "ocr_backend": recommendation.ocr_backend,
        },
    }

    result_path = OUTPUT_DIR / f"{upload_path.stem}_analysis.json"
    result_path.write_text(json.dumps(analysis_payload, indent=2), encoding="utf-8")
    analysis_payload["saved_json"] = str(result_path)
    return analysis_payload


def get_shared_runtime_components(recommendation: PipelineRecommendation) -> tuple[Any, Any, Any]:
    detector_key = (
        "detector",
        recommendation.detector_backend or "",
        recommendation.detector_weights or "",
    )
    feature_key = ("feature_extractor", "cpu")
    ocr_key = ("ocr", recommendation.ocr_backend or "ensemble")

    config_mod = importlib.import_module("hybrid_qml_ocr.config")

    detector = _RUNTIME_CACHE.get(detector_key)
    if detector_key not in _RUNTIME_CACHE:
        detector = None
        if recommendation.detector_weights and recommendation.detector_backend not in {None, "classifier_only_roi_mode"}:
            detector_mod = importlib.import_module("hybrid_qml_ocr.detector")
            detector = detector_mod.build_detector(
                config_mod.DetectorConfig(
                    backend=recommendation.detector_backend,
                    weights_path=recommendation.detector_weights,
                    device="cpu",
                ),
                SUPPORTED_CLASSES,
            )
        _RUNTIME_CACHE[detector_key] = detector

    feature_extractor = _RUNTIME_CACHE.get(feature_key)
    if feature_key not in _RUNTIME_CACHE:
        features_mod = importlib.import_module("hybrid_qml_ocr.features")
        feature_extractor = features_mod.ROIHybridFeatureExtractor(
            config_mod.FeatureExtractorConfig(device="cpu")
        )
        _RUNTIME_CACHE[feature_key] = feature_extractor

    ocr_executor = _RUNTIME_CACHE.get(ocr_key)
    if ocr_key not in _RUNTIME_CACHE:
        ocr_mod = importlib.import_module("hybrid_qml_ocr.ocr")
        ocr_executor = ocr_mod.OCRExecutor(
            config_mod.OCRConfig(backend=recommendation.ocr_backend, device="cpu")
        )
        _RUNTIME_CACHE[ocr_key] = ocr_executor

    return (
        _RUNTIME_CACHE.get(detector_key),
        _RUNTIME_CACHE.get(feature_key),
        _RUNTIME_CACHE.get(ocr_key),
    )


def get_classifier_for_artifact(artifact_path: str) -> Any:
    resolved_path = str(resolve_project_path(artifact_path))
    cache_key = ("classifier", resolved_path)
    classifier = _RUNTIME_CACHE.get(cache_key)
    if cache_key not in _RUNTIME_CACHE:
        hybrid_models_mod = importlib.import_module("hybrid_qml_ocr.hybrid_models")
        classifier = hybrid_models_mod.BaseHybridQuantumClassifier.load(resolved_path)
        _RUNTIME_CACHE[cache_key] = classifier
    return _RUNTIME_CACHE.get(cache_key)


def build_dashboard_context(analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    path_hints = suggested_paths()
    dependency_status = collect_dependency_status()
    inventory = discover_inventory()
    benchmark_report = load_benchmark_report()
    recommendation = choose_pipeline(inventory, benchmark_report)
    benchmark_context = build_benchmark_context(benchmark_report)
    available_models = build_available_classifier_entries(
        inventory,
        benchmark_report,
        recommended_artifact=recommendation.classifier_artifact,
    )
    dataset_status = {
        "detector": inspect_detector_dataset(path_hints["detector_dataset_yaml"]),
        "classifier": inspect_classifier_dataset(path_hints["classifier_dataset_dir"]),
    }
    return {
        "analysis": analysis,
        "dependency_status": dependency_status,
        "inventory": inventory,
        "recommendation": recommendation,
        "benchmark": benchmark_context,
        "dataset_status": dataset_status,
        "supported_classes": SUPPORTED_CLASSES,
        "available_models": available_models,
        "model_catalog": build_model_catalog(),
        "training_status": get_training_state_payload(),
        "path_hints": path_hints,
        "flow_steps": ui_flow_steps(),
        "project_brief": PROJECT_BRIEF,
    }


def build_dashboard_payload(analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_dashboard_context(analysis=analysis)
    return {
        "analysis": context["analysis"],
        "dependency_status": [asdict(item) for item in context["dependency_status"]],
        "inventory": asdict(context["inventory"]),
        "recommendation": asdict(context["recommendation"]),
        "benchmark": context["benchmark"],
        "dataset_status": context["dataset_status"],
        "supported_classes": context["supported_classes"],
        "available_models": context["available_models"],
        "model_catalog": context["model_catalog"],
        "training_status": context["training_status"],
        "path_hints": context["path_hints"],
        "flow_steps": context["flow_steps"],
        "project_brief": context["project_brief"],
    }


def read_request_value(key: str, default: str = "") -> str:
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        return str(payload.get(key, default))
    return str(request.form.get(key, default))


@app.route("/", methods=["GET"])
def dashboard() -> str:
    return render_template("app_shell.html")


@app.route("/api/dashboard", methods=["GET"])
def api_dashboard() -> Any:
    return jsonify(build_dashboard_payload())


@app.route("/status", methods=["GET"])
def status() -> dict[str, Any]:
    return get_training_state_payload()


@app.route("/api/status", methods=["GET"])
def api_status() -> Any:
    return jsonify(get_training_state_payload())


@app.route("/train/detector", methods=["POST"])
def train_detector() -> str:
    dataset_yaml = (read_request_value("dataset_yaml") or "").strip()
    if not dataset_yaml:
        return jsonify({"ok": False, "message": "Detector training needs a dataset YAML path."}), 400
    detector_status = inspect_detector_dataset(dataset_yaml)
    if not detector_status["ready"]:
        return jsonify({"ok": False, "message": detector_status["message"], "dataset_status": detector_status}), 400
    command = [
        sys.executable,
        "-u",
        "train_detector_yolo.py",
        "--dataset-yaml",
        dataset_yaml,
        "--model",
        (read_request_value("model") or "yolov8n.pt").strip(),
        "--epochs",
        (read_request_value("epochs") or "50").strip(),
        "--imgsz",
        (read_request_value("imgsz") or "960").strip(),
        "--batch",
        (read_request_value("batch") or "8").strip(),
        "--project",
        (read_request_value("project") or "runs/detect").strip(),
        "--name",
        (read_request_value("name") or "qml_ocr_detector").strip(),
        "--device",
        (read_request_value("device") or "cpu").strip(),
        "--reuse-existing",
        (read_request_value("reuse_existing") or "true").strip(),
    ]
    summary_path = (read_request_value("summary_path") or "").strip()
    if summary_path:
        command.extend(["--summary-path", summary_path])
    started, message = start_background_job(
        "detector",
        "Detector Training",
        command,
        active_item=Path((read_request_value("name") or "qml_ocr_detector").strip()).stem.replace("_", " "),
        progress_current=1,
        progress_total=1,
        progress_status="training",
    )
    status_code = 200 if started else 409
    return jsonify({"ok": started, "message": message}), status_code


@app.route("/api/train/detector", methods=["POST"])
def api_train_detector() -> Any:
    return train_detector()


@app.route("/train/classifier", methods=["POST"])
def train_classifier() -> str:
    dataset_dir = (read_request_value("dataset_dir") or "").strip()
    if not dataset_dir:
        return jsonify({"ok": False, "message": "Classifier training needs an ROI dataset directory."}), 400
    classifier_status = inspect_classifier_dataset(dataset_dir)
    if not classifier_status["ready"]:
        return jsonify({"ok": False, "message": classifier_status["message"], "dataset_status": classifier_status}), 400
    command = [
        sys.executable,
        "-u",
        "train_hybrid.py",
        "--dataset-dir",
        dataset_dir,
        "--artifact-path",
        (read_request_value("artifact_path") or "artifacts/hybrid_qml_classifier.pkl").strip(),
        "--model-type",
        (read_request_value("model_type") or "qsvc").strip(),
        "--encoding",
        (read_request_value("encoding") or "angle").strip(),
        "--n-qubits",
        (read_request_value("n_qubits") or "6").strip(),
        "--test-size",
        (read_request_value("test_size") or "0.2").strip(),
        "--device",
        (read_request_value("device") or "cpu").strip(),
        "--reuse-existing",
        (read_request_value("reuse_existing") or "true").strip(),
    ]
    summary_path = (read_request_value("summary_path") or "").strip()
    if summary_path:
        command.extend(["--summary-path", summary_path])
    started, message = start_background_job(
        "classifier",
        "Hybrid Classifier Training",
        command,
        active_item=(read_request_value("model_type") or "classifier").strip().replace("_", " "),
        progress_current=1,
        progress_total=1,
        progress_status="training",
    )
    status_code = 200 if started else 409
    return jsonify({"ok": started, "message": message}), status_code


@app.route("/api/train/classifier", methods=["POST"])
def api_train_classifier() -> Any:
    return train_classifier()


@app.route("/train/classifier-suite", methods=["POST"])
def train_classifier_suite() -> str:
    dataset_dir = (read_request_value("dataset_dir") or "").strip()
    if not dataset_dir:
        return jsonify({"ok": False, "message": "Comparison suite training needs an ROI dataset directory."}), 400
    classifier_status = inspect_classifier_dataset(dataset_dir)
    if not classifier_status["ready"]:
        return jsonify({"ok": False, "message": classifier_status["message"], "dataset_status": classifier_status}), 400
    command = [
        sys.executable,
        "-u",
        "train_model_suite.py",
        "--dataset-dir",
        dataset_dir,
        "--artifacts-dir",
        (read_request_value("artifacts_dir") or "artifacts").strip(),
        "--profile",
        (read_request_value("profile") or "core").strip(),
        "--test-size",
        (read_request_value("test_size") or "0.2").strip(),
        "--device",
        (read_request_value("device") or "cpu").strip(),
        "--reuse-existing",
        (read_request_value("reuse_existing") or "true").strip(),
    ]
    profile_name = (read_request_value("profile") or "core").strip()
    started, message = start_background_job(
        "suite",
        "Classifier Comparison Suite",
        command,
        active_item=f"{profile_name} suite",
        progress_status="preparing",
    )
    status_code = 200 if started else 409
    return jsonify({"ok": started, "message": message}), status_code


@app.route("/api/train/classifier-suite", methods=["POST"])
def api_train_classifier_suite() -> Any:
    return train_classifier_suite()


@app.route("/benchmark/generate", methods=["POST"])
def generate_benchmark() -> str:
    command = [sys.executable, "-u", "build_benchmark_report.py"]
    started, message = start_background_job(
        "benchmark",
        "Benchmark Report Generation",
        command,
        active_item="benchmark report",
        progress_current=1,
        progress_total=1,
        progress_status="building",
    )
    status_code = 200 if started else 409
    return jsonify({"ok": started, "message": message}), status_code


@app.route("/api/benchmark/generate", methods=["POST"])
def api_generate_benchmark() -> Any:
    return generate_benchmark()


@app.route("/analyze", methods=["POST"])
def analyze() -> str:
    file_storage = request.files.get("image")
    if file_storage is None or not file_storage.filename:
        return jsonify({"ok": False, "message": "Choose an image file before running the pipeline."}), 400
    suffix = Path(file_storage.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return jsonify({"ok": False, "message": "Unsupported file type. Use PNG, JPG, JPEG, BMP, or WEBP."}), 400

    upload_path = save_uploaded_file(file_storage)
    try:
        inventory = discover_inventory()
        benchmark_report = load_benchmark_report()
        recommendation = choose_pipeline(inventory, benchmark_report)
        inference_mode = read_request_value("inference_mode", "recommended")
        classifier_artifact = read_request_value("classifier_artifact", "")
        active_recommendation, classifier_entries, resolved_mode = resolve_inference_models(
            inventory=inventory,
            benchmark_report=benchmark_report,
            recommendation=recommendation,
            inference_mode=inference_mode,
            classifier_artifact=classifier_artifact,
        )
        analysis = analyze_image(
            upload_path,
            active_recommendation,
            classifier_entries=classifier_entries,
            comparison_mode=resolved_mode,
        )
        return jsonify({"ok": True, "analysis": analysis})
    except Exception as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": str(exc),
                    "traceback": traceback.format_exc(limit=1),
                }
            ),
            500,
        )


@app.route("/api/analyze", methods=["POST"])
def api_analyze() -> Any:
    return analyze()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
