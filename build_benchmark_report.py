from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hybrid_qml_ocr.hybrid_models import describe_classifier_model, is_quantum_model


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_classifier_family(payload: dict[str, Any]) -> str:
    model_type = str(payload.get("model_type", ""))
    return "quantum" if is_quantum_model(model_type) else "classical"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate detector/classifier summaries into a benchmark report.")
    parser.add_argument("--artifacts-dir", default="artifacts")
    parser.add_argument("--output-path", default="artifacts/benchmark_report.json")
    return parser.parse_args()


def build_classifier_row(item: dict[str, Any]) -> dict[str, Any]:
    model_type = str(item.get("model_type", "classifier"))
    encoding = str(item.get("encoding", "angle"))
    descriptor = describe_classifier_model(model_type, encoding if encoding != "classical_projection" else "angle")
    accuracy = float(item.get("accuracy", 0.0))
    macro_f1 = float(item.get("macro_f1", 0.0))
    train_time_seconds = float(item.get("train_time_seconds", 0.0))
    return {
        "name": item.get("model_name", descriptor["display_name"]),
        "model": model_type,
        "model_family": item.get("model_family", infer_classifier_family(item)),
        "encoding": item.get("encoding", "classical_projection"),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "weighted_f1": float(item.get("weighted_f1", 0.0)),
        "artifact_path": item.get("artifact_path", ""),
        "n_qubits": int(item.get("n_qubits", 0)),
        "artifact_reused": bool(item.get("artifact_reused", False)),
        "train_time_seconds": train_time_seconds,
        "kernel_name": item.get("kernel_name", descriptor["kernel_name"]),
        "feature_map_name": item.get("feature_map_name", descriptor["feature_map_name"]),
        "feature_map_detail": item.get("feature_map_detail", descriptor["feature_map_detail"]),
        "ansatz_name": item.get("ansatz_name", descriptor["ansatz_name"]),
        "summary": item.get("model_summary", descriptor["summary"]),
        "strengths": item.get("model_strengths", descriptor["strengths"]),
        "limitations": item.get("model_limitations", descriptor["limitations"]),
        "notes": "Classifier score uses held-out test accuracy and macro F1.",
    }


def build_chart_series(rows: list[dict[str, Any]], key: str, multiplier: float = 1.0) -> list[dict[str, Any]]:
    return [
        {
            "label": row.get("name", row.get("model", "model")),
            "value": round(float(row.get(key, 0.0)) * multiplier, 4),
            "family": row.get("model_family", "unknown"),
            "artifact_path": row.get("artifact_path", ""),
        }
        for row in rows
    ]


def build_family_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("model_family", "unknown")), []).append(row)
    summary: list[dict[str, Any]] = []
    for family, family_rows in grouped.items():
        accuracies = [float(item.get("accuracy", 0.0)) for item in family_rows]
        macro_f1_scores = [float(item.get("macro_f1", 0.0)) for item in family_rows]
        best_entry = max(family_rows, key=lambda item: (float(item.get("accuracy", 0.0)), float(item.get("macro_f1", 0.0))))
        summary.append(
            {
                "family": family,
                "count": len(family_rows),
                "best_model": best_entry.get("name", "unknown"),
                "best_accuracy": max(accuracies, default=0.0),
                "avg_accuracy": mean(accuracies) if accuracies else 0.0,
                "avg_macro_f1": mean(macro_f1_scores) if macro_f1_scores else 0.0,
            }
        )
    summary.sort(key=lambda row: (float(row["best_accuracy"]), float(row["avg_accuracy"])), reverse=True)
    return summary


