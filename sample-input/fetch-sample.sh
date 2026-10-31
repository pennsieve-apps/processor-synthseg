#!/bin/sh
# Fetch one T1w scan of OpenNeuro ds000117 (CC0) into data/input/.
set -eu
sub=${1:-sub-01}
dest="$(dirname "$0")/../data/input"
mkdir -p "$dest"
aws s3 cp --no-sign-request "s3://openneuro.org/ds000117/$sub/ses-mri/anat/${sub}_ses-mri_T1w.nii.gz" "$dest/${sub}_T1w.nii.gz"
ls -l "$dest"
