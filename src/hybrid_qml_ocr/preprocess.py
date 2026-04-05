from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class PreprocessResult:
    original_bgr: np.ndarray
    denoised_bgr: np.ndarray
    contrast_bgr: np.ndarray
    binary: np.ndarray


def read_image(image_path: str | Path) -> np.ndarray:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Unable to read image: {image_path}")
    return image


def reduce_noise(image_bgr: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(image_bgr, None, 8, 8, 7, 21)


def enhance_contrast(image_bgr: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_l = clahe.apply(l_channel)
    merged = cv2.merge([enhanced_l, a_channel, b_channel])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def binarize(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )


def preprocess_for_detection(image_bgr: np.ndarray) -> PreprocessResult:
    denoised = reduce_noise(image_bgr)
    contrast = enhance_contrast(denoised)
    binary = binarize(contrast)
    return PreprocessResult(
        original_bgr=image_bgr,
        denoised_bgr=denoised,
        contrast_bgr=contrast,
        binary=binary,
    )


def crop_roi(
    image_bgr: np.ndarray,
    box: tuple[int, int, int, int],
    padding_ratio: float = 0.04,
) -> np.ndarray:
    height, width = image_bgr.shape[:2]
    x1, y1, x2, y2 = box
    pad_x = int((x2 - x1) * padding_ratio)
    pad_y = int((y2 - y1) * padding_ratio)
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(width, x2 + pad_x)
    y2 = min(height, y2 + pad_y)
    return image_bgr[y1:y2, x1:x2].copy()


def resize_for_model(image_bgr: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return cv2.resize(image_bgr, size, interpolation=cv2.INTER_AREA)


def preprocess_roi_for_ocr(roi_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    upscaled = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.bilateralFilter(upscaled, 9, 50, 50)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    sharpened = cv2.addWeighted(enhanced, 1.35, cv2.GaussianBlur(enhanced, (0, 0), 2.0), -0.35, 0)
    adaptive = cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        9,
    )
    otsu = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    adaptive_foreground = float(np.mean(adaptive == 0))
    binary = adaptive if 0.03 <= adaptive_foreground <= 0.55 else otsu
    kernel = np.ones((2, 2), dtype=np.uint8)
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    return cv2.copyMakeBorder(closed, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)


def preprocess_roi_for_trocr(roi_bgr: np.ndarray) -> np.ndarray:
    denoised = reduce_noise(roi_bgr)
    contrast = enhance_contrast(denoised)
    upscaled = cv2.resize(contrast, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    sharpened = cv2.addWeighted(upscaled, 1.2, cv2.GaussianBlur(upscaled, (0, 0), 2.0), -0.2, 0)
    bordered = cv2.copyMakeBorder(
        sharpened,
        16,
        16,
        16,
        16,
        cv2.BORDER_CONSTANT,
        value=(255, 255, 255),
    )
    return cv2.cvtColor(bordered, cv2.COLOR_BGR2RGB)


def build_classification_views(roi_bgr: np.ndarray) -> list[np.ndarray]:
    height, width = roi_bgr.shape[:2]
    margin_x = max(1, int(width * 0.04))
    margin_y = max(1, int(height * 0.04))
    if width > 2 * margin_x and height > 2 * margin_y:
        centered = roi_bgr[margin_y: height - margin_y, margin_x: width - margin_x]
        centered = cv2.resize(centered, (width, height), interpolation=cv2.INTER_CUBIC)
    else:
        centered = roi_bgr.copy()
    contrast = enhance_contrast(roi_bgr)
    sharpened = cv2.addWeighted(contrast, 1.2, cv2.GaussianBlur(contrast, (0, 0), 1.2), -0.2, 0)
    return [roi_bgr, sharpened, centered]
