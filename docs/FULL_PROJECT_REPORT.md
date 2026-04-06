# Full Project Report: Hybrid Quantum-Enhanced Object Detection and OCR Pipeline

## Title

**Hybrid Quantum-Enhanced Object Detection, Classification, and OCR for QML Research and Development**

## Authoring Context

This report documents the end-to-end design, implementation, benchmarking, and deployment rationale of the `hybrid_qml_ocr_pipeline` project. It is written as a full A-to-Z project report based on the current implementation and measured benchmark outputs available in the repository as of **April 5, 2026**.

## Abstract

This project implements a full pipeline for detecting objects such as bottles, chip packets, and medicine boxes, classifying them with classical and hybrid quantum machine learning models, and extracting printed text from them with OCR. The system combines OpenCV preprocessing, YOLO-based object detection, ROI extraction, classical feature engineering, quantum feature encoding, hybrid quantum classifiers built with Qiskit, and OCR backends using Tesseract and TrOCR. A React + Flask user interface supports dataset preparation, model training, benchmark generation, and inference visualization from one workspace.

The project was designed not only to achieve end-to-end functional performance, but also to answer a research and product question: **when does a hybrid quantum model add value compared with a strong classical baseline?** On the current ROI classification dataset, the best classical models and one quantum amplitude-encoding kernel model all reach **99.5% held-out accuracy**, while the broader quantum family average remains below the classical family average. The current recommended production stack is therefore **YOLO detector + Classical SVM (RBF) + OCR Ensemble**, while the hybrid quantum branch remains the primary innovation and research track.

## Keywords

- Quantum Machine Learning
- Hybrid Quantum-Classical Systems
- Object Detection
- OCR
- YOLO
- Qiskit
- Computer Vision
- TrOCR
- Tesseract
- ROI Classification

## 1. Introduction

Object detection with OCR is a realistic applied computer-vision problem because the task is not limited to identifying an object class. A useful system must also locate the item in the image, distinguish among visually similar object categories, and recover printed text that may be partially visible, reflective, or distorted by lighting and perspective.

This project addresses that problem by integrating three major subsystems:

1. object detection
2. ROI classification
3. OCR-based text extraction

The distinguishing feature of the project is its controlled comparison between:

- classical classifiers
- hybrid quantum classifiers
- quantum-oriented classifier families using multiple encodings and kernels

Instead of assuming quantum is better, the project evaluates whether quantum adds measurable value on the same task and dataset.

## 2. Problem Statement

The target problem is to process an image and produce:

- the detected object type
- the extracted text, if text is readable
- a clean visual output showing the object and the recognized text region

The supported classes are:

- `chip_packet`
- `medicine_box`
- `bottle`

The system must also handle:

- no readable text
- unsupported detector outputs
- cropped ROI-only inference mode
- full-scene object detection mode

The business objective is to build a presentation-ready and benchmark-driven system that supports both practical deployment decisions and research comparisons.

## 3. Project Objectives

The project objectives were:

1. Build a production-style end-to-end pipeline for object detection, classification, and OCR.
2. Implement quantum feature encoding using both angle encoding and amplitude encoding.
3. Implement hybrid quantum models including quantum-kernel SVM and variational quantum classifiers.
4. Compare classical and quantum approaches under the same evaluation setup.
5. Create a UI that supports training, benchmarking, and inference in a presentation-ready format.
6. Produce results that are technically honest, reproducible, and easy to present to non-specialist stakeholders.

## 4. Scope

### Included

- image preprocessing
- full-scene object detection
- ROI extraction
- classical ROI feature extraction
- angle encoding
- amplitude encoding
- quantum kernel SVM
- variational quantum classifier
- OCR using Tesseract and TrOCR
- benchmark generation
- UI-based training and inference

### Excluded

- custom OCR fine-tuning
- deployment to cloud/mobile infrastructure
- pure quantum end-to-end image processing
- open-set detector retraining for arbitrary unknown object families

## 5. System Overview

### 5.1 End-to-End Flow

```text
Input Image
  ->
OpenCV Preprocessing
  ->
Object Detection
  ->
ROI Extraction
  ->
Classical Feature Extraction
  ->
Classical or Hybrid Quantum Classification
  ->
OCR
  ->
Annotated Full-Image Output + Structured JSON
```

### 5.2 Dual Operating Modes

The system supports two practical modes:

