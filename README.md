# processor-synthseg

Whole-brain segmentation of T1-weighted MRI with **SynthSeg 2.0** (Billot et al. 2023), step 5 of
the Clinical Brain MRI Volumetrics workflow. SynthSeg is a contrast- and resolution-agnostic
U-Net: it segments any brain scan without retraining and reports results at 1 mm isotropic.
The app runs it on the CPU through FreeSurfer 8.2.0's `mri_synthseg` script, with the trained
networks baked into the image, so a run needs no network access.

Per subject it writes a FreeSurfer-labelled segmentation, SynthSeg's volume table and its
automated QC scores; across the run it also writes one cohort volume table
(`volumes/volumes.csv`) for the report step.

## Ports

| Port | Kind | Files | Notes |
|---|---|---|---|
| `image` | input (root placement) | `<sub>[_<entities>]_T1w.nii[.gz]`, one per subject | Looked for in `INPUT_DIR/image/` first, else anywhere under `INPUT_DIR` by the `T1w` suffix. The subject label is everything before the first `_`. Any T1w works (raw, N4-corrected, skull-stripped or not). |
| `labels` | output | `labels/<sub>_dseg.nii.gz`, `labels/provenance.json` | int32 label map, 1 mm isotropic, FreeSurfer label values (see below). |
| `volumes` | output | `volumes/<sub>_volumes.csv`, `volumes/volumes.csv` | SynthSeg's `--vol` table: header row + one row per subject, volumes in mm³. The per-subject file has one row; `volumes.csv` has one row per subject of the run. |
| `qc` | output | `qc/<sub>_qc.csv` | SynthSeg's `--qc` table: predicted quality score in [0, 1] per structure group (a predicted Dice; values below ~0.65 flag a region the authors consider failed). |

The `subject` column of both CSVs holds the subject label (`sub-01`), not the file name.

`volumes/<sub>_volumes.csv` columns, in order: `subject`, `total intracranial`, then the 32
structures below in label order (`left cerebral white matter`, `left cerebral cortex`,
`left lateral ventricle`, …, `right ventral DC`). With `PARC=true` the 68 Desikan-Killiany
cortical regions follow (`ctx-lh-bankssts` … `ctx-rh-insula`).

## Parameters

| Parameter | Type | Default | Passed as | |
|---|---|---|---|---|
| `ROBUST` | boolean | `false` | `--robust` | SynthSeg-robust: slower, for clinical / low-quality scans (thick slices, low SNR, poor contrast). Implies SynthSeg's fast mode (no test-time flipping / topology clean-up). |
| `PARC` | boolean | `false` | `--parc` | Also parcellate the cortex (labels 1000–1035 / 2000–2035, extra volume columns). |
| `THREADS` | integer | `4` | `--threads` | CPU threads for TensorFlow. |

`--cpu` and `--noaddctab` (plain NIfTI, no embedded colour table) are always passed.

## Runtime

`computeTypes: [standard]`, 4 vCPU / 16 GiB, 1 h timeout. On the platform (amd64, no
emulation) SynthSeg 2.0 takes roughly 1–3 min per 1 mm whole-head scan on 4 threads, with a
peak of a few GB of RAM; `ROBUST=true` is slower. The image is ~2.3 GB (TensorFlow 2.13 CPU
+ 370 MB of weights). Each subject runs in its own `mri_synthseg` process; a subject that
fails is logged and skipped, and the run only fails when every subject failed (or no T1w
was found).

## Label values

The label map uses FreeSurfer's `aseg` label values (FreeSurferColorLUT.txt):

| Label | Structure | Label | Structure |
|---|---|---|---|
| 0 | background | 24 | CSF |
| 2 / 41 | left / right cerebral white matter | 26 / 58 | left / right accumbens area |
| 3 / 42 | left / right cerebral cortex | 28 / 60 | left / right ventral DC |
| 4 / 43 | left / right lateral ventricle | 14 | 3rd ventricle |
| 5 / 44 | left / right inferior lateral ventricle | 15 | 4th ventricle |
| 7 / 46 | left / right cerebellum white matter | 16 | brain-stem |
| 8 / 47 | left / right cerebellum cortex | 17 / 53 | left / right hippocampus |
| 10 / 49 | left / right thalamus | 18 / 54 | left / right amygdala |
| 11 / 50 | left / right caudate | 12 / 51 | left / right putamen |
| 13 / 52 | left / right pallidum | | |

With `PARC=true` the cortex labels (3, 42) are replaced by Desikan-Killiany regions
`1000 + i` (left) and `2000 + i` (right), `i` = 1…35 as in the FreeSurfer LUT
(`ctx-lh-bankssts` = 1001, …). The map is always at 1 mm isotropic in the input's RAS frame
(SynthSeg resamples internally), so it overlays on the input in any viewer that honours the
affine; it is not voxel-aligned with a non-1 mm input.

## Running it locally

```sh
./sample-input/fetch-sample.sh   # ds000117 sub-01 (CC0, OpenNeuro) -> data/input/
make run                         # builds the image (amd64) and runs it over data/input/
find data/output -type f
```

Or by hand:

```sh
docker build --platform linux/amd64 -t processor-synthseg .
docker run --rm --platform linux/amd64 \
  -e INPUT_DIR=/data/input -e OUTPUT_DIR=/data/output -e THREADS=4 \
  -v "$PWD/data/input:/data/input:ro" -v "$PWD/data/output:/data/output" \
  processor-synthseg
```

The image is amd64 only (TensorFlow wheels); on an Apple-silicon Mac it runs under
emulation, 10–20× slower than native, and needs a Docker VM of 8 GB or more.

`make test` runs `processor.main` with the local Python instead (install `requirements.txt`
and point `FREESURFER_HOME` at a folder laid out like `/opt/synthseg` in the image: the
vendored script, `models/*.npy` and the four `.h5` files).

## How the weights get into the image

The SynthSeg authors' download link (UCL SharePoint) is offline, and the repo only holds
`synthseg_1.0.h5`. FreeSurfer distributes the same 2.0 models as part of every release, and
its public git-annex object store serves them individually by content hash. The
`Dockerfile` fetches the four files from there at build time and checks each SHA-256, so
nothing large is committed and a build is reproducible. See `THIRD_PARTY.md` for licences
(the weights are research-use only under the FreeSurfer licence).

## Citation

- Billot B, Greve DN, Puonti O, Thielscher A, Van Leemput K, Fischl B, Dalca AV, Iglesias JE.
  SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining.
  *Medical Image Analysis* 86:102789 (2023). https://doi.org/10.1016/j.media.2023.102789
- Billot B, Magdamo C, Cheng Y, Arnold SE, Das S, Iglesias JE. Robust machine learning
  segmentation for large-scale analysis of heterogeneous clinical brain MRI datasets.
  *PNAS* 120(9):e2216399120 (2023). https://doi.org/10.1073/pnas.2216399120 (robust mode,
  parcellation, QC)
