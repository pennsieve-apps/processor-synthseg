# Third-party software and models

This app is Apache-2.0 (see `LICENSE`). The image it builds contains the following
third-party components; their licences apply to the image, and the FreeSurfer
Software License Agreement makes the SynthSeg weights (and FreeSurfer's copy of the
script) **research-use only** — commercial use needs a licence from MGH.

| Component | What | Licence | Source |
|---|---|---|---|
| SynthSeg 2.0 — code | `vendor/synthseg/mri_synthseg`: FreeSurfer 8.2.0's single-file port of SynthSeg's prediction code (`scripts/commands/SynthSeg_predict.py` + `SynthSeg/predict_synthseg.py` + the needed `ext/lab2im` / `ext/neuron` utilities), with its label tables `vendor/synthseg/models/*.npy`. Taken verbatim from `freesurfer/freesurfer` tag `v8.2.0`, folder `mri_synthseg/` (sha256 of the script `f3c182cd…279b`). | Original SynthSeg code: Apache-2.0 (© Benjamin Billot). FreeSurfer's port: FreeSurfer Software License Agreement v1.0 (`vendor/synthseg/LICENSE.txt`), redistribution allowed with the agreement, research purposes only. | https://github.com/BBillot/SynthSeg, https://github.com/freesurfer/freesurfer/tree/v8.2.0/mri_synthseg |
| SynthSeg 2.0 — trained weights | `synthseg_2.0.h5`, `synthseg_robust_2.0.h5`, `synthseg_parc_2.0.h5`, `synthseg_qc_2.0.h5`, downloaded at build time from FreeSurfer's public git-annex object store (`surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/repo/annex.git/annex/objects/…`, the files FreeSurfer ≥ 7.3 installs under `$FREESURFER_HOME/models/`), each verified against its SHA-256 (listed in the `Dockerfile`). | FreeSurfer Software License Agreement v1.0 (research use only; redistribution with the agreement). The SynthSeg authors' own distribution of the same files (UCL SharePoint, now offline) was Apache-2.0. | https://surfer.nmr.mgh.harvard.edu/fswiki/SynthSeg |
| TensorFlow 2.13.1 (CPU) | Inference engine (bundled Keras 2.13). | Apache-2.0 | https://github.com/tensorflow/tensorflow |
| surfa 0.6.3 | Imported by `mri_synthseg` (volume I/O helpers; only `sf.system` is reached in this app). | MIT-style FreeSurfer licence (© MGH) | https://github.com/freesurfer/surfa |
| NumPy 1.24.3, SciPy 1.10.1, h5py 3.9.0, nibabel 5.2.1 | Array maths, image I/O. | BSD-3 / MIT | PyPI |
| python:3.11-slim-bookworm | Base image (Debian 12 + CPython 3.11). | PSF (Python); Debian packages under their own free licences | https://hub.docker.com/_/python |

## Citations

Whole-brain segmentation (always):

> Billot B, Greve DN, Puonti O, Thielscher A, Van Leemput K, Fischl B, Dalca AV, Iglesias JE.
> **SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining.**
> Medical Image Analysis 86:102789 (2023). https://doi.org/10.1016/j.media.2023.102789

Robust mode (`ROBUST=true`), cortical parcellation (`PARC=true`) and the QC scores (always written):

> Billot B, Magdamo C, Cheng Y, Arnold SE, Das S, Iglesias JE.
> **Robust machine learning segmentation for large-scale analysis of heterogeneous clinical brain MRI datasets.**
> PNAS 120(9):e2216399120 (2023). https://doi.org/10.1073/pnas.2216399120

FreeSurfer (the distribution the script and weights are taken from):

> Fischl B. **FreeSurfer.** NeuroImage 62(2):774-781 (2012). https://doi.org/10.1016/j.neuroimage.2012.01.021
