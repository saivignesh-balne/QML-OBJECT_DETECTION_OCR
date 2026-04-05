from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


PROJECT_ROOT = Path(__file__).resolve().parent
DOCS_DIR = PROJECT_ROOT / "docs"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
BENCHMARK_PATH = ARTIFACTS_DIR / "benchmark_report.json"
DETECTOR_SUMMARY_PATH = ARTIFACTS_DIR / "qml_ocr_detector.summary.json"
OUTPUT_PPTX = DOCS_DIR / "INTERNSHIP_EVALUATION_PRESENTATION.pptx"
FALLBACK_OUTPUT_PPTX = DOCS_DIR / "INTERNSHIP_EVALUATION_PRESENTATION_QML_FOCUSED.pptx"

ACCENT = RGBColor(15, 155, 118)
ACCENT_DARK = RGBColor(13, 127, 97)
AMBER = RGBColor(197, 138, 49)
INK = RGBColor(23, 50, 45)
MUTED = RGBColor(92, 114, 107)
BG = RGBColor(250, 247, 239)
WHITE = RGBColor(255, 255, 255)
LINE = RGBColor(214, 224, 220)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def set_slide_background(slide) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG


def add_header(slide, eyebrow: str, title: str, subtitle: str | None = None) -> None:
    eyebrow_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(4.0), Inches(0.35))
    tf = eyebrow_box.text_frame
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = eyebrow.upper()
    r.font.name = "Arial"
    r.font.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = ACCENT_DARK

    title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.7), Inches(12.0), Inches(0.8))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.name = "Arial"
    r.font.bold = True
    r.font.size = Pt(24)
    r.font.color.rgb = INK

    if subtitle:
        subtitle_box = slide.shapes.add_textbox(Inches(0.6), Inches(1.35), Inches(12.0), Inches(0.5))
        tf = subtitle_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = subtitle
        r.font.name = "Arial"
        r.font.size = Pt(11)
        r.font.color.rgb = MUTED


def add_slide_number(slide, index: int, total: int) -> None:
    box = slide.shapes.add_textbox(Inches(12.2), Inches(7.0), Inches(0.8), Inches(0.25))
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    r = p.add_run()
    r.text = f"{index}/{total}"
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.color.rgb = MUTED


def add_bullet_panel(slide, x, y, w, h, bullets: list[str], font_size: int = 18) -> None:
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, x, y, w, h)
    fill = shape.fill
    fill.solid()
    fill.fore_color.rgb = WHITE
    shape.line.color.rgb = LINE

    tf = shape.text_frame
    tf.clear()
    tf.margin_left = Pt(12)
    tf.margin_right = Pt(8)
    tf.margin_top = Pt(8)
    tf.margin_bottom = Pt(8)
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.name = "Arial"
        p.font.size = Pt(font_size)
        p.font.color.rgb = INK
        p.bullet = True
        p.space_after = Pt(6)


def add_two_column_bullets(slide, left_title: str, left_bullets: list[str], right_title: str, right_bullets: list[str]) -> None:
    left_title_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(5.7), Inches(0.4))
    p = left_title_box.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = left_title
    r.font.name = "Arial"
    r.font.bold = True
    r.font.size = Pt(16)
    r.font.color.rgb = ACCENT_DARK

    right_title_box = slide.shapes.add_textbox(Inches(6.8), Inches(1.8), Inches(5.7), Inches(0.4))
    p = right_title_box.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = right_title
    r.font.name = "Arial"
    r.font.bold = True
    r.font.size = Pt(16)
    r.font.color.rgb = AMBER

    add_bullet_panel(slide, Inches(0.7), Inches(2.2), Inches(5.8), Inches(4.5), left_bullets, font_size=16)
    add_bullet_panel(slide, Inches(6.7), Inches(2.2), Inches(5.8), Inches(4.5), right_bullets, font_size=16)


def add_metric_chip(slide, x, y, label: str, value: str, color: RGBColor) -> None:
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, x, y, Inches(2.0), Inches(0.9))
    fill = shape.fill
    fill.solid()
    fill.fore_color.rgb = WHITE
    shape.line.color.rgb = color

    tf = shape.text_frame
    tf.clear()
    p1 = tf.paragraphs[0]
    r1 = p1.add_run()
    r1.text = label
    r1.font.name = "Arial"
    r1.font.size = Pt(11)
    r1.font.color.rgb = MUTED

    p2 = tf.add_paragraph()
    r2 = p2.add_run()
    r2.text = value
    r2.font.name = "Arial"
    r2.font.bold = True
    r2.font.size = Pt(18)
    r2.font.color.rgb = INK


