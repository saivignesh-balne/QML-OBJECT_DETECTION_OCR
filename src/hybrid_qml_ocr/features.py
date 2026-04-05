from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models

from .config import FeatureExtractorConfig
from .preprocess import resize_for_model


@dataclass
class ROIEncodedFeatures:
    vector: np.ndarray
    source_dim: int


class CNNFeatureExtractor:
    def __init__(self, config: FeatureExtractorConfig) -> None:
        self.config = config
        self.device = torch.device(config.device)
        if config.cnn_backbone != "resnet18":
            raise ValueError("This scaffold currently supports cnn_backbone='resnet18'.")
        weights = models.ResNet18_Weights.DEFAULT
        base = models.resnet18(weights=weights)
        self.transform = weights.transforms()
        self.model = nn.Sequential(*list(base.children())[:-1])
        self.model.to(self.device)
        self.model.eval()

    def encode(self, image_bgr: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(
            resize_for_model(image_bgr, self.config.image_size),
            cv2.COLOR_BGR2RGB,
        )
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        tensor = self.transform(tensor).unsqueeze(0).to(self.device)
        with torch.no_grad():
            embedding = self.model(tensor).flatten(1).cpu().numpy()
        return embedding.squeeze(0)


def extract_hog_features(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(resize_for_model(image_bgr, (128, 128)), cv2.COLOR_BGR2GRAY)
    hog = cv2.HOGDescriptor(
        _winSize=(128, 128),
        _blockSize=(32, 32),
        _blockStride=(16, 16),
        _cellSize=(16, 16),
        _nbins=9,
    )
    descriptor = hog.compute(gray)
    return descriptor.flatten().astype(np.float32)


def extract_lbp_histogram(image_bgr: np.ndarray, bins: int = 32) -> np.ndarray:
    gray = cv2.cvtColor(resize_for_model(image_bgr, (128, 128)), cv2.COLOR_BGR2GRAY)
    center = gray[1:-1, 1:-1]
    lbp = np.zeros_like(center, dtype=np.uint8)
    neighbors = [
        gray[:-2, :-2],
        gray[:-2, 1:-1],
        gray[:-2, 2:],
        gray[1:-1, 2:],
        gray[2:, 2:],
        gray[2:, 1:-1],
        gray[2:, :-2],
        gray[1:-1, :-2],
    ]
    for bit_index, neighbor in enumerate(neighbors):
        lbp |= ((neighbor >= center).astype(np.uint8) << bit_index)
    hist, _ = np.histogram(lbp.ravel(), bins=bins, range=(0, 256), density=True)
    return hist.astype(np.float32)


def extract_color_histogram(image_bgr: np.ndarray, bins: int = 16) -> np.ndarray:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    features: list[np.ndarray] = []
    for channel_index in range(3):
        hist = cv2.calcHist([hsv], [channel_index], None, [bins], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        features.append(hist.astype(np.float32))
    return np.concatenate(features)


class ROIHybridFeatureExtractor:
    def __init__(self, config: FeatureExtractorConfig) -> None:
        self.config = config
        self.cnn_extractor = CNNFeatureExtractor(config) if config.use_cnn_embeddings else None

    def encode(self, image_bgr: np.ndarray) -> ROIEncodedFeatures:
        parts: list[np.ndarray] = []
        if self.cnn_extractor is not None:
            parts.append(self.cnn_extractor.encode(image_bgr))
        if self.config.use_hog:
            parts.append(extract_hog_features(image_bgr))
        if self.config.use_lbp:
            parts.append(extract_lbp_histogram(image_bgr))
        if self.config.use_color_histogram:
            parts.append(extract_color_histogram(image_bgr))
        if not parts:
            raise ValueError("At least one feature extractor must be enabled.")
        vector = np.concatenate(parts).astype(np.float32)
        return ROIEncodedFeatures(vector=vector, source_dim=int(vector.shape[0]))

    def encode_images(self, images_bgr: list[np.ndarray]) -> np.ndarray:
        return np.stack([self.encode(image).vector for image in images_bgr], axis=0)

    def encode_batch(self, image_paths: list[str | Path]) -> np.ndarray:
        images: list[np.ndarray] = []
        for image_path in image_paths:
            image = cv2.imread(str(image_path))
            if image is None:
                raise FileNotFoundError(f"Unable to read ROI image: {image_path}")
            images.append(image)
        return self.encode_images(images)
