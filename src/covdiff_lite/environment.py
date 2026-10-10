"""Resolve tools and record the environment before collecting coverage."""

import os
import hashlib
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


TOOL_DEFAULTS = {
    "gcc": "gcc-11",
    "gcov": "gcov-11",
    "clang": "clang-14",
    "llvm_cov": "llvm-cov-14",
    "llvm_profdata": "llvm-profdata-14",
}


def inspect_environment() -> dict:
    tools = {}
    errors = []
    for name, default in TOOL_DEFAULTS.items():
        selected = os.environ.get("COVDIFF_" + name.upper(), default)
        executable = shutil.which(selected)
        item = {"requested": selected, "path": executable}
        tools[name] = item
        if executable is None:
            errors.append(f"Missing tool: {selected}")
            continue
        # LLVM 14 profdata accepts version flags through a subcommand.
        args = [executable, "show", "--version"] if name == "llvm_profdata" else [executable, "--version"]
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=10)
            item["version_output"] = result.stdout + result.stderr
            match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", item["version_output"])
            if result.returncode or not match:
                errors.append(f"Could not read version of {selected}")
            else:
                item["version"] = match.group(0)
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"Cannot invoke {selected}: {exc}")
    for group in (("gcc", "gcov"), ("clang", "llvm_cov", "llvm_profdata")):
        versions = [tools[name].get("version") for name in group]
        if all(versions) and len(set(versions)) != 1:
            errors.append("Unmatched tool versions: " + ", ".join(f"{n}={tools[n]['version']}" for n in group))
    package_file = Path("/opt/covdiff/packages.tsv")
    implementation = hashlib.sha256()
    package_root = Path(__file__).parent
    for path in sorted(package_root.rglob('*.py')):
        implementation.update(str(path.relative_to(package_root)).encode() + b'\0' + path.read_bytes())
    return {
        "schema_version": 1,
        "execution": os.environ.get("COVDIFF_EXECUTION", "native"),
        "image_id": os.environ.get("COVDIFF_IMAGE_ID"),
        "image_reference": os.environ.get("COVDIFF_IMAGE_REFERENCE"),
        "implementation_sha256": implementation.hexdigest(),
        "system": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "tools": tools,
        "packages": package_file.read_text() if package_file.exists() else None,
        "errors": errors,
        "ready": not errors,
    }
