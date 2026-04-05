from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import PipelineConfig
from .detector import Detection, build_detector
from .features import ROIHybridFeatureExtractor
from .hybrid_models import BaseHybridQuantumClassifier
from .ocr import OCRExecutor
from .preprocess import build_classification_views, crop_roi, preprocess_for_detection, read_image


@dataclass
class ObjectResult:
    detector_label: str
    detector_confidence: float
    bbox: tuple[int, int, int, int]
    object_label: str
    extracted_text: str
    ocr_backend: str
    ocr_candidates: list[dict[str, Any]]


class HybridQMLOCRPipeline:
    def __init__(
        self,
        config: PipelineConfig,
        classifier: BaseHybridQuantumClassifier,
    ) -> None:
        self.config = config
        self.detector = build_detector(config.detector, config.class_names)
        self.features = ROIHybridFeatureExtractor(config.features)
        self.classifier = classifier
        self.ocr = OCRExecutor(config.ocr)
        self.output_dir = Path(config.output.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, image_path: str | Path) -> dict[str, Any]:
        image = read_image(image_path)
        preprocessed = preprocess_for_detection(image)
        detections = self.detector.detect(preprocessed.contrast_bgr)
        object_results: list[ObjectResult] = []
        for detection in detections:
            roi = crop_roi(preprocessed.contrast_bgr, detection.bbox)
            object_label = self._resolve_object_label(roi, detection)
            selected_ocr, raw_ocr_results = self.ocr.run(roi)
            extracted_text = selected_ocr.text.strip() if selected_ocr.text else ""
            object_results.append(
                ObjectResult(
                    detector_label=detection.label,
                    detector_confidence=detection.confidence,
                    bbox=detection.bbox,
                    object_label=object_label,
                    extracted_text=extracted_text if extracted_text else "No label",
                    ocr_backend=selected_ocr.backend,
                    ocr_candidates=[asdict(result) for result in raw_ocr_results],
                )
            )
        annotated_path = None
        if self.config.output.save_visualization:
            annotated_path = self._save_annotated_image(image, detections, object_results, Path(image_path).stem)
        return {
            "image_path": str(image_path),
            "num_detections": len(object_results),
            "results": [asdict(item) for item in object_results],
            "annotated_image": str(annotated_path) if annotated_path else None,
        }

    def _resolve_object_label(self, roi: np.ndarray, detection: Detection) -> str:
        supported_labels = set(self.config.class_names)
        if detection.label not in supported_labels:
            return "unidentified object detected"
        feature_matrix = self.features.encode_images(build_classification_views(roi))
        predictions = self.classifier.predict(feature_matrix)
        values, counts = np.unique(predictions, return_counts=True)
        predicted_label = str(values[np.argmax(counts)])
        if predicted_label not in supported_labels:
            return "unidentified object detected"
        return predicted_label

    def _save_annotated_image(
        self,
        image_bgr: np.ndarray,
        detections: list[Detection],
        object_results: list[ObjectResult],
        image_stem: str,
    ) -> Path:
        canvas = image_bgr.copy()
        for detection, result in zip(detections, object_results, strict=False):
            x1, y1, x2, y2 = detection.bbox
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{result.object_label} | {detection.confidence:.2f}"
            cv2.putText(
                canvas,
                label,
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
        target = self.output_dir / f"{image_stem}_annotated.jpg"
        cv2.imwrite(str(target), canvas)
        return target

    def save_json(self, payload: dict[str, Any], image_stem: str) -> Path:
        target = self.output_dir / f"{image_stem}_result.json"
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target
