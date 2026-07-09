# Releasing NetMapper

This repository is set up so stable user deployments should come from Git tags
such as `v1.0.2`, while `main` remains available for development work.

## Single source of truth

Release version metadata now comes from Git tags:

- `vX.Y.Z` tags

That drives:

- the NetBox plugin version shown by `NetmapperConfig`
- the Python package version used by builds

## Recommended release flow

1. Update `docs/upgrade-notes.md` for the release.
2. Run validation locally:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

3. Run your normal tests and CI checks.
4. Commit the release changes.
5. Create an annotated tag:

```bash
git tag -a vX.Y.Z -m "NetMapper vX.Y.Z"
```

6. Push the branch and tag:

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

For non-tagged builds, `setuptools-scm` generates a development version from
the Git history, so test branches stay distinguishable from released builds.
