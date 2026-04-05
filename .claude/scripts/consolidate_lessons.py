#!/usr/bin/env python3
"""Analyze and consolidate lessons for maintenance."""
import json
import os
from itertools import combinations


def load_lessons():
    path = os.path.join(
        os.path.dirname(__file__), '..', 'quality', 'ecosystem', 'lessons.json'
    )
    with open(path, 'r') as f:
        return json.load(f)


def analyze(data):
    lessons = data.get('lessonsLearned', [])
    print(f"Total lessons: {len(lessons)}")

    # Type distribution
    types = {}
    for l in lessons:
        t = l.get('type', 'unknown')
        types[t] = types.get(t, 0) + 1

    print("\nType distribution:")
    for t, count in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

    # Tag distribution
    tags = {}
    for l in lessons:
        for t in l.get('tags', []):
            tags[t] = tags.get(t, 0) + 1

    print("\nTag distribution:")
    for tag, count in sorted(tags.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")

    # Check for potential duplicates (lessons with identical tags)
    potential_dupes = []
    for a, b in combinations(lessons, 2):
        a_tags = set(a.get('tags', []))
        b_tags = set(b.get('tags', []))
        if a_tags == b_tags and len(a_tags) > 1:
            potential_dupes.append((a['id'], b['id']))

    if potential_dupes:
        print(f"\nPotential duplicates ({len(potential_dupes)}):")
        for a, b in potential_dupes:
            print(f"  {a} <-> {b}")
    else:
        print("\nNo potential duplicates found")

    # Coverage check
    expected_tags = {
        '#context', '#ownership', '#boundaries', '#maintenance', '#drift',
        '#alignment', '#elimination', '#linking', '#refinement', '#architecture',
        '#workflow', '#adoption', '#progressive', '#infrastructure', '#ecosystem',
        '#simplicity', '#consistency'
    }
    covered = set(tags.keys())
    uncovered = expected_tags - covered

    if uncovered:
        print(f"\nUncovered tags ({len(uncovered)}):")
        for tag in sorted(uncovered):
            print(f"  {tag}")
    else:
        print("\nAll taxonomy tags covered")


if __name__ == '__main__':
    data = load_lessons()
    analyze(data)
