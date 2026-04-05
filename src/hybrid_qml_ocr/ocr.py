from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytesseract
import torch
from PIL import Image
from pytesseract import Output, TesseractNotFoundError
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from .config import OCRConfig
from .preprocess import preprocess_roi_for_ocr, preprocess_roi_for_trocr


@dataclass
class OCRResult:
    text: str
    confidence: float | None
    backend: str
    error: str | None = None
    boxes: list[dict[str, object]] | None = None


def score_ocr_result(result: OCRResult) -> float:
    text = (result.text or "").strip()
    if not text:
        return -1.0
    confidence = result.confidence if result.confidence is not None else 0.55
    alnum_chars = sum(character.isalnum() for character in text)
    alnum_ratio = alnum_chars / max(1, len(text))
    mixed_token_bonus = 0.15 if any(character.isdigit() for character in text) and any(character.isalpha() for character in text) else 0.0
    length_bonus = min(len(text), 24) / 24.0 * 0.1
    return float(confidence + (0.25 * alnum_ratio) + mixed_token_bonus + length_bonus)


class TesseractOCR:
    def __init__(self, config: OCRConfig) -> None:
        self.config = config
        self.available = True
        self.last_error: str | None = None
        if config.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = config.tesseract_cmd
        try:
            pytesseract.get_tesseract_version()
        except Exception as exc:
            self.available = False
            self.last_error = str(exc)

    def run(self, roi_bgr: np.ndarray) -> OCRResult:
        if not self.available:
            return OCRResult(text="", confidence=None, backend="tesseract", error=self.last_error)
        binary = preprocess_roi_for_ocr(roi_bgr)
        variants = [binary]
        if float(np.mean(binary)) < 127.0:
            variants.append(255 - binary)
        results: list[OCRResult] = []
        for variant_index, variant in enumerate(variants):
            for psm in [self.config.tesseract_psm, 6, 7, 11]:
                try:
                    data = pytesseract.image_to_data(
                        variant,
                        config=f"--oem 3 --psm {psm}",
                        output_type=Output.DICT,
                    )
                except TesseractNotFoundError as exc:
                    self.available = False
                    self.last_error = str(exc)
                    return OCRResult(text="", confidence=None, backend="tesseract", error=self.last_error)
                words: list[str] = []
                confidences: list[float] = []
                boxes: list[dict[str, object]] = []
                for text, conf, left, top, width, height in zip(
                    data["text"],
                    data["conf"],
                    data["left"],
                    data["top"],
                    data["width"],
                    data["height"],
                    strict=False,
                ):
                    cleaned = str(text).strip()
                    conf_value = float(conf) if str(conf).strip() not in {"", "-1"} else -1.0
                    if cleaned and conf_value >= 0.0:
                        words.append(cleaned)
                        confidences.append(conf_value)
                        boxes.append(self._map_box_to_roi(left, top, width, height, roi_bgr))
                mean_conf = float(np.mean(confidences) / 100.0) if confidences else None
                results.append(
                    OCRResult(
                        text=" ".join(words).strip(),
                        confidence=mean_conf,
                        backend="tesseract" if variant_index == 0 else "tesseract_inverted",
                        boxes=boxes,
                    )
                )
        return max(results, key=score_ocr_result, default=OCRResult("", None, "tesseract"))

    @staticmethod
    def _map_box_to_roi(
        left: int,
        top: int,
        width: int,
        height: int,
        roi_bgr: np.ndarray,
    ) -> dict[str, object]:
        border = 12.0
        scale = 3.0
        roi_height, roi_width = roi_bgr.shape[:2]
        x1 = max(0, int(round((float(left) - border) / scale)))
        y1 = max(0, int(round((float(top) - border) / scale)))
        w = max(1, int(round(float(width) / scale)))
        h = max(1, int(round(float(height) / scale)))
        x2 = min(roi_width, x1 + w)
        y2 = min(roi_height, y1 + h)
        return {
            "bbox": [x1, y1, x2, y2],
            "left": x1,
            "top": y1,
            "right": x2,
            "bottom": y2,
        }


class TrOCROCR:
    def __init__(self, config: OCRConfig) -> None:
        self.config = config
        self.device = torch.device(config.device)
        self.available = True
        self.last_error: str | None = None
        self.processor = None
        self.model = None
        try:
            self.processor = TrOCRProcessor.from_pretrained(config.trocr_model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(config.trocr_model_name)
            self.model.to(self.device)
            self.model.eval()
        except Exception as exc:
            self.available = False
            self.last_error = str(exc)

    def run(self, roi_bgr: np.ndarray) -> OCRResult:
        if not self.available or self.processor is None or self.model is None:
            return OCRResult(text="", confidence=None, backend="trocr", error=self.last_error)
        try:
            variants = [
                ("trocr_color", preprocess_roi_for_trocr(roi_bgr)),
                ("trocr_binary", np.repeat(preprocess_roi_for_ocr(roi_bgr)[..., None], 3, axis=2)),
            ]
            results: list[OCRResult] = []
            for backend_name, processed in variants:
                pil_image = Image.fromarray(processed)
                pixel_values = self.processor(images=pil_image, return_tensors="pt").pixel_values.to(self.device)
                with torch.no_grad():
                    generated = self.model.generate(
                        pixel_values,
                        max_new_tokens=self.config.max_new_tokens,
                    )
                text = self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
                results.append(OCRResult(text=text, confidence=None, backend=backend_name, boxes=[]))
            return max(results, key=score_ocr_result, default=OCRResult("", None, "trocr"))
        except Exception as exc:
            self.last_error = str(exc)
            return OCRResult(text="", confidence=None, backend="trocr", error=self.last_error)


def select_best_ocr_result(results: list[OCRResult]) -> OCRResult:
    populated = [result for result in results if result.text]
    if not populated:
        return OCRResult(text="", confidence=None, backend="none", boxes=[])
    return max(populated, key=score_ocr_result)


class OCRExecutor:
    def __init__(self, config: OCRConfig) -> None:
        self.config = config
        self.tesseract = TesseractOCR(config) if config.backend in {"tesseract", "ensemble"} else None
        self.trocr = TrOCROCR(config) if config.backend in {"trocr", "ensemble"} else None

    def run(self, roi_bgr: np.ndarray) -> tuple[OCRResult, list[OCRResult]]:
        if self.config.backend == "tesseract":
            if self.tesseract is None:
                result = OCRResult(text="", confidence=None, backend="tesseract", error="Tesseract backend was not initialized.")
                return result, [result]
            result = self.tesseract.run(roi_bgr)
            return result, [result]
        if self.config.backend == "trocr":
            if self.trocr is None:
                result = OCRResult(text="", confidence=None, backend="trocr", error="TrOCR backend was not initialized.")
                return result, [result]
            result = self.trocr.run(roi_bgr)
            return result, [result]
        results: list[OCRResult] = []
        if self.tesseract is not None:
            results.append(self.tesseract.run(roi_bgr))
        if self.trocr is not None:
            results.append(self.trocr.run(roi_bgr))
        if not results:
            results = [OCRResult(text="", confidence=None, backend="none", error="No OCR backend was initialized.")]
        return select_best_ocr_result(results), results
