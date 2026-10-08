import gzip
import json
from pathlib import Path


def parse_gcov(path: Path, source: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        report = json.load(stream)
    if str(report.get("format_version")) != "1":
        raise ValueError(f"Unsupported gcov JSON format: {report.get('format_version')}")
    cwd = Path(report.get("current_working_directory", path.parent))
    matches = [item for item in report["files"]
               if (cwd / item["file"]).resolve() == source.resolve()]
    if len(matches) != 1:
        raise ValueError(f"Expected one gcov file record for {source}; found {len(matches)}")
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
    return {"format_version": report["format_version"], "lines": lines,
            "functions": matches[0].get("functions", [])}
