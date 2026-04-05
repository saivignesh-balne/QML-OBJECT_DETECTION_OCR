# Hybrid Quantum-Enhanced Object Detection and OCR Pipeline

## Scope

This folder is a production-style scaffold for:

1. Image preprocessing
2. Object detection with `YOLO` or `Faster R-CNN`
3. ROI extraction
4. Classical feature extraction
5. Quantum feature encoding
6. Hybrid classification with `QSVC` or `VQC`
7. OCR with `Tesseract` and `TrOCR`
8. Structured JSON output

Reference classes:

- `chip_packet`
- `medicine_box`
- `bottle`

Class intent:

- `chip_packet`: any snack or chips packet
- `medicine_box`: any medicine package or medicine box
- `bottle`: bottle with label text if readable, otherwise object detected with `No label`
- any other detected object: return `unidentified object detected`

## Presentation Brief

For a manager-facing, presentation-style explanation of:

- classical vs hybrid quantum vs pure quantum
- advantages and disadvantages
- when each approach is the better choice
- how to position the project in a review or demo

see:

- [docs/PRESENTATION_BRIEF.md](docs/PRESENTATION_BRIEF.md)
- [docs/FULL_PROJECT_REPORT.md](docs/FULL_PROJECT_REPORT.md)
- [docs/FULL_PROJECT_REPORT.tex](docs/FULL_PROJECT_REPORT.tex)
- [docs/EVALUATION_PRESENTATION_SCRIPT.txt](docs/EVALUATION_PRESENTATION_SCRIPT.txt)
- [docs/INTERNSHIP_EVALUATION_PRESENTATION.pptx](docs/INTERNSHIP_EVALUATION_PRESENTATION.pptx)

PowerPoint generator:

- `python build_evaluation_presentation.py`

## Architecture Diagram

```text
Input image
  |
  v
[OpenCV preprocessing]
  - denoise
  - CLAHE contrast enhancement
  - adaptive binarization
  |
  v
[Detector]
  - YOLO
  - Faster R-CNN
  |
  v
[ROIs]
  |------------------------------|
  v                              v
[OCR branch]                 [Classification branch]
  - Tesseract OCR             - ResNet18 embedding
  - TrOCR                     - HOG
  - best-result selection     - color histogram
                               - angle/amplitude encoding
                               - QSVC or VQC
  |------------------------------|
  v
JSON + annotated image
```

## Project Layout

```text
hybrid_qml_ocr_pipeline/
  requirements.txt
  ui_app.py
  build_benchmark_report.py
  train_detector_yolo.py
  train_hybrid.py
  run_pipeline.py
  ui_templates/
  ui_static/
  src/hybrid_qml_ocr/
    config.py
    preprocess.py
    detector.py
    features.py
    quantum.py
    hybrid_models.py
    ocr.py
    pipeline.py
```

## UI Dashboard

The project now includes a React frontend with a Flask API backend for:

- sidebar navigation
- step-by-step workflow pages with next/previous flow
- artifact and dependency status
- detector training
- hybrid classifier training
- benchmark report generation
- best-pipeline recommendation
- upload-based object analysis
- preprocessing previews
- annotated detection output
- per-ROI OCR and quantum classification details
- runtime stage benchmarks
- benchmark leaderboard rendering from `artifacts/benchmark_report.json`
- a dedicated future model room for adding more model families later

Current quick-start mode:

- If you only place data in `data/roi_classifier`, the app works in `ROI upload mode`.
- In that mode, uploaded images are assumed to already be cropped to one object.
- Detector training becomes optional and can be added later.

Frontend build:

```bash
npm install
npm run build:ui
```

Run the UI backend:

```bash
python ui_app.py
```

Open:

```text
http://127.0.0.1:5001
```

## UI-Only Flow

You can now do the full workflow from the UI:

1. Open the dashboard.
2. Use the left sidebar to move between `Overview`, `Workflow`, `Training`, `Benchmarks`, `Inference Lab`, and `Model Room`.
3. Put cropped bottle, chip packet, and medicine box images into `data/roi_classifier`.
4. In `Training`, train the hybrid classifier first.
5. Optionally train the detector later if you want full-scene object detection.
6. The app automatically refreshes the benchmark report after successful training, or you can click `Generate Benchmark Report`.
7. In `Inference Lab`, upload a cropped image to use ROI upload mode immediately.
8. In `Workflow`, move step-by-step with next/previous controls to follow the pipeline process.
9. In `Benchmarks`, inspect the recommended stack and score tables.
10. In `Model Room`, keep space reserved for future detectors, OCR models, and hybrid pipelines.
11. The UI will show:
   - original image
   - denoised image
   - contrast-enhanced image
   - binarized image
   - annotated detection result or ROI-mode full-image box
   - per-object label
   - OCR output
   - quantum model details
   - runtime benchmark timings

Required data layout:

- detector training: a YOLO dataset YAML pointing to train/val image and label folders
- classifier training: a ROI folder with one subfolder per class

Example ROI classifier layout:

