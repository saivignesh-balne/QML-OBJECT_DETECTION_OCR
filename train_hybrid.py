from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

from src.hybrid_qml_ocr.config import FeatureExtractorConfig, QuantumClassifierConfig
from src.hybrid_qml_ocr.features import ROIHybridFeatureExtractor
from src.hybrid_qml_ocr.hybrid_models import (
    BaseHybridQuantumClassifier,
    QUANTUM_MODEL_TYPES,
    build_classifier,
    describe_classifier_model,
)
from src.hybrid_qml_ocr.preprocess import build_classification_views


ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def collect_dataset(dataset_dir: Path) -> tuple[list[Path], list[str]]:
    image_paths: list[Path] = []
    labels: list[str] = []
    for class_dir in sorted(path for path in dataset_dir.iterdir() if path.is_dir()):
        for image_path in sorted(class_dir.rglob("*")):
            if image_path.suffix.lower() in ALLOWED_SUFFIXES:
                image_paths.append(image_path)
                labels.append(class_dir.name)
    if not image_paths:
        raise FileNotFoundError(f"No training images were found under {dataset_dir}")
    return image_paths, labels


def load_roi_image(image_path: Path) -> np.ndarray:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Unable to read ROI image: {image_path}")
    return image


def augment_roi_image(image_bgr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    height, width = image_bgr.shape[:2]
    angle = float(rng.uniform(-8.0, 8.0))
    scale = float(rng.uniform(0.95, 1.05))
    tx = float(rng.uniform(-0.03, 0.03) * width)
    ty = float(rng.uniform(-0.03, 0.03) * height)
    matrix = cv2.getRotationMatrix2D((width / 2.0, height / 2.0), angle, scale)
    matrix[:, 2] += [tx, ty]
    augmented = cv2.warpAffine(
        image_bgr,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    alpha = float(rng.uniform(0.9, 1.1))
    beta = float(rng.uniform(-14.0, 14.0))
    augmented = cv2.convertScaleAbs(augmented, alpha=alpha, beta=beta)
    if rng.random() < 0.35:
        augmented = cv2.GaussianBlur(augmented, (3, 3), sigmaX=0.5)
    return augmented


def build_balanced_training_set(
    train_paths: list[Path],
    train_labels: np.ndarray,
    random_state: int,
) -> tuple[list[np.ndarray], list[str], dict[str, int], dict[str, int]]:
    grouped_paths: dict[str, list[Path]] = {}
    for path, label in zip(train_paths, train_labels, strict=False):
        grouped_paths.setdefault(str(label), []).append(path)

    original_counts = {label: len(paths) for label, paths in grouped_paths.items()}
    target_count = max(original_counts.values())
    balanced_images: list[np.ndarray] = []
    balanced_labels: list[str] = []
    augmented_counts = {label: 0 for label in grouped_paths}
    rng = np.random.default_rng(random_state)

    for label, paths in grouped_paths.items():
        for path in paths:
            balanced_images.append(load_roi_image(path))
            balanced_labels.append(label)
        deficit = target_count - len(paths)
        for _ in range(deficit):
            source_path = paths[int(rng.integers(0, len(paths)))]
            augmented_images = augment_roi_image(load_roi_image(source_path), rng)
            balanced_images.append(augmented_images)
            balanced_labels.append(label)
            augmented_counts[label] += 1

    return balanced_images, balanced_labels, original_counts, augmented_counts


def predict_with_tta(
    classifier: object,
    feature_extractor: ROIHybridFeatureExtractor,
    image_paths: list[Path],
) -> np.ndarray:
    predictions: list[str] = []
    for image_path in image_paths:
        image = load_roi_image(image_path)
        views = build_classification_views(image)
        feature_matrix = feature_extractor.encode_images(views)
        view_predictions = classifier.predict(feature_matrix)
        values, counts = np.unique(view_predictions, return_counts=True)
        predictions.append(str(values[np.argmax(counts)]))
    return np.asarray(predictions)


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def build_model_name(model_type: str, encoding: str) -> str:
    return str(describe_classifier_model(model_type, encoding)["display_name"])


def build_model_family(model_type: str) -> str:
    return "quantum" if model_type in QUANTUM_MODEL_TYPES else "classical"


def load_summary_if_compatible(
    artifact_path: Path,
    summary_path: Path,
    dataset_dir: Path,
    model_type: str,
    encoding: str,
    n_qubits: int,
    feature_map_reps: int,
    ansatz_reps: int,
    maxiter: int,
    preselect_dim: int,
    classical_feature_dim: int,
    test_size: float,
) -> dict[str, object] | None:
    if not artifact_path.exists() or not summary_path.exists():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if str(payload.get("dataset_dir", "")) != str(dataset_dir.resolve()):
        return None
    if str(payload.get("model_type", "")) != model_type:
        return None
    if float(payload.get("test_size", -1.0)) != float(test_size):
        return None
    if model_type in QUANTUM_MODEL_TYPES:
        if str(payload.get("encoding", "")) != encoding:
            return None
        if int(payload.get("n_qubits", -1)) != int(n_qubits):
            return None
    if int(payload.get("feature_map_reps", -1)) != int(feature_map_reps):
        return None
    if int(payload.get("ansatz_reps", -1)) != int(ansatz_reps):
        return None
    if int(payload.get("maxiter", -1)) != int(maxiter):
        return None
    if int(payload.get("preselect_dim", -1)) != int(preselect_dim):
        return None
    if int(payload.get("classical_feature_dim", -1)) != int(classical_feature_dim):
        return None
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a hybrid quantum classifier on cropped ROI images.")
    parser.add_argument("--dataset-dir", required=True, help="Folder with one subfolder per class.")
    parser.add_argument("--artifact-path", default="artifacts/hybrid_qml_classifier.pkl")
    parser.add_argument("--summary-path", default=None, help="Optional JSON summary output path.")
    parser.add_argument(
        "--model-type",
        choices=[
            "qsvc",
            "qsvc_zz_linear",
            "qsvc_zz_full",
            "qsvc_pauli",
            "vqc",
            "vqc_real",
            "vqc_efficient",
            "svc_rbf",
            "random_forest",
            "logreg",
            "mlp",
        ],
        default="qsvc",
    )
    parser.add_argument("--encoding", choices=["angle", "amplitude"], default="angle")
    parser.add_argument("--n-qubits", type=int, default=6)
    parser.add_argument("--feature-map-reps", type=int, default=2)
    parser.add_argument("--ansatz-reps", type=int, default=2)
    parser.add_argument("--maxiter", type=int, default=50)
    parser.add_argument("--preselect-dim", type=int, default=256)
    parser.add_argument("--classical-feature-dim", type=int, default=128)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--reuse-existing", default="true", help="Reuse an existing compatible artifact instead of retraining.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_dir = Path(args.dataset_dir)
    artifact_path = Path(args.artifact_path)
    summary_path = Path(args.summary_path) if args.summary_path else artifact_path.with_suffix(".summary.json")
    model_family = build_model_family(args.model_type)
    model_info = describe_classifier_model(args.model_type, args.encoding)
    if model_family == "quantum" and args.encoding not in model_info.get("supported_encodings", ["angle", "amplitude"]):
        supported_encodings = ", ".join(model_info.get("supported_encodings", []))
        raise ValueError(
            f"{args.model_type} does not support encoding '{args.encoding}'. Supported encodings: {supported_encodings}"
        )
    reuse_existing = parse_bool(args.reuse_existing)
    existing_summary = load_summary_if_compatible(
        artifact_path=artifact_path,
        summary_path=summary_path,
        dataset_dir=dataset_dir,
        model_type=args.model_type,
        encoding=args.encoding,
        n_qubits=args.n_qubits,
        feature_map_reps=args.feature_map_reps,
        ansatz_reps=args.ansatz_reps,
        maxiter=args.maxiter,
        preselect_dim=args.preselect_dim,
        classical_feature_dim=args.classical_feature_dim,
        test_size=args.test_size,
    )
    if reuse_existing and existing_summary is not None:
        existing_summary["artifact_reused"] = True
        summary_path.write_text(json.dumps(existing_summary, indent=2), encoding="utf-8")
        print(f"Reusing compatible classifier artifact: {artifact_path}")
        print(f"Reusing compatible classifier summary: {summary_path}")
        return

    image_paths, labels = collect_dataset(dataset_dir)
    started_at = time.perf_counter()
    feature_extractor = ROIHybridFeatureExtractor(FeatureExtractorConfig(device=args.device))
    labels_array = np.asarray(labels)
    train_paths, test_paths, train_labels, test_labels = train_test_split(
        image_paths,
        labels_array,
        test_size=args.test_size,
        stratify=labels_array,
        random_state=42,
    )
    balanced_images, balanced_labels, original_train_counts, augmented_counts = build_balanced_training_set(
        train_paths,
        train_labels,
        random_state=42,
    )
    train_features = feature_extractor.encode_images(balanced_images)
    class_names = sorted(set(labels))
    classifier_config = QuantumClassifierConfig(
        class_names=class_names,
        model_type=args.model_type,
        encoding=args.encoding,
        n_qubits=args.n_qubits,
        feature_map_reps=args.feature_map_reps,
        ansatz_reps=args.ansatz_reps,
        maxiter=args.maxiter,
        preselect_dim=args.preselect_dim,
        classical_feature_dim=args.classical_feature_dim,
        artifact_path=args.artifact_path,
    )
    classifier = build_classifier(classifier_config)
    classifier.fit(train_features, np.asarray(balanced_labels))
    predictions = predict_with_tta(classifier, feature_extractor, list(test_paths))
    report = classification_report(test_labels, predictions, digits=4)
    report_dict = classification_report(test_labels, predictions, output_dict=True, zero_division=0)
    accuracy = float(accuracy_score(test_labels, predictions))
    macro_precision, macro_recall, macro_f1, _ = precision_recall_fscore_support(
        test_labels,
        predictions,
        average="macro",
        zero_division=0,
    )
    weighted_precision, weighted_recall, weighted_f1, _ = precision_recall_fscore_support(
        test_labels,
        predictions,
        average="weighted",
        zero_division=0,
    )
    elapsed = float(time.perf_counter() - started_at)
    print(report)
    saved_path = classifier.save(artifact_path)
    print(f"Saved classifier artifact to: {saved_path}")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_payload = {
        "generated_at": datetime.now().isoformat(),
        "kind": "classifier",
        "artifact_path": str(saved_path),
        "summary_path": str(summary_path),
        "dataset_dir": str(dataset_dir.resolve()),
        "num_samples": int(len(labels)),
        "num_classes": int(len(class_names)),
        "class_names": class_names,
        "train_samples_original": int(len(train_paths)),
        "train_samples_balanced": int(len(balanced_labels)),
        "test_samples": int(len(test_paths)),
        "train_class_counts_original": original_train_counts,
        "train_class_counts_augmented": augmented_counts,
        "model_name": build_model_name(args.model_type, args.encoding),
        "model_family": model_family,
        "model_type": args.model_type,
        "encoding": args.encoding if model_family == "quantum" else "classical_projection",
        "n_qubits": int(args.n_qubits),
        "feature_map_reps": int(args.feature_map_reps),
        "ansatz_reps": int(args.ansatz_reps),
        "maxiter": int(args.maxiter),
        "preselect_dim": int(args.preselect_dim),
        "classical_feature_dim": int(args.classical_feature_dim),
        "kernel_name": model_info["kernel_name"],
        "feature_map_name": model_info["feature_map_name"],
        "feature_map_detail": model_info["feature_map_detail"],
        "ansatz_name": model_info["ansatz_name"],
        "model_summary": model_info["summary"],
        "model_strengths": model_info["strengths"],
        "model_limitations": model_info["limitations"],
        "test_size": float(args.test_size),
        "device": args.device,
        "tta_views": 3,
        "artifact_reused": False,
        "accuracy": accuracy,
        "macro_precision": float(macro_precision),
        "macro_recall": float(macro_recall),
        "macro_f1": float(macro_f1),
        "weighted_precision": float(weighted_precision),
        "weighted_recall": float(weighted_recall),
        "weighted_f1": float(weighted_f1),
        "train_time_seconds": elapsed,
        "classification_report": report_dict,
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    print(f"Saved classifier summary to: {summary_path}")


if __name__ == "__main__":
    main()
