from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a comparison suite of classical and quantum ROI classifiers.")
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--artifacts-dir", default="artifacts")
    parser.add_argument("--profile", choices=["core", "quantum", "extended", "all_models", "presentation"], default="core")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--reuse-existing", default="true")
    return parser.parse_args()


def build_suite(profile: str) -> list[dict[str, str]]:
    core_suite = [
        {"model_type": "svc_rbf", "encoding": "angle", "n_qubits": "6", "slug": "classical_svm_rbf", "feature_map_reps": "2", "ansatz_reps": "2", "maxiter": "50", "preselect_dim": "256", "classical_feature_dim": "128"},
        {"model_type": "random_forest", "encoding": "angle", "n_qubits": "6", "slug": "random_forest", "feature_map_reps": "2", "ansatz_reps": "2", "maxiter": "50", "preselect_dim": "256", "classical_feature_dim": "128"},
        {"model_type": "logreg", "encoding": "angle", "n_qubits": "6", "slug": "logistic_regression", "feature_map_reps": "2", "ansatz_reps": "2", "maxiter": "50", "preselect_dim": "256", "classical_feature_dim": "128"},
        {"model_type": "mlp", "encoding": "angle", "n_qubits": "6", "slug": "mlp_classifier", "feature_map_reps": "2", "ansatz_reps": "2", "maxiter": "50", "preselect_dim": "256", "classical_feature_dim": "128"},
        {"model_type": "qsvc", "encoding": "angle", "n_qubits": "6", "slug": "qsvc_angle", "feature_map_reps": "2", "ansatz_reps": "2", "maxiter": "50", "preselect_dim": "256", "classical_feature_dim": "128"},
    ]
    quantum_suite = [
        {"model_type": "qsvc_zz_full", "encoding": "angle", "n_qubits": "6", "slug": "qsvc_zz_full_angle", "feature_map_reps": "2", "ansatz_reps": "2", "maxiter": "50", "preselect_dim": "256", "classical_feature_dim": "128"},
        {"model_type": "qsvc_pauli", "encoding": "angle", "n_qubits": "4", "slug": "qsvc_pauli_angle", "feature_map_reps": "1", "ansatz_reps": "2", "maxiter": "50", "preselect_dim": "64", "classical_feature_dim": "128"},
        {"model_type": "qsvc", "encoding": "amplitude", "n_qubits": "6", "slug": "qsvc_amplitude", "feature_map_reps": "2", "ansatz_reps": "2", "maxiter": "50", "preselect_dim": "256", "classical_feature_dim": "128"},
        {"model_type": "vqc_real", "encoding": "angle", "n_qubits": "4", "slug": "vqc_real_angle", "feature_map_reps": "1", "ansatz_reps": "1", "maxiter": "20", "preselect_dim": "32", "classical_feature_dim": "64"},
        {"model_type": "vqc_efficient", "encoding": "angle", "n_qubits": "4", "slug": "vqc_efficient_angle", "feature_map_reps": "1", "ansatz_reps": "1", "maxiter": "20", "preselect_dim": "32", "classical_feature_dim": "64"},
    ]
    if profile == "core":
        return core_suite
    if profile == "quantum":
        return quantum_suite
    if profile == "presentation":
        presentation_slugs = {"qsvc_zz_full_angle", "qsvc_pauli_angle", "vqc_real_angle"}
        return core_suite + [item for item in quantum_suite if item["slug"] in presentation_slugs]
    return core_suite + quantum_suite


def main() -> None:
    args = parse_args()
    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, str | int]] = []
    suite_entries = build_suite(args.profile)
    total_entries = len(suite_entries)
    print(f"SUITE_TOTAL|{total_entries}|{args.profile}")
    overall_return_code = 0
    for index, item in enumerate(suite_entries, start=1):
        artifact_path = artifacts_dir / f"{item['slug']}.pkl"
        summary_path = artifacts_dir / f"{item['slug']}.summary.json"
        command = [
            sys.executable,
            "train_hybrid.py",
            "--dataset-dir",
            args.dataset_dir,
            "--artifact-path",
            str(artifact_path),
            "--summary-path",
            str(summary_path),
            "--model-type",
            item["model_type"],
            "--encoding",
            item["encoding"],
            "--n-qubits",
            item["n_qubits"],
            "--feature-map-reps",
            item["feature_map_reps"],
            "--ansatz-reps",
            item["ansatz_reps"],
            "--maxiter",
            item["maxiter"],
            "--preselect-dim",
            item["preselect_dim"],
            "--classical-feature-dim",
            item["classical_feature_dim"],
            "--test-size",
            str(args.test_size),
            "--device",
            args.device,
            "--reuse-existing",
            args.reuse_existing,
        ]
        print(f"SUITE_PROGRESS|{index}|{total_entries}|{item['slug']}|start")
        print(f"Training suite entry: {item['slug']}")
        print("Command:", " ".join(command))
        completed = subprocess.run(command, check=False)
        print(
            f"SUITE_PROGRESS|{index}|{total_entries}|{item['slug']}|"
            f"{'done' if completed.returncode == 0 else 'failed'}"
        )
        results.append(
            {
                "index": index,
                "slug": item["slug"],
                "model_type": item["model_type"],
                "encoding": item["encoding"],
                "n_qubits": item["n_qubits"],
                "feature_map_reps": item["feature_map_reps"],
                "ansatz_reps": item["ansatz_reps"],
                "maxiter": item["maxiter"],
                "preselect_dim": item["preselect_dim"],
                "classical_feature_dim": item["classical_feature_dim"],
                "return_code": int(completed.returncode),
                "status": "completed" if completed.returncode == 0 else "failed",
                "artifact_path": str(artifact_path),
                "summary_path": str(summary_path),
            }
        )
        if completed.returncode != 0:
            overall_return_code = completed.returncode

    failed_results = [entry for entry in results if int(entry["return_code"]) != 0]
    suite_summary = {
        "generated_at": datetime.now().isoformat(),
        "profile": args.profile,
        "dataset_dir": str(Path(args.dataset_dir).resolve()),
        "artifacts_dir": str(artifacts_dir.resolve()),
        "reuse_existing": args.reuse_existing,
        "num_models": total_entries,
        "num_failed": len(failed_results),
        "status": "failed" if failed_results else "completed",
        "results": results,
    }
    suite_summary_path = artifacts_dir / f"model_suite_{args.profile}.json"
    suite_summary_path.write_text(json.dumps(suite_summary, indent=2), encoding="utf-8")
    print(f"Saved model suite summary to: {suite_summary_path}")
    if failed_results:
        failed_slugs = ", ".join(str(entry["slug"]) for entry in failed_results)
        print(f"Suite completed with failures: {failed_slugs}")
    raise SystemExit(overall_return_code)


if __name__ == "__main__":
    main()
