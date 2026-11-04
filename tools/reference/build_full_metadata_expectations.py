"""Extract test expectations from immutable actual upstream metadata captures."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    files = {}
    expected = {"default": {}}
    for kind, count in (("algorithms", 12), ("options", 243), ("categories", 8)):
        path = ROOT / "references/metadata" / (kind + ".json")
        value = json.loads(path.read_text("utf-8"))
        assert len(value) == count
        expected["default"][kind] = value
        files[path.relative_to(ROOT).as_posix()] = sha(path)
    for mode, name in (("algorithmsEmpty", "core"), ("layered", "layered")):
        path = ROOT / ("test-runs/20261104-HOST-12/root/recursive-selected-" + name + "-original-01/observation.json")
        oracle = json.loads(path.read_text("utf-8"))
        assert oracle["workerSha256"] == "275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86"
        expected[mode] = oracle["observation"]["metadata"]
        files[path.relative_to(ROOT).as_posix()] = sha(path)
    output = ROOT / "tests/fixtures/suites/full-native-core/metadata-expected.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump({"schema": "pyelk-full-metadata-expectations/v1", "upstreamVersion": "0.12.1",
                   "sourceFilesSha256": files, "expectedQueries": expected}, stream, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