def add_title_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    ribbon = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.2))
    ribbon.fill.solid()
    ribbon.fill.fore_color.rgb = ACCENT
    ribbon.line.color.rgb = ACCENT

    title_box = slide.shapes.add_textbox(Inches(0.7), Inches(1.5), Inches(11.8), Inches(1.6))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = "Research on Hybrid Quantum Machine Learning\nfor Object Classification and OCR"
    r.font.name = "Arial"
    r.font.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = INK

    subtitle = slide.shapes.add_textbox(Inches(0.8), Inches(3.25), Inches(8.0), Inches(1.2))
    tf = subtitle.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Internship Evaluation Presentation"
    p.font.name = "Arial"
    p.font.size = Pt(20)
    p.font.color.rgb = ACCENT_DARK
    p = tf.add_paragraph()
    p.text = f"Prepared for Mentor and Panel Evaluation | {date.today().strftime('%d %B %Y')}"
    p.font.name = "Arial"
    p.font.size = Pt(14)
    p.font.color.rgb = MUTED

    add_metric_chip(slide, Inches(9.2), Inches(3.0), "Primary Objective", "QML Research", ACCENT)
    add_metric_chip(slide, Inches(9.2), Inches(4.0), "Comparison", "Classical vs QML", AMBER)
    add_metric_chip(slide, Inches(9.2), Inches(5.0), "Best Current Stack", "Classical SVM", ACCENT_DARK)
    add_slide_number(slide, 1, total)


def add_agenda_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(
        slide,
        "Title + Agenda + Introduction",
        "Agenda and internship context",
        "The presentation is centered on Quantum Machine Learning research in a practical vision pipeline.",
    )
    add_two_column_bullets(
        slide,
        "Agenda",
        [
            "QML research objective and project overview",
            "Methods, technologies, and benchmark design",
            "Internship goals and how they were achieved",
            "Results of the classical versus quantum comparison",
            "Recommendation and future scope",
        ],
        "Introduction",
        [
            "Core internship objective: research how useful QML is in this application context",
            "Practical task: detect, classify, and extract text from packaging objects",
            "Research task: compare classical and hybrid quantum models fairly",
            "Outcome target: identify the best production path and the best innovation path",
        ],
    )
    add_slide_number(slide, 2, total)


def add_overview_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Project Presentation", "Project overview", "The computer-vision task was used as a practical testbed for QML research")
    add_two_column_bullets(
        slide,
        "Problem",
        [
            "Packaging images are noisy because of glare, clutter, and small printed text",
            "The system must detect the object, classify it correctly, and extract readable text",
            "In the internship context, this becomes a realistic environment to test QML against classical baselines",
        ],
        "Solution",
        [
            "Full pipeline with detection, ROI classification, OCR, and benchmark-driven recommendation",
            "Supports controlled comparison of classical and quantum-aware classifiers on the same data",
            "Turns a packaging-recognition system into a measurable QML research platform",
        ],
    )
    add_slide_number(slide, 3, total)


def add_architecture_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Project Presentation", "Research architecture", "The vision pipeline is the experimental platform and QML is evaluated at the classifier stage")

    labels = [
        ("Input Image", ACCENT),
        ("Preprocessing", AMBER),
        ("Detection", ACCENT),
        ("ROI Extraction", AMBER),
        ("Classification", ACCENT),
        ("OCR", AMBER),
        ("Final Output", ACCENT_DARK),
    ]
    xs = [0.8, 2.45, 4.1, 5.75, 7.4, 9.05, 10.7]
    for idx, ((label, color), x) in enumerate(zip(labels, xs)):
        box = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(x), Inches(3.0), Inches(1.4), Inches(1.0))
        box.fill.solid()
        box.fill.fore_color.rgb = WHITE
        box.line.color.rgb = color
        tf = box.text_frame
        tf.clear()
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        r.font.name = "Arial"
        r.font.bold = True
        r.font.size = Pt(13)
        r.font.color.rgb = INK
        if idx < len(labels) - 1:
            connector = slide.shapes.add_connector(
                MSO_CONNECTOR.STRAIGHT,
                Inches(x + 1.4),
                Inches(3.5),
                Inches(x + 1.65),
                Inches(3.5),
            )
            connector.line.color.rgb = MUTED
            connector.line.width = Pt(2)

    add_bullet_panel(
        slide,
        Inches(1.0),
        Inches(4.8),
        Inches(11.4),
        Inches(1.45),
        [
            "OpenCV handles denoising, contrast enhancement, and OCR-friendly preprocessing.",
            "YOLO detects the object, then ROI classification compares classical and QML models on the same ROI features.",
            "OCR uses Tesseract and TrOCR, and the final output helps evaluate both practical value and research outcomes.",
        ],
        font_size=14,
    )
    add_slide_number(slide, 4, total)


