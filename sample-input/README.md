# Sample input

No NIfTI files are committed. Fetch a CC0 T1w scan from OpenNeuro into `data/input/`
(gitignored) with:

```sh
./sample-input/fetch-sample.sh            # ds000117 sub-01, 1 mm MPRAGE, ~11 MB
./sample-input/fetch-sample.sh sub-02     # another subject of the same dataset
```

Then `make run`. The file name `sub-01_T1w.nii.gz` is what the app keys on: the subject
label is everything before the first `_`, the suffix must be `T1w`.
