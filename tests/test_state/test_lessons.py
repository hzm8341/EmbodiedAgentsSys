"""Tests for LESSONS protocol."""
import pytest
from embodiedagentsys.state.protocols.lessons_protocol import (
    LessonEntry, parse_lessons_protocol, format_lessons_protocol, add_lesson
)


class TestLessonEntry:
    def test_lesson_entry_creation(self):
        lesson = LessonEntry(
            action_type="move_to",
            params={"x": 1.0},
            failure_reason="Obstacle detected in path",
            avoidance_suggestion="Plan path around obstacle"
        )
        assert lesson.action_type == "move_to"
        assert "obstacle" in lesson.failure_reason.lower()


class TestLessonsProtocol:
    def test_parse_empty_lessons(self):
        content = {"lessons": []}
        lessons = parse_lessons_protocol(content)
        assert lessons == []

    def test_parse_lessons(self):
        content = {
            "lessons": [
                {
                    "action_type": "grasp",
                    "params": {"target": "red_ball"},
                    "failure_reason": "Object too far",
                    "avoidance_suggestion": "Move closer first"
                }
            ]
        }
        lessons = parse_lessons_protocol(content)
        assert len(lessons) == 1
        assert lessons[0].action_type == "grasp"

    def test_format_lessons(self):
        lesson = LessonEntry(
            action_type="move_to",
            params={"x": 1.0},
            failure_reason="Out of bounds",
            avoidance_suggestion="Check workspace limits"
        )
        content = format_lessons_protocol([lesson])
        assert "lessons" in content
        assert len(content["lessons"]) == 1

    def test_add_lesson_no_duplicates(self):
        existing = [
            LessonEntry("move_to", {"x": 1.0}, "failed")
        ]
        new_lesson = LessonEntry("move_to", {"x": 1.0}, "failed again")
        result = add_lesson(existing, new_lesson)
        assert len(result) == 1  # No duplicate added

    def test_add_lesson_different_action(self):
        existing = [
            LessonEntry("move_to", {"x": 1.0}, "failed")
        ]
        new_lesson = LessonEntry("grasp", {"target": "ball"}, "gripper slipped")
        result = add_lesson(existing, new_lesson)
        assert len(result) == 2  # Different action, should add