#### ROI upload mode

- used when the detector is skipped
- intended for already-cropped single-object images
- useful for classifier-first experiments

#### Full pipeline mode

- detector identifies the object in the full image
- ROI is extracted automatically
- classifier and OCR run on the ROI

## 6. Repository Structure

```text
hybrid_qml_ocr_pipeline/
  artifacts/
  data/
  docs/
  frontend/
  src/hybrid_qml_ocr/
  ui_app.py
  train_detector_yolo.py
  train_hybrid.py
  train_model_suite.py
  build_benchmark_report.py
  run_pipeline.py
```

## 7. Dataset Design

The project uses separate datasets for detection and ROI classification.

### 7.1 Detection Dataset

The detector uses a YOLO-style dataset with:

- `images/train`
- `images/val`
- `labels/train`
- `labels/val`

Each label file follows YOLO format:

```text
<class_id> <x_center> <y_center> <width> <height>
```

### 7.2 ROI Classification Dataset

The ROI classifier uses cropped object images organized by class:

```text
data/roi_classifier/
  bottle/
  chip_packet/
  medicine_box/
```

### 7.3 Current ROI Dataset Statistics

From the saved classifier summaries:

- total ROI samples: `997`
- train split before balancing: `797`
- test split: `200`

Training class counts before balancing:

- `bottle`: `246`
- `chip_packet`: `202`
- `medicine_box`: `349`

Augmented samples added during balancing:

- `bottle`: `103`
- `chip_packet`: `147`
- `medicine_box`: `0`

Balanced training size:

- `1047`

## 8. Preprocessing Pipeline

The preprocessing stage uses OpenCV and contains separate paths for detection and OCR.

### 8.1 Detection Preprocessing

Detection preprocessing performs:

- noise reduction
- contrast enhancement
- binarization

The implemented operations include:

- fast non-local means denoising
- CLAHE-based contrast enhancement
- adaptive thresholding

### 8.2 OCR Preprocessing

OCR uses a more text-focused path:

- grayscale conversion
- upscaling
- bilateral filtering
- CLAHE enhancement
- sharpening
- adaptive thresholding and Otsu thresholding
- morphological closing

This is used to improve the readability of package text before OCR inference.

## 9. Object Detection

The detector subsystem is built around YOLO.

### 9.1 Detector Configuration

The saved detector summary reports the following training setup:

- base model: `yolov8n.pt`
- epochs: `30`
- image size: `640`
- batch size: `8`
- device: `cpu`

### 9.2 Detector Metrics

| Metric | Value |
|---|---:|
| Precision | 0.90054 |
| Recall | 0.94974 |
| mAP@50 | 0.95593 |
| mAP@50-95 | 0.61159 |

These values indicate that the detector is strong at object localization and retrieval, but the stricter `mAP@50-95` score shows there is still room to improve box quality and localization robustness under tighter thresholds.

## 10. ROI Feature Extraction

The classification branch does not feed raw images directly into quantum circuits. Instead, the project uses a hybrid feature extractor that produces a compact classical representation before classification.

The feature extractor uses combinations of:

- CNN embeddings
- HOG features
- LBP-style texture features
- color histogram features

This makes the project realistic for near-term quantum experiments because current quantum models cannot practically operate on full-resolution image tensors.

## 11. Quantum Feature Encoding

Two encoding strategies are implemented.

### 11.1 Angle Encoding

Angle encoding maps reduced classical features into rotation angles:

\[
\theta_i \in [0, \pi]
\]

Each qubit receives a rotation:

\[
R_y(\theta_i)
\]

This encoding is compact and suitable when the target dimensionality is the number of qubits.

### 11.2 Amplitude Encoding

Amplitude encoding maps a classical feature vector into a quantum state:

\[
\lvert \psi \rangle = \sum_{i=0}^{2^n - 1} a_i \lvert i \rangle
\]

subject to:

\[
\sum_i |a_i|^2 = 1
\]

This encoding can be more information-dense because it uses the amplitudes of the full quantum state, but it is more numerically sensitive and requires careful normalization.

## 12. Quantum Models Implemented

The project includes multiple model families.

### 12.1 Classical Baselines

- Classical SVM (RBF)
- Logistic Regression
- Random Forest
- MLP

### 12.2 Quantum Kernel Models

