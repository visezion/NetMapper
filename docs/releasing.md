# Releasing NetMapper

This repository is set up so stable user deployments should come from Git tags
such as `v1.0.2`, while `main` remains available for development work.

## Single source of truth

Release version metadata now lives in one place:

- `netmapper/version.py`

That file drives:

- the NetBox plugin version shown by `NetmapperConfig`
- the Python package version used by builds

## Recommended release flow

1. Update `netmapper/version.py`.
2. Update `docs/upgrade-notes.md` for the release.
3. Run validation locally:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

4. Run your normal tests and CI checks.
5. Commit the release changes.
6. Create an annotated tag:

```bash
git tag -a vX.Y.Z -m "NetMapper vX.Y.Z"
```

7. Push the branch and tag:

```bash
git push origin main
git push origin vX.Y.Z
```

## GitHub automation

The GitHub CD workflow now runs on `v*` tag pushes. It will:

- build the source and wheel artifacts
- validate the artifacts with `twine check`
- create a GitHub release
- publish to PyPI when `PYPI_PASSWORD` is configured

This avoids mutating source files inside CI and keeps the tagged commit as the
actual released code.