def main() -> None:
    args = parse_args()
    artifacts_dir = Path(args.artifacts_dir)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    detector_summaries: list[dict[str, Any]] = []
    classifier_summaries: list[dict[str, Any]] = []
    for path in sorted(artifacts_dir.glob("*.summary.json")):
        payload = load_json(path)
        kind = payload.get("kind")
        if kind == "detector":
            detector_summaries.append(payload)
        elif kind == "classifier":
            classifier_summaries.append(payload)

    detector_benchmarks = sorted(
        [
            {
                "name": item.get("name", Path(item.get("best_weights") or item.get("save_dir", "")).name or "detector"),
                "model": item.get("base_model", "detector"),
                "accuracy": float(item.get("mAP50_95", item.get("mAP50", 0.0))),
                "mAP50": float(item.get("mAP50", 0.0)),
                "mAP50_95": float(item.get("mAP50_95", 0.0)),
                "precision": float(item.get("precision", 0.0)),
                "recall": float(item.get("recall", 0.0)),
                "weights_path": item.get("best_weights", ""),
                "notes": "Detector ranking uses mAP50-95 when available.",
            }
            for item in detector_summaries
        ],
        key=lambda row: row["accuracy"],
        reverse=True,
    )

    classifier_benchmarks = sorted(
        [build_classifier_row(item) for item in classifier_summaries],
        key=lambda row: (row["accuracy"], row["macro_f1"]),
        reverse=True,
    )

    ocr_benchmarks = [
        {
            "name": "OCR Ensemble",
            "score": "policy default",
            "notes": "Uses both Tesseract and TrOCR and selects the best non-empty output.",
        },
        {
            "name": "TrOCR",
            "score": "policy fallback",
            "notes": "Transformer OCR for difficult object text regions.",
        },
        {
            "name": "Tesseract",
            "score": "policy fallback",
            "notes": "Fast OCR baseline for clean printed text.",
        },
    ]

    leaderboard: list[dict[str, Any]] = []
    if detector_benchmarks and classifier_benchmarks:
        for detector in detector_benchmarks:
            for classifier in classifier_benchmarks:
                composite_score = round((detector["accuracy"] + classifier["accuracy"]) / 2.0, 6)
                leaderboard.append(
                    {
                        "pipeline": f'{Path(detector["weights_path"]).name or detector["name"]} + {classifier["name"]} + OCR Ensemble',
                        "accuracy": composite_score,
                        "macro_f1": classifier["macro_f1"],
                        "detector_backend": "faster_rcnn" if "faster" in detector["name"].lower() else "yolo",
                        "detector_weights": detector["weights_path"],
                        "classifier_artifact": classifier["artifact_path"],
                        "classifier_name": classifier["name"],
                        "classifier_family": classifier.get("model_family", "unknown"),
                        "ocr_backend": "ensemble",
                        "mode": "full_pipeline",
                        "notes": "Composite proxy score = mean(detector mAP50-95, classifier accuracy).",
                    }
                )
        leaderboard.sort(key=lambda row: (row["accuracy"], row["macro_f1"]), reverse=True)
    elif classifier_benchmarks:
        for classifier in classifier_benchmarks:
            leaderboard.append(
                {
                    "pipeline": f'ROI Upload Mode + {classifier["name"]} + OCR Ensemble',
                    "accuracy": classifier["accuracy"],
                    "macro_f1": classifier["macro_f1"],
                    "detector_backend": "classifier_only_roi_mode",
                    "detector_weights": "",
                    "classifier_artifact": classifier["artifact_path"],
                    "classifier_name": classifier["name"],
                    "classifier_family": classifier.get("model_family", "unknown"),
                    "ocr_backend": "ensemble",
                    "mode": "classifier_only",
                    "notes": "Classifier-only ROI mode for already-cropped single-object uploads.",
                }
            )
        leaderboard.sort(key=lambda row: (row["accuracy"], row["macro_f1"]), reverse=True)

    recommended = leaderboard[0] if leaderboard else {}
    family_summary = build_family_summary(classifier_benchmarks)
    payload = {
        "generated_at": datetime.now().isoformat(),
        "recommended_pipeline": {
            "mode": recommended.get("mode"),
            "detector_backend": recommended.get("detector_backend"),
            "detector_weights": recommended.get("detector_weights"),
            "classifier_artifact": recommended.get("classifier_artifact"),
            "classifier_name": recommended.get("classifier_name"),
            "classifier_family": recommended.get("classifier_family"),
            "ocr_backend": recommended.get("ocr_backend", "ensemble"),
        }
        if recommended
        else {},
        "leaderboard": leaderboard,
        "detector_benchmarks": detector_benchmarks,
        "classifier_benchmarks": classifier_benchmarks,
        "ocr_benchmarks": ocr_benchmarks,
        "classifier_family_summary": family_summary,
        "chart_series": {
            "classifier_accuracy_pct": build_chart_series(classifier_benchmarks, "accuracy", multiplier=100.0),
            "classifier_macro_f1_pct": build_chart_series(classifier_benchmarks, "macro_f1", multiplier=100.0),
            "classifier_train_time_s": build_chart_series(classifier_benchmarks, "train_time_seconds"),
            "detector_map_pct": build_chart_series(detector_benchmarks, "accuracy", multiplier=100.0),
            "family_avg_accuracy_pct": [
                {
                    "label": row["family"],
                    "value": round(float(row["avg_accuracy"]) * 100.0, 4),
                    "family": row["family"],
                    "artifact_path": "",
                }
                for row in family_summary
            ],
        },
        "notes": [
            "Detector ranking uses mAP50-95 when available.",
            "Classifier ranking uses held-out test accuracy, macro F1, and training-time metadata.",
            "Quantum entries now include distinct kernel maps and variational ansatz choices for fairer comparison.",
            "Classical baselines are retained because they define the performance bar quantum models must beat or complement.",
            "Overall leaderboard still uses a proxy composite score unless you replace it with true end-to-end validation results.",
            "If detector summaries are missing, the report falls back to classifier-only ROI upload mode.",
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved benchmark report to: {output_path}")


if __name__ == "__main__":
    main()
