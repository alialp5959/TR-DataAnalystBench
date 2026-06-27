"""Assemble a Hugging Face-uploadable release/ directory.

Produces a self-contained folder that can be pushed to the Hugging Face Hub:

    release/
      README.md                      # the dataset card (from docs/hf_dataset_card.md)
      data/<tier>/<split>.jsonl      # one file per tier and split
      charts/<tier>/*.png            # chart images referenced by chart_path
      stats.json                     # per-tier counts

The release/ directory is a build artifact (git-ignored); run this script,
then upload release/ with `huggingface-cli upload` or the datasets library.
"""

import json
import shutil
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = PROJECT_ROOT / "release"

CARD_PATH = PROJECT_ROOT / "docs" / "hf_dataset_card.md"

TIERS = {
    "synthetic_v01": PROJECT_ROOT / "data" / "processed" / "synthetic_v01.jsonl",
    "synthetic_v02": PROJECT_ROOT / "data" / "processed" / "synthetic_v02.jsonl",
    "real_pilot": PROJECT_ROOT / "data" / "processed" / "real_pilot.jsonl",
    "chart_read_v01": PROJECT_ROOT / "data" / "processed" / "chart_read_v01.jsonl",
}

CHART_DIRS = {
    "synthetic_v01": PROJECT_ROOT / "charts" / "synthetic_v01",
    "synthetic_v02": PROJECT_ROOT / "charts" / "synthetic_v02",
    "real_pilot": PROJECT_ROOT / "charts" / "real_pilot",
    "chart_read_v01": PROJECT_ROOT / "charts" / "chart_read_v01",
}

SPLITS = ["train", "validation", "test"]


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    (RELEASE_DIR / "data").mkdir(parents=True)
    (RELEASE_DIR / "charts").mkdir(parents=True)

    stats = {"total_examples": 0, "tiers": {}}

    for tier, dataset_path in TIERS.items():
        if not dataset_path.exists():
            raise FileNotFoundError(f"Missing {dataset_path}; generate the tier first.")

        examples = load_jsonl(dataset_path)
        tier_dir = RELEASE_DIR / "data" / tier
        tier_dir.mkdir(parents=True)

        split_counts = {}
        for split in SPLITS:
            rows = [e for e in examples if e.get("split") == split]
            (tier_dir / f"{split}.jsonl").write_text(
                "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in rows),
                encoding="utf-8",
            )
            split_counts[split] = len(rows)

        # copy charts referenced by this tier
        chart_src = CHART_DIRS[tier]
        if chart_src.exists():
            shutil.copytree(chart_src, RELEASE_DIR / "charts" / tier)

        stats["tiers"][tier] = {
            "examples": len(examples),
            "splits": split_counts,
            "tasks": sorted(set(e["question_type"] for e in examples)),
            "domains": sorted(set(e["domain"] for e in examples)),
            "answer_types": dict(Counter(e["answer_type"] for e in examples)),
        }
        stats["total_examples"] += len(examples)

    # dataset card -> release/README.md
    shutil.copyfile(CARD_PATH, RELEASE_DIR / "README.md")

    (RELEASE_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Release built successfully.")
    print(f"Output: {RELEASE_DIR}")
    print(f"Total examples: {stats['total_examples']}")
    for tier, info in stats["tiers"].items():
        print(f"  {tier}: {info['examples']} ({info['splits']})")
    print("\nUpload with, e.g.:")
    print("  huggingface-cli upload <user>/TR-DataAnalystBench release . --repo-type dataset")


if __name__ == "__main__":
    main()
