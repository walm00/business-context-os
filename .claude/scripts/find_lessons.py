#!/usr/bin/env python3
"""Search lessons by tags or keywords."""
import json
import sys
import os


def find_lessons(tags=None, keyword=None):
    lessons_path = os.path.join(
        os.path.dirname(__file__), '..', 'quality', 'ecosystem', 'lessons.json'
    )
    with open(lessons_path, 'r') as f:
        data = json.load(f)

    results = []
    for lesson in data.get('lessonsLearned', []):
        if tags:
            lesson_tags = lesson.get('tags', [])
            if any(t in lesson_tags for t in tags):
                results.append(lesson)
        elif keyword:
            if keyword.lower() in lesson.get('lesson', '').lower():
                results.append(lesson)
        else:
            results.append(lesson)

    return results


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--tags':
            tags = sys.argv[2:]
            results = find_lessons(tags=tags)
        elif sys.argv[1] == '--keyword':
            results = find_lessons(keyword=' '.join(sys.argv[2:]))
        else:
            results = find_lessons(keyword=' '.join(sys.argv[1:]))
    else:
        results = find_lessons()

    for r in results:
        print(f"[{r['id']}] {r['lesson']}")
        print(f"  Tags: {', '.join(r.get('tags', []))}")
        print(f"  Apply: {r.get('applicability', 'N/A')}")
        print()

    print(f"Found {len(results)} lesson(s)")
