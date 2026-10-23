import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.release_notes import build_release_notes


REPOSITORY = "phlpr/netbox_geoview"
ROOT = Path(__file__).resolve().parents[1]


class ReleaseNotesTests(unittest.TestCase):
    def test_extracts_only_selected_release_and_preserves_markdown(self):
        body = "### Added\n\n- Use `role` colors.\n\n```python\nuse_role_colors = True\n```"
        changelog = (
            "# Changelog\n\n## Unreleased\n\n- Future changes.\n\n"
            "## 0.9.0 - 2026-10-22\n\n" + body + "\n\n"
            "## 0.8.2 - 2026-10-01\n\n- Older changes.\n"
        )
        self.assertEqual(
            build_release_notes(changelog, "0.9.0", REPOSITORY),
            body + "\n\n**Full Changelog**: "
            "https://github.com/phlpr/netbox_geoview/compare/v0.8.2...v0.9.0\n",
        )

    def test_first_release_has_no_compare_link(self):
        self.assertEqual(
            build_release_notes("## 0.1.0 - 2026-01-01\n\n- Initial release.\n", "0.1.0", REPOSITORY),
            "- Initial release.\n",
        )

    def test_undated_historical_release_can_be_comparison_base(self):
        notes = build_release_notes(
            "## 0.6.0 - 2026-08-22\n\n- New changes.\n\n## 0.5.0\n\n- Old changes.\n",
            "0.6.0", REPOSITORY,
        )
        self.assertIn("/compare/v0.5.0...v0.6.0", notes)

    def test_missing_or_similar_version_is_rejected(self):
        for heading in ("Unreleased", "0.9.01 - 2026-10-22", "0.9.0rc1 - 2026-10-22"):
            with self.subTest(heading=heading), self.assertRaisesRegex(ValueError, "found 0"):
                build_release_notes(f"## {heading}\n\n- Changes.\n", "0.9.0", REPOSITORY)

    def test_duplicate_entries_are_rejected(self):
        entry = "## 0.9.0 - 2026-10-22\n\n- Changes.\n"
        with self.assertRaisesRegex(ValueError, "found 2"):
            build_release_notes(entry + "\n" + entry, "0.9.0", REPOSITORY)

    def test_empty_entries_cannot_borrow_content_from_next_release(self):
        for body in ("", "\n\n", "### Added\n\n### Fixed", "<!-- TODO: write notes -->\n\n### Added"):
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, "no release notes"):
                build_release_notes(
                    f"## 0.9.0 - 2026-10-22\n\n{body}\n\n## 0.8.2\n\n- Old changes.\n",
                    "0.9.0", REPOSITORY,
                )

    def test_missing_or_invalid_date_is_rejected(self):
        for suffix in ("", " - 2026-02-30"):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                build_release_notes(f"## 0.9.0{suffix}\n\n- Changes.\n", "0.9.0", REPOSITORY)

    def test_cli_writes_notes_and_rejects_invalid_input_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            changelog = Path(directory) / "CHANGELOG.md"
            output = Path(directory) / "notes.md"
            changelog.write_text("## 0.9.0 - 2026-10-22\n\n- Changes.\n", encoding="utf-8")
            for tag, valid in (("v0.9.0", True), ("v1.0.0", False), ("0.9.0", False)):
                with self.subTest(tag=tag):
                    output.unlink(missing_ok=True)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "scripts/release_notes.py"), tag,
                         "--repository", REPOSITORY, "--changelog", str(changelog),
                         "--output", str(output)],
                        text=True, capture_output=True,
                    )
                    if valid:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(output.read_text(encoding="utf-8"), "- Changes.\n")
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
