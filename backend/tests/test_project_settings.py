import unittest

from flask import Flask

from backend.database import Project, db
from backend.services.project_settings import (
    update_project_settings,
    update_project_settings_tool,
)


SETTINGS = {
    "tone": "Academic",
    "writing_style": "Formal",
    "academic_level": "Graduate",
    "language": "English",
    "essay_type": "Argumentative",
    "additional_instructions": "Cite recent sources",
}


class ProjectSettingsTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.project = Project(name="Wrong title", settings=dict(SETTINGS), description="old")
        db.session.add_all([self.project, Project(name="Taken title")])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()

    def test_changes_only_the_given_settings_and_rerenders_the_description(self):
        result = update_project_settings(
            self.project.id, {"title": "  Climate essay ", "tone": "Persuasive"}
        )

        self.assertEqual(result["name"], "Climate essay")
        self.assertEqual(result["settings"], {**SETTINGS, "tone": "Persuasive"})
        self.assertIn("Use a persuasive tone.", result["description"])
        self.assertIn("Also: Cite recent sources", result["description"])
        db.session.expire_all()
        self.assertEqual(db.session.get(Project, self.project.id).name, "Climate essay")

    def test_empty_additional_instructions_clears_them(self):
        result = update_project_settings(self.project.id, {"additional_instructions": ""})

        self.assertIsNone(result["settings"]["additional_instructions"])
        self.assertNotIn("Also:", result["description"])

    def test_project_without_settings_starts_from_defaults(self):
        project = Project(name="Bare project")
        db.session.add(project)
        db.session.commit()

        result = update_project_settings(project.id, {"language": "Portuguese"})

        self.assertEqual(result["settings"]["language"], "Portuguese")
        self.assertEqual(result["settings"]["tone"], "Academic")

    def test_rejected_value_changes_nothing(self):
        for changes, message in (
            ({"title": "New title", "tone": "Loud"}, "tone is invalid."),
            ({"title": "Taken title"}, "Another project already uses this title."),
            ({"title": "   "}, "title is required."),
            ({"colour": "red"}, "Unknown setting: colour."),
            ({}, "Give at least one setting to change."),
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, message):
                    update_project_settings(self.project.id, changes)
                db.session.expire_all()
                project = db.session.get(Project, self.project.id)
                self.assertEqual(project.name, "Wrong title")
                self.assertEqual(project.settings, SETTINGS)

    def test_tool_schema_lists_the_allowed_values(self):
        schema = update_project_settings_tool().definition.input_schema

        self.assertIn("Persuasive", schema["properties"]["tone"]["enum"])
        self.assertIn("title", schema["properties"])
        self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