- QSVM ZZ kernel linear
- QSVM ZZ kernel full
- QSVM Pauli kernel
- QSVM amplitude-encoding variant

### 12.3 Variational Quantum Models

- VQC with RealAmplitudes ansatz
- VQC with EfficientSU2 ansatz

## 13. OCR Subsystem

The OCR layer is implemented as a dual-backend system:

- Tesseract OCR
- TrOCR

The project also uses an OCR ensemble policy that selects the best non-empty OCR result.

### OCR Output Policy

- if text is readable, return the extracted text
- if no text is readable, return `No label`
- if the object class is unsupported, return `unidentified object detected`

## 14. User Interface

The UI is built with:

- Flask backend
- React frontend

The UI supports:

- dataset readiness checks
- detector training
- ROI classifier training
- comparison suite execution
- benchmark generation
- full-image inference
- comparison charts and tables

The interface is designed to support both engineering iteration and manager-facing presentation.

## 15. Experimental Methodology

### 15.1 Benchmark Principle

All classifier families are evaluated on the same ROI dataset split and use the same general feature-extraction pipeline. This makes the comparison more fair than comparing unrelated pipelines.

### 15.2 Key Evaluation Metrics

For classifiers:

- accuracy
- macro F1
- weighted F1
- training time

For detection:

- precision
- recall
- mAP@50
- mAP@50-95

### 15.3 Important Evaluation Note

The current full-pipeline leaderboard in the benchmark report uses a **composite proxy score**:

\[
\text{Composite Score} = \frac{\text{Detector mAP@50-95} + \text{Classifier Accuracy}}{2}
\]

This is useful for ranking candidate stacks quickly, but it is **not the same thing as a true end-to-end validation score**. The report should therefore present this honestly as a proxy rather than as a final field accuracy metric.

## 16. Results

### 16.1 Current Recommended Pipeline

The current recommended stack from the benchmark report is:

- detector: `YOLO`
- classifier: `Classical SVM (RBF)`
- OCR: `Ensemble`

### 16.2 Detector Result

| Component | Best Current Choice | Key Metric |
|---|---|---:|
| Detector | YOLO (`qml_ocr_detector_best.pt`) | mAP@50-95 = `0.61159` |

### 16.3 Classifier Results

| Model | Family | Encoding | Accuracy | Macro F1 | Train Time (s) |
|---|---|---|---:|---:|---:|
| Classical SVM (RBF) | Classical | Classical projection | 0.995 | 0.99543 | 54.49 |
| Logistic Regression | Classical | Classical projection | 0.995 | 0.99543 | 54.62 |
| MLP Classifier | Classical | Classical projection | 0.995 | 0.99543 | 54.97 |
| QSVM ZZ Kernel Linear | Quantum | Amplitude | 0.995 | 0.99543 | 519.16 |
| Random Forest | Classical | Classical projection | 0.990 | 0.99088 | 61.87 |
| QSVM Pauli Kernel | Quantum | Angle | 0.900 | 0.89910 | 513.67 |
| QSVM ZZ Kernel Linear | Quantum | Angle | 0.810 | 0.81339 | 468.06 |
| QSVM ZZ Kernel Full | Quantum | Angle | 0.745 | 0.74539 | 920.36 |
| VQC RealAmplitudes | Quantum | Angle | 0.440 | 0.43485 | 131.27 |
| VQC EfficientSU2 | Quantum | Angle | 0.430 | 0.42986 | 141.86 |

### 16.4 Family-Level Summary

| Family | Count | Best Model | Best Accuracy | Average Accuracy | Average Macro F1 |
|---|---:|---|---:|---:|---:|
| Classical | 4 | Classical SVM (RBF) | 0.995 | 0.99375 | 0.99429 |
| Quantum | 6 | QSVM ZZ Kernel Linear (amplitude) | 0.995 | 0.72000 | 0.71967 |

## 17. Interpretation of Results

### 17.1 What the Results Mean

The current results lead to an important conclusion:

- the **best production candidate** is currently classical
- the **best quantum candidate** is the amplitude-encoding QSVM
- the **average quantum family performance** is well below the classical family average

This means the strongest evidence-based statement is:

> Classical models are currently the safest production choice on this dataset, while hybrid quantum models remain valuable as a research and innovation branch.

### 17.2 Important Observation

The amplitude-encoding QSVM matches the best classical accuracy at `99.5%`, which is a meaningful result. However, it requires much more training time:

