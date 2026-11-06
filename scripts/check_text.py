"""Check the basic card contract for one stage against accepted stage sources."""
import json
import re
import sys
import unicodedata
from pathlib import Path

COUNTS = [200, 800, 1200, 1600, 1600, 1600, 1800, 1800, 1600, 1200]
REQUIRED = {
    "schema_version", "id", "locale", "sentence", "cloze", "answer",
    "accepted_answers", "lemma", "meaning", "part_of_speech",
}
SPECIFIC = {"target_reading", "learning_role", "pronunciation", "usage"}


def length(value):
    return sum(not ch.isspace() for ch in unicodedata.normalize("NFC", value))


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def main():
    stage = int(sys.argv[1])
    root = Path(__file__).resolve().parents[1]
    cards = json.loads((root / f"cards/ja-JP/{stage:02}.json").read_text())
    coverage = (root / f"coverage/ja-JP/{stage:02}.md").read_text()
    expected = [f"ja-{stage:02}-{index:04}" for index in range(1, COUNTS[stage] + 1)]
    assert isinstance(cards, list) and len(cards) == COUNTS[stage], "Wrong card count"
    assert [card["common"]["id"] for card in cards] == expected, "Wrong IDs/order"
    rows = [line.split("|")[1:4] for line in coverage.splitlines()
            if re.match(r"\| ja-\d\d-\d{4} \|", line)]
    assert [row[0].strip() for row in rows] == expected, "Coverage IDs/count/order differ"
    assert all(all(cell.strip() for cell in row) for row in rows), "Empty coverage value"
    sentence_cap = 28 if stage <= 1 else 40 if stage == 2 else 60
    seen_ids, seen_sentences = set(), set()
    for previous in range(stage):
        path = root / f"cards/ja-JP/{previous:02}.json"
        assert path.exists(), f"Missing accepted stage {previous:02}"
        for card in json.loads(path.read_text()):
            seen_ids.add(card["common"]["id"])
            seen_sentences.add(unicodedata.normalize("NFC", card["common"]["sentence"]))
    for card in cards:
        assert set(card) == {"common", "language_specific"}, "Wrong top-level fields"
        common, specific = card["common"], card["language_specific"]
        identity = common["id"]
        assert REQUIRED <= set(common) <= REQUIRED | {"register", "note"}, identity
        assert type(common["schema_version"]) is int and common["schema_version"] == 2, identity
        assert common["locale"] == "ja-JP", identity
        for key in set(common) - {"schema_version", "accepted_answers"}:
            assert isinstance(common[key], str) and common[key].strip(), (identity, key)
        assert isinstance(common["accepted_answers"], list), identity
        assert all(isinstance(value, str) and value.strip()
                   for value in common["accepted_answers"]), identity
        assert common["answer"] == common["cloze"], identity
        assert sum(common["sentence"].startswith(common["cloze"], offset)
                   for offset in range(len(common["sentence"]))) == 1, identity
        assert length(common["sentence"]) <= sentence_cap, (identity, "sentence cap")
        assert all(0 < length(value) <= 16
                   for value in [common["cloze"], *common["accepted_answers"]]), identity
        assert isinstance(specific, dict), identity
        assert {"target_reading", "learning_role"} <= set(specific) <= SPECIFIC, identity
        assert all(isinstance(value, str) and value.strip() for value in specific.values()), identity
        assert specific["learning_role"] in {"production", "recognition"}, identity
        assert all(value == unicodedata.normalize("NFC", value) for value in strings(card)), identity
        assert identity not in seen_ids, (identity, "duplicate ID")
        assert common["sentence"] not in seen_sentences, (identity, "duplicate sentence")
        seen_ids.add(identity)
        seen_sentences.add(common["sentence"])
    print(f"PASS: stage {stage:02}, {len(cards)} cards and coverage rows; fields, IDs, clozes, caps and duplicates.")


if __name__ == "__main__":
    main()
