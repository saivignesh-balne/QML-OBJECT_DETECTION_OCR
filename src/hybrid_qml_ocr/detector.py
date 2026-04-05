from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import cv2
import numpy as np
import torch
from torchvision.models.detection import fasterrcnn_resnet50_fpn_v2

from .config import DetectorConfig


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]


class BaseDetector(ABC):
    def __init__(self, config: DetectorConfig, class_names: list[str]) -> None:
        self.config = config
        self.class_names = class_names

    @abstractmethod
    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        raise NotImplementedError


class YoloDetector(BaseDetector):
    def __init__(self, config: DetectorConfig, class_names: list[str]) -> None:
        super().__init__(config, class_names)
        from ultralytics import YOLO

        self.model = YOLO(str(config.weights_path))

    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        result = self.model.predict(
            source=image_bgr,
            conf=self.config.confidence_threshold,
            imgsz=self.config.image_size,
            device=self.config.device,
            max_det=self.config.max_detections,
            verbose=False,
        )[0]
        detections: list[Detection] = []
        if result.boxes is None:
            return detections
        boxes = result.boxes.xyxy.cpu().numpy().astype(int)
        scores = result.boxes.conf.cpu().numpy()
        classes = result.boxes.cls.cpu().numpy().astype(int)
        for box, score, class_id in zip(boxes, scores, classes, strict=False):
            label = self.class_names[class_id] if class_id < len(self.class_names) else str(class_id)
            detections.append(
                Detection(
                    label=label,
                    confidence=float(score),
                    bbox=(int(box[0]), int(box[1]), int(box[2]), int(box[3])),
                )
            )
        return detections


class FasterRCNNDetector(BaseDetector):
    def __init__(self, config: DetectorConfig, class_names: list[str]) -> None:
        super().__init__(config, class_names)
        self.device = torch.device(config.device)
        self.model = fasterrcnn_resnet50_fpn_v2(weights=None, num_classes=len(class_names) + 1)
        state_dict = torch.load(str(config.weights_path), map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        tensor = tensor.to(self.device)
        with torch.no_grad():
            predictions = self.model([tensor])[0]
        detections: list[Detection] = []
        for box, score, label_index in zip(
            predictions["boxes"].cpu().numpy(),
            predictions["scores"].cpu().numpy(),
            predictions["labels"].cpu().numpy(),
            strict=False,
        ):
            if float(score) < self.config.confidence_threshold:
                continue
            class_id = int(label_index) - 1
            label = self.class_names[class_id] if 0 <= class_id < len(self.class_names) else str(label_index)
            x1, y1, x2, y2 = box.astype(int).tolist()
            detections.append(
                Detection(
                    label=label,
                    confidence=float(score),
                    bbox=(x1, y1, x2, y2),
                )
            )
        return detections


def build_detector(config: DetectorConfig, class_names: list[str]) -> BaseDetector:
    if config.backend == "yolo":
        return YoloDetector(config, class_names)
    if config.backend == "faster_rcnn":
        return FasterRCNNDetector(config, class_names)
    raise ValueError(f"Unsupported detector backend: {config.backend}")
