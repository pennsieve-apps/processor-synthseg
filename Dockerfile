# SynthSeg 2.0 on the CPU, packaged for Pennsieve (amd64 Fargate; no network at run time).
#
# Code: FreeSurfer 8.2.0's mri_synthseg (a single-file port of github.com/BBillot/SynthSeg,
# vendored in vendor/synthseg/ with its licence) on TensorFlow 2.13 CPU.
# Weights: the four SynthSeg 2.0 models are fetched at build time from FreeSurfer's public
# git-annex object store (the same files FreeSurfer installs under $FREESURFER_HOME/models),
# each checked against its SHA-256. Nothing large lives in the repo.
FROM --platform=linux/amd64 python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TF_CPP_MIN_LOG_LEVEL=3 \
    # oneDNN kernels are faster but need several times the memory on a whole-head 1 mm
    # volume; the plain Eigen kernels fit comfortably in the task's 16 GB.
    TF_ENABLE_ONEDNN_OPTS=0 \
    FREESURFER_HOME=/opt/synthseg \
    PYTHONPATH=/processor

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# The script and its small label tables (from freesurfer/freesurfer tag v8.2.0, mri_synthseg/).
COPY vendor/synthseg/ /opt/synthseg/

# The trained networks (~370 MB together), pinned by content hash.
ARG ANNEX=https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/repo/annex.git/annex/objects
RUN set -eu; cd /opt/synthseg/models; \
    fetch() { \
      key="SHA256E-s$2--$3.0.h5"; \
      curl -fsSL --retry 5 --retry-delay 15 -o "$1" "$ANNEX/$4/$key/$key"; \
      echo "$3  $1" | sha256sum -c -; \
    }; \
    fetch synthseg_2.0.h5        53079152  f190bfd742f450ef3ca2c9df9ed4d2e0232b3a74471da5e51b7770bacdf80c3e bee/241; \
    fetch synthseg_robust_2.0.h5 214606800 7bc30bf5c3d204f20c4a6cb5a283aedbcab6af1de927cda783f59b67d19cb01c 187/db4; \
    fetch synthseg_parc_2.0.h5   53090840  83bb1de76fb6f173c6dacacd433f81209fc6abb1dbc179a930ec06ecabbeb684 c04/403; \
    fetch synthseg_qc_2.0.h5     49878004  fb92e37daa0842bdd8a03bc06a3b36b0d38810e31c714659cedd09119c0abfb7 3ac/fe4; \
    ls -l /opt/synthseg/models

COPY VERSION /processor/VERSION
COPY processor/ /processor/processor/

# The platform runs the task as uid 1000; /tmp is the scratch space.
RUN useradd --uid 1000 --create-home processor
USER 1000
WORKDIR /processor

ENTRYPOINT ["python3", "-m", "processor.entry"]
