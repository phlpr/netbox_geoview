# Releasing netbox-geoview

This repository is configured for Trusted Publishing to PyPI and TestPyPI via GitHub Actions.

## One-time setup in PyPI / TestPyPI

You must create the project once in each index and register the matching Trusted Publisher.

### 1) Create the project namespace

- Ensure the package name `netbox-geoview` is available on:
  - PyPI: https://pypi.org/project/netbox-geoview/
  - TestPyPI: https://test.pypi.org/project/netbox-geoview/

If the name is not yet claimed, the first successful publish will create it.

### 2) Add Trusted Publisher for TestPyPI

In TestPyPI project settings, add a Trusted Publisher with:

- Owner: `phlpr`
- Repository name: `netbox_geoview`
- Workflow name: `publish-testpypi.yml`
- Environment name: `testpypi`

### 3) Add Trusted Publisher for PyPI

In PyPI project settings, add a Trusted Publisher with:

- Owner: `phlpr`
- Repository name: `netbox_geoview`
- Workflow name: `publish-pypi.yml`
- Environment name: `pypi`

## Release flows

## CI checks

- Workflow `Tests` runs on pushes to `main` and on pull requests.
- Current scope: lightweight unit tests that do not require a full NetBox test environment.

### Test release (manual)

- Run GitHub Actions workflow `Publish to TestPyPI` manually.

### Production release (tag-based)

1. Update version in `netbox_geoview/version.py`.
2. Commit and push changes to default branch.
3. Create and push a version tag in `vX.Y.Z` format.
4. Workflow `Publish to PyPI` will run automatically for `v*` tags.

Example:

```bash
git tag v0.2.0
git push origin v0.2.0
```