- Classical SVM: about `54.49` seconds
- Amplitude QSVM: about `519.16` seconds

So the quantum model is competitive in accuracy but not yet attractive as the default production choice when cost and speed are considered.

## 18. Classical vs Hybrid Quantum vs Pure Quantum

| Approach | How It Works Here | Advantages | Disadvantages | Best Use |
|---|---|---|---|---|
| Classical | OpenCV + ROI features + classical classifier | Fast, strong baselines, easier deployment, low complexity | Less research novelty | Best production option |
| Hybrid Quantum | Classical preprocessing + compressed features + quantum kernel/VQC | Good research value, realistic near-term quantum setup, fair comparison | Higher complexity, slower training, gains must be justified | Best innovation track |
| Pure Quantum | Direct quantum image encoding and classification | High novelty and future strategic interest | Not practical for this task today | Future direction only |

## 19. Advantages of the Implemented System

The project has several strong engineering advantages:

- full pipeline from detection to OCR
- reproducible saved artifacts
- UI-based workflow for training and inference
- fair comparison between model families
- presentation-ready visualization
- practical support for both ROI-only and full-image modes

The project also has strong research advantages:

- multiple quantum encodings
- multiple quantum model families
- direct comparison against strong classical baselines
- honest evidence about what quantum helps and where it does not

## 20. Limitations

The current project still has important limitations:

1. The full-pipeline leaderboard uses a proxy composite score rather than true end-to-end validation.
2. OCR quality is still dependent on image quality and backend availability.
3. Quantum models are simulated rather than run on production quantum hardware.
4. Pure quantum image processing is not feasible in this setting today.
5. Detector performance, while strong, still has moderate strict mAP under the `50-95` metric.

## 21. Risks

The main practical risks are:

- detector localization errors degrading downstream classification and OCR
- OCR failure on reflective or low-resolution labels
- over-reliance on ROI data that may be cleaner than real-world inputs
- presenting proxy composite scores as if they were field-validated end-to-end results

## 22. Recommendations

### 22.1 Deployment Recommendation

Use the current recommended stack for deployment-oriented demos:

- YOLO detector
- Classical SVM (RBF)
- OCR Ensemble

### 22.2 Research Recommendation

Retain the hybrid quantum track, especially:

- amplitude-encoding QSVM
- Pauli-kernel QSVM

These are the most credible quantum-side performers in the current benchmark set.

### 22.3 Evaluation Recommendation

The next major improvement should be a true end-to-end validation benchmark with:

- full-scene test images
- measured detection + classification + OCR accuracy together
- per-class and per-condition breakdown

## 23. Future Work

Recommended next steps:

1. Add full end-to-end field validation instead of relying only on proxy composite ranking.
2. Improve OCR robustness with label-specific OCR preprocessing and optional fine-tuning.
3. Add stronger open-set handling for unsupported objects.
4. Explore richer quantum kernels and encoding compression strategies.
5. Compare CPU and GPU training/inference tradeoffs where available.
6. Add exportable benchmark reports for management review and auditability.

## 24. Conclusion

This project successfully implements a full object detection, classification, and OCR workflow with a defensible comparison between classical and hybrid quantum approaches. The system is technically complete, benchmark-aware, UI-driven, and suitable for both demo and research presentation.

The main conclusion is clear:

- **Classical models are currently the best default production choice**
- **Hybrid quantum models provide real innovation value and at least one competitive accuracy result**
- **Pure quantum processing remains a future direction rather than a practical choice for this image task**

This is a strong project outcome because it provides both:

- a reliable deployment path
- a measurable innovation path

## 25. Appendix A: Current File Outputs

Key generated assets include:

- detector summary: `artifacts/qml_ocr_detector.summary.json`
- classifier summaries: `artifacts/*.summary.json`
- benchmark report: `artifacts/benchmark_report.json`
- presentation brief: `docs/PRESENTATION_BRIEF.md`

## 26. Appendix B: Example Final Output Structure

Typical inference output contains:

- full-image result preview
- predicted object label
- extracted text
- text-region boxes
- runtime charts
- model comparison table

## 27. Appendix C: References

Indicative technical references used by the implementation stack:

- Ultralytics YOLO
- Qiskit and Qiskit Machine Learning
- PyTorch
- OpenCV
- Tesseract OCR
- Microsoft TrOCR
