from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a YOLO detector for custom package/object detection.")
    parser.add_argument("--dataset-yaml", required=True, help="Path to Ultralytics dataset YAML.")
    parser.add_argument("--model", default="yolov8n.pt", help="Base YOLO checkpoint.")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--project", default="runs/detect")
    parser.add_argument("--name", default="qml_ocr_detector")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--summary-path", default=None, help="Optional detector summary JSON output path.")
    parser.add_argument("--reuse-existing", default="true", help="Reuse an existing compatible detector artifact instead of retraining.")
    return parser.parse_args()


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def read_latest_metrics(results_csv_path: Path) -> dict[str, float]:
    if not results_csv_path.exists():
        return {}
    with results_csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        return {}
    latest = rows[-1]
    metrics: dict[str, float] = {}
    for key, value in latest.items():
        try:
            metrics[key.strip()] = float(value)
        except (TypeError, ValueError):
            continue
    return metrics


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary_path) if args.summary_path else Path("artifacts") / f"{args.name}_detector.summary.json"
    exported_weights = Path("weights") / f"{args.name}_best.pt"
    if parse_bool(args.reuse_existing) and summary_path.exists() and exported_weights.exists():
        try:
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            existing_summary = {}
        if (
            str(existing_summary.get("dataset_yaml", "")) == str(Path(args.dataset_yaml).resolve())
            and str(existing_summary.get("base_model", "")) == args.model
            and int(existing_summary.get("epochs", -1)) == int(args.epochs)
            and int(existing_summary.get("imgsz", -1)) == int(args.imgsz)
            and int(existing_summary.get("batch", -1)) == int(args.batch)
            and str(existing_summary.get("device", "")) == args.device
        ):
            existing_summary["artifact_reused"] = True
            summary_path.write_text(json.dumps(existing_summary, indent=2), encoding="utf-8")
            print(f"Reusing compatible detector weights: {exported_weights}")
            print(f"Reusing compatible detector summary: {summary_path}")
            return

    model = YOLO(args.model)
    training_result = model.train(
        data=args.dataset_yaml,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
        device=args.device,
        exist_ok=True,
    )
    candidate_dirs: list[Path] = []
    result_save_dir = getattr(training_result, "save_dir", None)
    if result_save_dir:
        candidate_dirs.append(Path(result_save_dir))
    trainer = getattr(model, "trainer", None)
    trainer_save_dir = getattr(trainer, "save_dir", None) if trainer is not None else None
    if trainer_save_dir:
        candidate_dirs.append(Path(trainer_save_dir))
    candidate_dirs.append(Path(args.project) / args.name)

    save_dir = next(
        (path for path in candidate_dirs if (path / "weights" / "best.pt").exists()),
        candidate_dirs[0],
    )
    best_weights = save_dir / "weights" / "best.pt"
    exported_weights.parent.mkdir(parents=True, exist_ok=True)
    if best_weights.exists():
        shutil.copy2(best_weights, exported_weights)
    metrics = read_latest_metrics(save_dir / "results.csv")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_payload = {
        "generated_at": datetime.now().isoformat(),
        "kind": "detector",
        "dataset_yaml": str(Path(args.dataset_yaml).resolve()),
        "base_model": args.model,
        "epochs": int(args.epochs),
        "imgsz": int(args.imgsz),
        "batch": int(args.batch),
        "device": args.device,
        "project": args.project,
        "name": args.name,
        "save_dir": str(save_dir.resolve()),
        "best_weights": str(exported_weights.resolve()) if exported_weights.exists() else "",
        "training_best_weights": str(best_weights.resolve()) if best_weights.exists() else "",
        "artifact_reused": False,
        "metrics": metrics,
        "mAP50": metrics.get("metrics/mAP50(B)", metrics.get("metrics/mAP50", 0.0)),
        "mAP50_95": metrics.get("metrics/mAP50-95(B)", metrics.get("metrics/mAP50-95", 0.0)),
        "precision": metrics.get("metrics/precision(B)", metrics.get("metrics/precision", 0.0)),
        "recall": metrics.get("metrics/recall(B)", metrics.get("metrics/recall", 0.0)),
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    print(f"Saved detector summary to: {summary_path}")


if __name__ == "__main__":
    main()