def add_ui_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Project Presentation", "Experimental workflow", "How the system supports QML experiments, benchmarking, and demonstration")
    add_two_column_bullets(
        slide,
        "UI Workflow",
        [
            "Train detector from the UI",
            "Train ROI classifier suite from the UI",
            "Generate benchmark report automatically",
            "Run inference and compare all saved model families",
        ],
        "Research Workflow",
        [
            "ROI upload mode for controlled classifier experiments",
            "Full pipeline mode for practical end-to-end evaluation",
            "Single-model, selected-model, or all-model comparison",
            "Clean output image plus charts and tables for evaluation review",
        ],
    )
    add_slide_number(slide, 5, total)


def add_dataset_slide(prs: Presentation, benchmark: dict, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Project Presentation", "Experimental setup and dataset design", "Separate datasets were used so the QML comparison remains controlled and meaningful")
    add_two_column_bullets(
        slide,
        "Detection Dataset",
        [
            "YOLO-style full-scene dataset with images/train, images/val, labels/train, labels/val",
            "Bounding-box annotations are stored in YOLO text format",
            "Used to create realistic scene-level inputs for the research pipeline",
        ],
        "ROI Classifier Dataset",
        [
            "Class-organized cropped object images",
            "Total ROI samples: 997",
            "Balanced training used augmentation to reduce class imbalance before model comparison",
        ],
    )
    add_metric_chip(slide, Inches(0.9), Inches(6.2), "ROI Samples", "997", ACCENT)
    add_metric_chip(slide, Inches(3.1), Inches(6.2), "Test Samples", "200", AMBER)
    add_metric_chip(slide, Inches(5.3), Inches(6.2), "Balanced Train", "1047", ACCENT_DARK)
    add_slide_number(slide, 6, total)


def add_methods_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Methods, Skills & Technology Used", "QML methods used in the pipeline", "The project objective was to study QML inside a realistic hybrid workflow")
    add_two_column_bullets(
        slide,
        "Vision Pipeline",
        [
            "Noise reduction, contrast enhancement, and binarization with OpenCV",
            "YOLO object detection for localization",
            "ROI extraction with controlled padding",
            "OCR ensemble using Tesseract and TrOCR",
        ],
        "QML Methods",
        [
            "Classical feature extraction from ROI images",
            "Angle encoding and amplitude encoding for quantum preparation",
            "Quantum-kernel SVM and variational quantum classifiers",
            "Direct comparison against strong classical baselines under the same evaluation logic",
        ],
    )
    add_slide_number(slide, 7, total)


def add_comparison_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Methods, Skills & Technology Used", "Classical vs hybrid quantum vs pure quantum", "This slide defines the comparison framework used in the internship")
    table = slide.shapes.add_table(4, 5, Inches(0.5), Inches(1.9), Inches(12.3), Inches(4.6)).table
    headers = ["Approach", "How It Works Here", "Advantages", "Disadvantages", "Best Use"]
    rows = [
        ["Classical", "OpenCV + ROI features + classical classifier", "Fast, strong baselines, easier deployment", "Lower research novelty", "Production baseline"],
        ["Hybrid Quantum", "Classical preprocessing + compressed features + quantum classifier", "Best way to study QML realistically today", "Higher complexity and slower training", "Main research track"],
        ["Pure Quantum", "Direct quantum image encoding and classification", "High novelty and future vision", "Not practical for this task today", "Future work"],
    ]
    for col, header in enumerate(headers):
        cell = table.cell(0, col)
        cell.text = header
    for row_idx, row in enumerate(rows, start=1):
        for col_idx, value in enumerate(row):
            table.cell(row_idx, col_idx).text = value
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Arial"
                    run.font.size = Pt(11)
                    run.font.color.rgb = INK
    add_slide_number(slide, 8, total)


def add_technology_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Methods, Skills & Technology Used", "Skills and technologies used", "Technologies used to build and evaluate the QML research pipeline")
    add_two_column_bullets(
        slide,
        "Technologies",
        [
            "Python, OpenCV, PyTorch, Ultralytics YOLO",
            "Qiskit and Qiskit Machine Learning",
            "Tesseract OCR and Microsoft TrOCR",
            "Flask, React, JSON-based benchmarking",
        ],
        "Skills Developed",
        [
            "End-to-end AI pipeline integration",
            "Dataset preparation and evaluation design",
            "QML benchmarking and interpretation",
            "Presentation-ready UI and technical documentation",
        ],
    )
    add_slide_number(slide, 9, total)


def add_execution_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Methods, Skills & Technology Used", "Internship execution and practical learning", "How the QML research question was converted into a usable project")
    add_bullet_panel(
        slide,
        Inches(0.8),
        Inches(2.0),
        Inches(11.8),
        Inches(4.7),
        [
            "Structured the detector dataset and the ROI classifier dataset separately.",
            "Trained detector, classical baselines, and multiple quantum-oriented classifier variants.",
            "Integrated benchmarking, visualization, and inference into a single UI workflow.",
            "Documented the project in report, presentation brief, and evaluation-facing formats.",
            "Learned how to translate QML results into an honest production-versus-research recommendation.",
        ],
        font_size=18,
    )
    add_slide_number(slide, 10, total)


def add_goals_slide_one(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Goals & Objective of Internship", "Achievement of internship objectives I", "Application, Knowledge, Exploration, Identification")
    add_two_column_bullets(
        slide,
        "Application + Knowledge",
        [
            "Applied computer-vision, OCR, and ML concepts in a complete working pipeline.",
            "Learned how quantum feature encoding and QML classifiers fit into a realistic hybrid system.",
            "Connected QML concepts to measurable implementation outcomes instead of only theoretical study.",
        ],
        "Exploration + Identification",
        [
            "Explored multiple encodings, kernels, and model families.",
            "Identified where QML is competitive and where classical methods remain stronger.",
            "Used held-out benchmarks rather than assumptions to interpret the comparison.",
        ],
    )
    add_slide_number(slide, 11, total)


def add_goals_slide_two(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Goals & Objective of Internship", "Achievement of internship objectives II", "Innovation, Engagement, Evaluation, Demonstration")
    add_two_column_bullets(
        slide,
        "Innovation + Engagement",
        [
            "Built a hybrid classical-quantum benchmark platform instead of a single-model demo.",
            "Worked across vision, OCR, QML, UI, benchmarking, and documentation.",
            "Created a project that supports both engineering use and research presentation.",
        ],
        "Evaluation + Demonstration",
        [
            "Compared all models on the same ROI dataset and benchmark logic.",
            "Generated visual charts, tables, and saved artifacts for repeatable QML evaluation.",
            "Prepared clean outputs and reporting material for mentors and panelists.",
        ],
    )
    add_slide_number(slide, 12, total)


def add_results_slide(prs: Presentation, detector_summary: dict, benchmark: dict, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Results", "Measured performance summary", "The key result is the classical versus QML comparison, supported by strong detector performance")
    metrics = detector_summary
    add_metric_chip(slide, Inches(0.8), Inches(2.0), "Precision", f"{metrics.get('precision', 0.0):.4f}", ACCENT)
    add_metric_chip(slide, Inches(3.0), Inches(2.0), "Recall", f"{metrics.get('recall', 0.0):.4f}", AMBER)
    add_metric_chip(slide, Inches(5.2), Inches(2.0), "mAP@50", f"{metrics.get('mAP50', 0.0):.4f}", ACCENT_DARK)
    add_metric_chip(slide, Inches(7.4), Inches(2.0), "mAP@50-95", f"{metrics.get('mAP50_95', 0.0):.4f}", AMBER)

    top_rows = benchmark.get("classifier_benchmarks", [])[:5]
    table = slide.shapes.add_table(len(top_rows) + 1, 4, Inches(0.8), Inches(3.2), Inches(11.7), Inches(3.0)).table
    headers = ["Model", "Family", "Accuracy", "Train Time (s)"]
    for i, header in enumerate(headers):
        table.cell(0, i).text = header
    for row_idx, row in enumerate(top_rows, start=1):
        values = [
            str(row.get("name", "")),
            str(row.get("model_family", "")),
            f"{float(row.get('accuracy', 0.0)) * 100:.2f}%",
            f"{float(row.get('train_time_seconds', 0.0)):.2f}",
        ]
        for col_idx, value in enumerate(values):
            table.cell(row_idx, col_idx).text = value
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Arial"
                    run.font.size = Pt(11)
                    run.font.color.rgb = INK
    add_slide_number(slide, 13, total)


def add_benchmark_slide(prs: Presentation, benchmark: dict, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Results", "Research conclusion and recommendation", "What this internship shows about QML in this application context")

    chart_data = CategoryChartData()
    top_models = benchmark.get("classifier_benchmarks", [])[:6]
    chart_data.categories = [row.get("name", "")[:24] for row in top_models]
    chart_data.add_series("Accuracy", [float(row.get("accuracy", 0.0)) * 100 for row in top_models])
    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(0.7),
        Inches(1.9),
        Inches(6.7),
        Inches(4.2),
        chart_data,
    ).chart
    chart.has_legend = False
    chart.value_axis.maximum_scale = 100
    chart.value_axis.minimum_scale = 0
    chart.category_axis.tick_labels.font.size = Pt(10)
    chart.value_axis.tick_labels.font.size = Pt(10)
    chart.chart_title.has_text_frame = True
    chart.chart_title.text_frame.text = "Top Classifier Accuracy (%)"

    recommendation = benchmark.get("recommended_pipeline", {})
    add_bullet_panel(
        slide,
        Inches(7.8),
        Inches(2.0),
        Inches(4.8),
        Inches(4.0),
        [
            f"Recommended stack today: {recommendation.get('detector_backend', 'pending')} + {recommendation.get('classifier_name', 'pending')} + {recommendation.get('ocr_backend', 'pending')}",
            "Classical models currently provide the strongest production baseline on this dataset.",
            "The best QML result is the amplitude QSVM, which is competitive in accuracy but slower to train.",
            "Conclusion: QML is promising and worth researching, but it should currently be positioned as an innovation track rather than the default deployment path.",
        ],
        font_size=15,
    )
    add_slide_number(slide, 14, total)


def add_future_scope_slide(prs: Presentation, total: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(slide, "Future Scope", "Next steps", "How this project can continue as a stronger QML research platform")
    add_bullet_panel(
        slide,
        Inches(0.9),
        Inches(2.0),
        Inches(11.5),
        Inches(4.6),
        [
            "Add true end-to-end validation on full-scene test images instead of relying only on a composite proxy score.",
            "Improve OCR robustness for small, reflective, and partially visible labels.",
            "Test additional quantum kernels, encodings, and compression strategies.",
            "Continue QML experiments only where they provide measurable value over strong classical baselines.",
            "Use the platform for deeper research rather than assuming quantum superiority in advance.",
        ],
        font_size=18,
    )
    closing = slide.shapes.add_textbox(Inches(0.9), Inches(6.8), Inches(10.5), Inches(0.35))
    p = closing.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = "Final takeaway: this internship shows how QML can be studied responsibly in a real AI pipeline, with classical as the current production winner and hybrid QML as the key research direction."
    r.font.name = "Arial"
    r.font.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = ACCENT_DARK
    add_slide_number(slide, 15, total)


def build_presentation() -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    benchmark = load_json(BENCHMARK_PATH)
    detector_summary = load_json(DETECTOR_SUMMARY_PATH)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    total_slides = 15

    add_title_slide(prs, total_slides)
    add_agenda_slide(prs, total_slides)
    add_overview_slide(prs, total_slides)
    add_architecture_slide(prs, total_slides)
    add_ui_slide(prs, total_slides)
    add_dataset_slide(prs, benchmark, total_slides)
    add_methods_slide(prs, total_slides)
    add_comparison_slide(prs, total_slides)
    add_technology_slide(prs, total_slides)
    add_execution_slide(prs, total_slides)
    add_goals_slide_one(prs, total_slides)
    add_goals_slide_two(prs, total_slides)
    add_results_slide(prs, detector_summary, benchmark, total_slides)
    add_benchmark_slide(prs, benchmark, total_slides)
    add_future_scope_slide(prs, total_slides)

    try:
        prs.save(OUTPUT_PPTX)
        return OUTPUT_PPTX
    except PermissionError:
        prs.save(FALLBACK_OUTPUT_PPTX)
        return FALLBACK_OUTPUT_PPTX


if __name__ == "__main__":
    path = build_presentation()
    print(f"Saved PowerPoint to: {path}")
