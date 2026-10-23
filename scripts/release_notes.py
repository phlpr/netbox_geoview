"""Extract a release's notes from CHANGELOG.md without importing the plugin."""

import argparse
import re
from datetime import date
from pathlib import Path


RELEASE_HEADING = re.compile(
    r"(?P<version>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]+)?)"
    r"(?: - (?P<date>\d{4}-\d{2}-\d{2}))?"
)


def build_release_notes(changelog, version, repository):
    headings = list(re.finditer(r"^## (.+)$", changelog, re.MULTILINE))
    releases = [RELEASE_HEADING.fullmatch(heading.group(1).strip()) for heading in headings]
    matches = [
        index for index, release in enumerate(releases)
        if release and release.group("version") == version
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one changelog entry for {version}; found {len(matches)}")

    index = matches[0]
    release_date = releases[index].group("date")
    if not release_date:
        raise ValueError(f"Changelog entry for {version} needs a YYYY-MM-DD release date")
    date.fromisoformat(release_date)

    end = headings[index + 1].start() if index + 1 < len(headings) else len(changelog)
    body = changelog[headings[index].end():end].strip()
    content = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    content = re.sub(r"^#{1,6}\s+.*$", "", content, flags=re.MULTILINE)
    if not content.strip(" \t\r\n-*+"):
        raise ValueError(f"Changelog entry for {version} has no release notes")

    previous = next((release for release in releases[index + 1:] if release), None)
    if previous:
        previous_version = previous.group("version")
        body += (
            f"\n\n**Full Changelog**: https://github.com/{repository}/compare/"
            f"v{previous_version}...v{version}"
        )
    return body + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Release tag matching the package version, e.g. v0.9.0")
    parser.add_argument("--repository", required=True, help="GitHub repository in owner/name form")
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.tag.startswith("v"):
        parser.error("Release tag must start with v")
    try:
        notes = build_release_notes(
            args.changelog.read_text(encoding="utf-8"), args.tag[1:], args.repository
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    args.output.write_text(notes, encoding="utf-8")
    print(f"Release notes validated for {args.tag}: {args.output}")


if __name__ == "__main__":
    main()
