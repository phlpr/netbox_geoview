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
- Run the separate local integration and browser suites in [TESTING.md](TESTING.md)
  for each newly supported NetBox version; the lightweight CI job alone is insufficient.

## Release preparation

1. Select a new, unpublished semantic version.
2. Update `__version__`, `NETBOX_MIN_VERSION`, and `NETBOX_MAX_VERSION` in
   `netbox_geoview/version.py`.
3. Update `README.md`, `COMPATIBILITY.md`, and `CHANGELOG.md`.
4. Run the unit tests and a smoke test with every newly supported NetBox line.
5. Build both distributions and validate their metadata:

   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   python -m build
   python -m twine check dist/*
   ```

6. Verify that the wheel contains templates, static assets, translations,
   management commands, and packaged test-data resources.
7. Install the wheel into a clean NetBox environment and run `manage.py check`
   plus `manage.py collectstatic --no-input`.

### Test release (manual)

- Push the release commit to the default branch.
- Run GitHub Actions workflow `Publish to TestPyPI` manually.
- Install the exact version from TestPyPI in a disposable environment and
  repeat the NetBox smoke test.

### Production release (tag-based)

1. Update version in `netbox_geoview/version.py`.
2. Commit and push changes to default branch.
3. Create and push a version tag in `vX.Y.Z` format.
4. Workflow `Publish to PyPI` will run automatically for `v*` tags.
5. Confirm the package on PyPI and the generated GitHub release.

Example:

```bash
git tag v0.2.0
git push origin v0.2.0
```