```text
data/roi_classifier/
  chip_packet/
  medicine_box/
  bottle/
```

Best-pipeline behavior:

- if `artifacts/benchmark_report.json` exists, the UI uses its `recommended_pipeline`
- otherwise it falls back to the best available local detector weight, the first available classifier artifact, and OCR ensemble mode

Expected benchmark report shape:

```json
{
  "generated_at": "2026-04-04T15:00:00",
  "recommended_pipeline": {
    "detector_backend": "yolo",
    "detector_weights": "weights/yolo_custom.pt",
    "classifier_artifact": "artifacts/hybrid_qml_classifier.pkl",
    "classifier_name": "QSVC Angle Encoding",
    "ocr_backend": "ensemble"
  },
  "leaderboard": [
    {
      "pipeline": "YOLO + QSVC + OCR Ensemble",
      "accuracy": 0.94,
      "macro_f1": 0.93,
      "notes": "validation split"
    }
  ],
  "classifier_benchmarks": [],
  "detector_benchmarks": [],
  "ocr_benchmarks": [],
  "notes": [
    "Populate this file with real validation metrics to drive best-pipeline selection."
  ]
}
```

## 1. Image Preprocessing

Detection and OCR use different preprocessing paths:

```python
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


def preprocess_roi_for_ocr(roi_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    upscaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    filtered = cv2.bilateralFilter(upscaled, 7, 50, 50)
    binary = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((2, 2), dtype=np.uint8))
```

## 2. Detection and ROI Extraction

The detector stage localizes candidate objects and the ROI stage crops them with padding:

```python
class YoloDetector(BaseDetector):
    def detect(self, image_bgr: np.ndarray) -> list[Detection]:
        result = self.model.predict(
            source=image_bgr,
            conf=self.config.confidence_threshold,
            imgsz=self.config.image_size,
            device=self.config.device,
            max_det=self.config.max_detections,
            verbose=False,
        )[0]
        ...


def crop_roi(image_bgr: np.ndarray, box: tuple[int, int, int, int], padding_ratio: float = 0.04) -> np.ndarray:
    ...
```

YOLO detector training:

```bash
python train_detector_yolo.py ^
  --dataset-yaml data/custom_objects.yaml ^
  --model yolov8n.pt ^
  --epochs 60 ^
  --imgsz 960 ^
  --device cuda
```

## 3. Classical ROI Features

Each ROI is turned into a classical feature vector before quantum encoding:

```python
class ROIHybridFeatureExtractor:
    def encode(self, image_bgr: np.ndarray) -> ROIEncodedFeatures:
        parts: list[np.ndarray] = []
        if self.cnn_extractor is not None:
            parts.append(self.cnn_extractor.encode(image_bgr))
        if self.config.use_hog:
            parts.append(extract_hog_features(image_bgr))
        if self.config.use_color_histogram:
            parts.append(extract_color_histogram(image_bgr))
        vector = np.concatenate(parts).astype(np.float32)
        return ROIEncodedFeatures(vector=vector, source_dim=int(vector.shape[0]))
```

## 4. Quantum Feature Encoding

### Angle Encoding

```python
def angle_encoding_circuit(features: np.ndarray, n_qubits: int) -> QuantumCircuit:
    angles = scale_to_angles(features, n_qubits)
    circuit = QuantumCircuit(n_qubits)
    for qubit, angle in enumerate(angles):
        circuit.ry(float(angle), qubit)
    for qubit in range(n_qubits - 1):
        circuit.cx(qubit, qubit + 1)
    return circuit
```

### Amplitude Encoding

```python
def amplitude_encoding_circuit(features: np.ndarray, n_qubits: int) -> QuantumCircuit:
    amplitudes = normalize_amplitudes(features, n_qubits)
    circuit = QuantumCircuit(n_qubits)
    circuit.append(StatePreparation(amplitudes), range(n_qubits))
    return circuit
```

### Classical-to-Quantum Projection

```python
class ClassicalToQuantumEncoder:
    @property
    def target_dim(self) -> int:
        if self.config.encoding == "angle":
            return self.config.n_qubits
        return 2**self.config.n_qubits

    def transform(self, features: np.ndarray) -> np.ndarray:
        scaled = self.scaler.transform(features)
        reduced = self.reducer.transform(scaled)
        reduced = self._post_reduce(reduced)
        if self.config.encoding == "angle":
            return self.angle_scaler.transform(reduced).astype(np.float32)
        return np.stack([normalize_amplitudes(sample, self.config.n_qubits) for sample in reduced], axis=0)
```

## 5. Hybrid Quantum Models

### Quantum Kernel + SVM

```python
class QuantumKernelSVMClassifier(BaseHybridQuantumClassifier):
    def fit(self, features: np.ndarray, labels: list[str] | np.ndarray) -> "QuantumKernelSVMClassifier":
        encoded_labels = self.label_encoder.transform(np.asarray(labels))
        quantum_inputs = self.encoder.fit_transform(np.asarray(features, dtype=np.float32))
        feature_map = build_feature_map(self.config)
        self.model = QSVC(quantum_kernel=FidelityStatevectorKernel(feature_map=feature_map))
        self.model.fit(quantum_inputs, encoded_labels)
        return self
```

