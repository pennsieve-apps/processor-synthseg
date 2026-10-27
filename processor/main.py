"""
processor-synthseg: whole-brain segmentation of T1w scans with SynthSeg 2.0, run on the CPU
through FreeSurfer's mri_synthseg script (vendored in /opt/synthseg, weights baked into the
image).

Input  image:   <sub>[_<entities>]_T1w.nii.gz, one per subject (INPUT_DIR/image/ or anywhere
                under INPUT_DIR by suffix).
Outputs:        labels/<sub>_dseg.nii.gz         FreeSurfer-labelled segmentation, 1 mm iso
                labels/provenance.json
                volumes/<sub>_volumes.csv        SynthSeg --vol table, header + one row (mm3)
                volumes/volumes.csv              the same for every subject, one row each
                qc/<sub>_qc.csv                  SynthSeg --qc table, header + one row
Parameters:     ROBUST (bool), PARC (bool), THREADS (int); --cpu is always passed.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from processor.bids_names import by_subject, derived_name, find_input_files, output_dir_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("processor-synthseg")

APP = "processor-synthseg"
TOOL = "SynthSeg"
TOOL_VERSION = "2.0 (FreeSurfer 8.2.0 mri_synthseg, TensorFlow 2.13.1 CPU)"
INPUT_NAME = "image"
INPUT_SUFFIXES = ("T1w",)
OUTPUTS = ["labels", "volumes", "qc"]
SYNTHSEG_HOME = Path(os.environ.get("FREESURFER_HOME", "/opt/synthseg"))
SYNTHSEG_SCRIPT = SYNTHSEG_HOME / "mri_synthseg"


def app_version() -> str:
    for candidate in (Path(__file__).resolve().parent.parent / "VERSION", Path("/processor/VERSION")):
        if candidate.is_file():
            return candidate.read_text().strip()
    return "unknown"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "y", "on")


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return max(1, int(float(value)))
    except ValueError:
        log.warning("%s=%r is not an integer, using %d", name, value, default)
        return default


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[list[str]]:
    with open(path, newline="") as fh:
        return [row for row in csv.reader(fh) if row]


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", newline="") as fh:
        csv.writer(fh).writerows(rows)


def relabel_subject(src: Path, dst: Path, subject: str) -> list[str]:
    """Copy a one-subject SynthSeg CSV (header + one row), replacing the subject cell (the
    input file's base name) with the BIDS subject label. Returns the header."""
    rows = read_csv(src)
    if len(rows) < 2:
        raise RuntimeError(f"{src.name} has no data row")
    header, row = rows[0], rows[1]
    row[0] = subject
    write_csv(dst, [header, row])
    return header


def run_subject(subject: str, image: Path, out: dict[str, Path], params: dict, work: Path) -> dict:
    """Segment one subject. Returns the provenance entry (raises on failure)."""
    seg_path = out["labels"] / derived_name(image, "dseg")
    vol_tmp = work / f"{subject}_volumes.csv"
    qc_tmp = work / f"{subject}_qc.csv"
    cmd = [
        sys.executable, str(SYNTHSEG_SCRIPT),
        "--i", str(image),
        "--o", str(seg_path),
        "--vol", str(vol_tmp),
        "--qc", str(qc_tmp),
        "--cpu",
        "--threads", str(params["THREADS"]),
        # Plain NIfTI through nibabel; no embedded FreeSurfer colour table.
        "--noaddctab",
    ]
    if params["ROBUST"]:
        cmd.append("--robust")
    if params["PARC"]:
        cmd.append("--parc")

    log.info("[%s] %s", subject, " ".join(cmd))
    t0 = time.monotonic()
    subprocess.run(cmd, check=True)
    for produced in (seg_path, vol_tmp, qc_tmp):
        if not produced.is_file() or produced.stat().st_size == 0:
            # mri_synthseg catches per-image exceptions and exits 0 after printing them.
            raise RuntimeError(f"SynthSeg did not write {produced.name}")

    vol_path = out["volumes"] / f"{subject}_volumes.csv"
    qc_path = out["qc"] / f"{subject}_qc.csv"
    relabel_subject(vol_tmp, vol_path, subject)
    relabel_subject(qc_tmp, qc_path, subject)
    seconds = round(time.monotonic() - t0, 1)
    log.info("[%s] done in %.0f s -> %s", subject, seconds, seg_path.name)
    return {
        "subject": subject,
        "inputs": [str(image.relative_to(params["_input_dir"]))],
        "outputs": [
            str(p.relative_to(params["_output_dir"])) for p in (seg_path, vol_path, qc_path)
        ],
        "command": cmd,
        "seconds": seconds,
    }


def write_cohort_table(volumes_dir: Path, subjects: list[str]) -> Path | None:
    """volumes/volumes.csv: every subject's row under one header."""
    rows: list[list[str]] = []
    header: list[str] | None = None
    for subject in subjects:
        per_subject = read_csv(volumes_dir / f"{subject}_volumes.csv")
        if header is None:
            header = per_subject[0]
            rows.append(header)
        elif per_subject[0] != header:
            log.warning("[%s] volume columns differ from the first subject's; row kept as is", subject)
        rows.extend(per_subject[1:])
    if header is None:
        return None
    path = volumes_dir / "volumes.csv"
    write_csv(path, rows)
    return path


def main() -> int:
    input_dir = os.environ.get("INPUT_DIR")
    output_dir = os.environ.get("OUTPUT_DIR")
    if not input_dir or not output_dir:
        log.error("INPUT_DIR and OUTPUT_DIR must be set")
        return 2
    if not os.path.isdir(input_dir):
        log.error("INPUT_DIR %s is not a folder", input_dir)
        return 2
    if not SYNTHSEG_SCRIPT.is_file():
        log.error("mri_synthseg not found at %s (FREESURFER_HOME=%s)", SYNTHSEG_SCRIPT, SYNTHSEG_HOME)
        return 2

    started = now_iso()
    params = {
        "ROBUST": env_bool("ROBUST", False),
        "PARC": env_bool("PARC", False),
        "THREADS": env_int("THREADS", 4),
    }
    out = {name: output_dir_for(output_dir, OUTPUTS, name) for name in OUTPUTS}
    log.info("%s %s: %s %s; parameters %s", APP, app_version(), TOOL, TOOL_VERSION, params)

    images = by_subject(find_input_files(input_dir, INPUT_NAME, INPUT_SUFFIXES))
    if not images:
        found = sorted(str(p.relative_to(input_dir)) for p in Path(input_dir).rglob("*") if p.is_file())
        log.error(
            "no T1w input found: expected <subject>[_<entities>]_T1w.nii[.gz] in %s/%s/ or under %s; found: %s",
            input_dir, INPUT_NAME, input_dir, found or "nothing",
        )
        return 1
    log.info("%d subject(s): %s", len(images), ", ".join(images))

    run_params = dict(params, _input_dir=Path(input_dir), _output_dir=Path(output_dir))
    entries: list[dict] = []
    done: list[str] = []
    failed: list[str] = []
    work = Path(tempfile.mkdtemp(prefix="synthseg-", dir="/tmp"))
    try:
        for subject, image in images.items():
            try:
                entries.append(run_subject(subject, image, out, run_params, work))
                done.append(subject)
            except Exception as exc:  # noqa: BLE001 - per-subject isolation
                log.error("[%s] FAILED: %s", subject, exc)
                failed.append(subject)
                entries.append({"subject": subject, "inputs": [str(image.relative_to(input_dir))],
                                "outputs": [], "error": str(exc)})
    finally:
        shutil.rmtree(work, ignore_errors=True)

    cohort = write_cohort_table(out["volumes"], done)
    if cohort:
        log.info("cohort table %s (%d subjects)", cohort.relative_to(output_dir), len(done))

    provenance = {
        "app": APP,
        "appVersion": app_version(),
        "tool": TOOL,
        "toolVersion": TOOL_VERSION,
        "startedAt": started,
        "finishedAt": now_iso(),
        "parameters": params,
        "subjects": entries,
    }
    with open(out["labels"] / "provenance.json", "w") as fh:
        json.dump(provenance, fh, indent=2)

    log.info("%d succeeded, %d failed", len(done), len(failed))
    if failed and not done:
        log.error("every subject failed: %s", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
