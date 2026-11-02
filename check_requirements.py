
import json
import re
import urllib.request
import urllib.error

from packaging.specifiers import SpecifierSet
from packaging.version import Version


PYTHON_VERSION = Version("3.11")
PYPI_URL = "https://pypi.org/pypi"


def fetch_json(url):
    """Fetch JSON data from PyPI."""
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Python311-Requirements-Checker"}
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise

    except urllib.error.URLError as error:
        print(f"Network error: {error}")
        return None


def parse_requirement(line):
    """Parse package==version."""
    line = line.strip()

    if not line or line.startswith("#"):
        return None

    match = re.fullmatch(
        r"([A-Za-z0-9_.-]+)\s*==\s*([A-Za-z0-9_.+-]+)",
        line
    )

    if not match:
        raise ValueError(f"Unsupported requirement: {line}")

    return match.group(1), match.group(2)


def get_minimum_python(specifier):
    """Get the highest explicit lower bound."""
    if not specifier:
        return None

    spec = SpecifierSet(specifier)
    minimum = None

    for item in spec:
        if item.operator in (">=", ">"):
            version = Version(item.version)

            if minimum is None or version > minimum:
                minimum = version

    return minimum


def check_requirements(filename):
    not_found = []
    incompatible = []
    highest_requirement = None

    with open(filename, "r", encoding="utf-8") as file:
     all_lines = file.readlines()

    lines = [
     line.strip()
     for line in all_lines
    if line.strip() and not line.strip().startswith("#")
    ]

    for line in lines:
        requirement = parse_requirement(line)

        if requirement is None:
            continue

        name, version = requirement

        print(f"Checking {name}=={version}...")

        package_data = fetch_json(
            f"{PYPI_URL}/{name}/json"
        )

        if package_data is None:
            not_found.append(f"{name}=={version}")
            continue

        release_data = fetch_json(
            f"{PYPI_URL}/{name}/{version}/json"
        )

        if release_data is None:
            not_found.append(f"{name}=={version}")
            continue

        requires_python = (
            release_data.get("info", {}).get("requires_python")
        )

        if requires_python:
            spec = SpecifierSet(requires_python)

            if PYTHON_VERSION not in spec:
                incompatible.append(
                    f"{name}=={version} ({requires_python})"
                )

        # Check minimum Python requirements of all releases.
        for release_version, files in package_data.get(
            "releases", {}
        ).items():

            for release_file in files:
                release_requires_python = release_file.get(
                    "requires_python"
                )

                if not release_requires_python:
                    continue

                try:
                    minimum = get_minimum_python(
                        release_requires_python
                    )
                except Exception:
                    continue

                if minimum is not None:
                    if (
                        highest_requirement is None
                        or minimum > highest_requirement[0]
                    ):
                        highest_requirement = (
                            minimum,
                            name,
                            release_version
                        )

    print("\n========== RESULTS ==========")
    print(f"Dependencies checked: {len(lines)}")
    print(f"Not found on PyPI: {not_found}")
    print(f"Incompatible with Python 3.11: {incompatible}")

    if highest_requirement:
        minimum, name, version = highest_requirement
        print(
            f"highest_requirement: "
            f"{name}=={version} (>= {minimum})"
        )
    else:
        print("highest_requirement: None")


if __name__ == "__main__":
    check_requirements("requirments.txt")