### Variational Quantum Classifier

```python
class VariationalQuantumClassifier(BaseHybridQuantumClassifier):
    def fit(self, features: np.ndarray, labels: list[str] | np.ndarray) -> "VariationalQuantumClassifier":
        encoded_labels = self.label_encoder.transform(np.asarray(labels))
        quantum_inputs = self.encoder.fit_transform(np.asarray(features, dtype=np.float32))
        self.model = VQC(
            feature_map=build_feature_map(self.config),
            ansatz=build_ansatz(self.config),
            loss="cross_entropy",
            optimizer=COBYLA(maxiter=self.config.maxiter),
            sampler=StatevectorSampler(),
            interpret=MulticlassInterpret(num_classes=len(self.config.class_names)),
            output_shape=len(self.config.class_names),
        )
        self.model.fit(quantum_inputs, one_hot(encoded_labels, num_classes=len(self.config.class_names)))
        return self
```

Hybrid classifier training:

```bash
python train_hybrid.py ^
  --dataset-dir data/roi_classifier ^
  --artifact-path artifacts/hybrid_qml_classifier.pkl ^
  --model-type qsvc ^
  --encoding angle ^
  --n-qubits 6 ^
  --device cuda
```

## 6. OCR

Both OCR backends are implemented:

```python
class TesseractOCR:
    def run(self, roi_bgr: np.ndarray) -> OCRResult:
        binary = preprocess_roi_for_ocr(roi_bgr)
        data = pytesseract.image_to_data(
            binary,
            config=f"--oem 3 --psm {self.config.tesseract_psm}",
            output_type=Output.DICT,
        )
        ...


class TrOCROCR:
    def run(self, roi_bgr: np.ndarray) -> OCRResult:
        processed = preprocess_roi_for_ocr(roi_bgr)
        pil_image = Image.fromarray(processed)
        pixel_values = self.processor(images=pil_image, return_tensors="pt").pixel_values.to(self.device)
        generated = self.model.generate(pixel_values, max_new_tokens=self.config.max_new_tokens)
        text = self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
        return OCRResult(text=text, confidence=None, backend="trocr")
```

## 7. End-to-End Inference

```bash
python run_pipeline.py ^
  --image samples/medicine_shelf.jpg ^
  --artifact-path artifacts/hybrid_qml_classifier.pkl ^
  --detector-backend yolo ^
  --detector-weights weights/yolo_custom.pt ^
  --class-names chip_packet medicine_box bottle ^
  --ocr-backend ensemble ^
  --device cuda ^
  --output-dir outputs
```

Pipeline orchestration:

```python
class HybridQMLOCRPipeline:
    def run(self, image_path: str | Path) -> dict[str, Any]:
        image = read_image(image_path)
        preprocessed = preprocess_for_detection(image)
        detections = self.detector.detect(preprocessed.contrast_bgr)
        for detection in detections:
            roi = crop_roi(preprocessed.contrast_bgr, detection.bbox)
            feature_vector = self.features.encode(roi).vector.reshape(1, -1)
            object_label = self.classifier.predict(feature_vector)[0]
            selected_ocr, raw_ocr_results = self.ocr.run(roi)
            ...
```

## 8. Example Output

```json
{
  "image_path": "samples/medicine_shelf.jpg",
  "num_detections": 2,
  "results": [
    {
      "detector_label": "medicine_box",
      "detector_confidence": 0.93,
      "bbox": [112, 84, 358, 278],
      "object_label": "medicine_box",
      "extracted_text": "Paracetamol 500mg",
      "ocr_backend": "trocr",
      "ocr_candidates": [
        {
          "text": "Paracetamol 500mg",
          "confidence": 0.82,
          "backend": "tesseract"
        },
        {
          "text": "Paracetamol 500mg",
          "confidence": null,
          "backend": "trocr"
        }
      ]
    },
    {
      "detector_label": "bottle",
      "detector_confidence": 0.88,
      "bbox": [412, 72, 506, 301],
      "object_label": "bottle",
      "extracted_text": "No label",
      "ocr_backend": "none",
      "ocr_candidates": [
        {
          "text": "",
          "confidence": null,
          "backend": "tesseract"
        },
        {
          "text": "",
          "confidence": null,
          "backend": "trocr"
        }
      ]
    }
  ],
  "annotated_image": "outputs/medicine_shelf_annotated.jpg"
}
```

Text handling rule:

- If readable printed text is found, return the extracted text.
- If no readable text is found on `chip_packet`, `medicine_box`, or `bottle`, keep the detected object class and set `extracted_text` to `No label`.
- If the detector returns any object outside the supported classes, set `object_label` to `unidentified object detected`.

## Self-Check

Requested scope covered:

- preprocessing
- object detection
- ROI extraction
- angle encoding
- amplitude encoding
- quantum kernel + SVM
- VQC
- Tesseract OCR
- deep OCR with TrOCR
- end-to-end inference
- example output
