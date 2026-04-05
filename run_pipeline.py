from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.hybrid_qml_ocr.config import DetectorConfig, OCRConfig, PipelineConfig, QuantumClassifierConfig
from src.hybrid_qml_ocr.hybrid_models import BaseHybridQuantumClassifier
from src.hybrid_qml_ocr.pipeline import HybridQMLOCRPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hybrid QML object detection and OCR on one image.")
    parser.add_argument("--image", required=True, help="Path to the input image.")
    parser.add_argument("--artifact-path", required=True, help="Pickled hybrid quantum classifier artifact.")
    parser.add_argument("--detector-backend", choices=["yolo", "faster_rcnn"], default="yolo")
    parser.add_argument("--detector-weights", required=True, help="Path to detector weights.")
    parser.add_argument("--class-names", nargs="+", required=True, help="Class names in detector/classifier order.")
    parser.add_argument("--ocr-backend", choices=["tesseract", "trocr", "ensemble"], default="ensemble")
    parser.add_argument("--tesseract-cmd", default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output-dir", default="outputs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    classifier = BaseHybridQuantumClassifier.load(args.artifact_path)
    config = PipelineConfig(
        class_names=list(args.class_names),
        detector=DetectorConfig(
            backend=args.detector_backend,
            weights_path=args.detector_weights,
            device=args.device,
        ),
        classifier=QuantumClassifierConfig(
            class_names=list(args.class_names),
            artifact_path=args.artifact_path,
        ),
        ocr=OCRConfig(
            backend=args.ocr_backend,
            tesseract_cmd=args.tesseract_cmd,
            device=args.device,
        ),
    )
    config.output.output_dir = args.output_dir
    pipeline = HybridQMLOCRPipeline(config=config, classifier=classifier)
    payload = pipeline.run(args.image)
    json_path = pipeline.save_json(payload, Path(args.image).stem)
    print(json.dumps(payload, indent=2))
    print(f"Saved JSON output to: {json_path}")


if __name__ == "__main__":
    main()
