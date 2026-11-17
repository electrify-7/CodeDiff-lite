import gzip
import json
from pathlib import Path


def parse_gcov(path: Path, source: Path) -> dict:
    raw_bytes = path.read_bytes()
    if raw_bytes[:2] == b"\x1f\x8b":
        text = gzip.decompress(raw_bytes).decode("utf-8")
    else:
        text = raw_bytes.decode("utf-8")
    report = json.loads(text)

    ver = str(report.get("format_version", "1"))
    if ver not in ("1", "1.0", "1.1"):
        raise ValueError(f"Unsupported gcov JSON format: {report.get('format_version')}")

    cwd = Path(report.get("current_working_directory", path.parent))
    matches = [item for item in report.get("files", [])
               if (cwd / item["file"]).resolve() == source.resolve()]
    if not matches:
        matches = [item for item in report.get("files", [])
                   if Path(item["file"]).name == source.name]
    if len(matches) > 1:
        exact_matches = [m for m in matches if str(source).endswith(m["file"])]
        if exact_matches:
            matches = [exact_matches[0]]
        else:
            matches = [matches[0]]
    elif len(matches) == 0:
        raise ValueError(f"Expected one gcov file record for {source}; found 0")

    lines = {}
    for item in matches[0]["lines"]:
        number = item["line_number"]
        count = item["count"]
        if type(number) is not int or number < 1 or type(count) is not int or count < 0:
            raise ValueError("Invalid gcov line location or count")
        key = str(number)
        if key in lines:
            raise ValueError(f"Ambiguous duplicate gcov line record: {number}")
        lines[key] = {
            "state": "reported", "count": count, "covered": count > 0,
            "unexecuted_block": item.get("unexecuted_block"),
            "branches": item.get("branches", []),
        }
    return {"format_version": report.get("format_version", "1"), "lines": lines,
            "functions": matches[0].get("functions", [])}
