"""LESSONS protocol - failed action experience for avoidance.

Following PhyAgentOS pattern where LESSONS.md records
failed actions to prevent repeating mistakes.
"""

from dataclasses import dataclass


@dataclass
class LessonEntry:
    """Single lesson from failed action.

    Following 《工业Agent设计准则》P4闭环:
    - Records what went wrong
    - Provides avoidance suggestion
    - Used by CriticValidator to prevent repeated failures
    """
    action_type: str
    params: dict
    failure_reason: str
    avoidance_suggestion: str = ""


def parse_lessons_protocol(content: dict) -> list[LessonEntry]:
    """Parse lessons protocol content into LessonEntry list.

    Args:
        content: Dict parsed from LESSONS.md JSON

    Returns:
        List of LessonEntry objects
    """
    lessons_data = content.get("lessons", [])
    return [LessonEntry(**lesson) for lesson in lessons_data]


def format_lessons_protocol(lessons: list[LessonEntry]) -> dict:
    """Format LessonEntry list into lessons protocol dict.

    Args:
        lessons: List of LessonEntry objects

    Returns:
        Dict ready for serialization to LESSONS.md
    """
    return {
        "schema_version": "EmbodiedAgentsSys.lessons.v1",
        "lessons": [
            {
                "action_type": lesson.action_type,
                "params": lesson.params,
                "failure_reason": lesson.failure_reason,
                "avoidance_suggestion": lesson.avoidance_suggestion,
            }
            for lesson in lessons
        ]
    }


def add_lesson(lessons: list[LessonEntry], new_lesson: LessonEntry) -> list[LessonEntry]:
    """Add a new lesson, avoiding duplicates.

    Args:
        lessons: Existing lessons list
        new_lesson: New lesson to add

    Returns:
        Updated lessons list
    """
    # Avoid exact duplicates (same action_type + params)
    for existing in lessons:
        if (existing.action_type == new_lesson.action_type and
            existing.params == new_lesson.params):
            return lessons
    return lessons + [new_lesson]
