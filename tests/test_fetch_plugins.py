import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fetch_plugins


class FetchPluginsTest(unittest.TestCase):
    def test_imports_only_configured_plugin_and_rewrites_skill_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "local"
            external = Path(temp_dir) / "external"
            root.mkdir()
            external.mkdir()
            (root / ".claude-plugin").mkdir()
            (external / ".claude-plugin").mkdir()
            (external / "skills" / "frontend-design").mkdir(parents=True)
            (external / "skills" / "frontend-design" / "SKILL.md").write_text("# frontend-design\n", encoding="utf-8")
            (external / "skills" / "docx").mkdir(parents=True)
            (external / "skills" / "docx" / "SKILL.md").write_text("# docx\n", encoding="utf-8")

            (root / "external_plugins.json").write_text(
                json.dumps([
                    {
                        "marketplace": "example/skills",
                        "plugins": ["document-skills"],
                    }
                ]),
                encoding="utf-8",
            )
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({
                    "name": "local-marketplace",
                    "plugins": [
                        {
                            "name": "translator",
                            "source": "./",
                            "description": "Local translator skill.",
                            "skills": ["./skills/translator"],
                        }
                    ],
                }),
                encoding="utf-8",
            )
            (external / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({
                    "plugins": [
                        {
                            "name": "document-skills",
                            "source": "./",
                            "description": "Document skills.",
                            "skills": [
                                "./skills/frontend-design",
                                "./skills/docx",
                            ],
                        },
                        {
                            "name": "ignored-plugin",
                            "source": "./",
                            "description": "Ignored plugin.",
                            "skills": ["./skills/ignored"],
                        },
                    ]
                }),
                encoding="utf-8",
            )

            imported = fetch_plugins.import_external_plugins(
                root=root,
                fetch_marketplace=lambda _spec, _workspace: external,
            )

            self.assertEqual(imported, ["document-skills"])
            external_skills = root / "external_plugins" / "example" / "skills" / "skills"
            self.assertTrue((external_skills / "frontend-design" / "SKILL.md").exists())
            self.assertTrue((external_skills / "docx" / "SKILL.md").exists())
            marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
            plugins = {plugin["name"]: plugin for plugin in marketplace["plugins"]}
            self.assertEqual(set(plugins), {"translator", "document-skills"})
            self.assertEqual(plugins["document-skills"]["source"], "./")
            self.assertEqual(
                plugins["document-skills"]["skills"],
                [
                    "./external_plugins/example/skills/skills/frontend-design",
                    "./external_plugins/example/skills/skills/docx",
                ],
            )

    def test_import_is_idempotent_by_plugin_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "local"
            external = Path(temp_dir) / "external"
            root.mkdir()
            external.mkdir()
            (root / ".claude-plugin").mkdir()
            (external / ".claude-plugin").mkdir()
            (external / "skills" / "docx").mkdir(parents=True)
            (external / "skills" / "docx" / "SKILL.md").write_text("# docx\n", encoding="utf-8")
            (root / "external_plugins.json").write_text(
                json.dumps([{"marketplace": "example/skills", "plugins": ["document-skills"]}]),
                encoding="utf-8",
            )
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "local-marketplace", "plugins": []}),
                encoding="utf-8",
            )
            (external / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({
                    "plugins": [
                        {
                            "name": "document-skills",
                            "source": "./",
                            "description": "Document skills.",
                            "skills": ["./skills/docx"],
                        }
                    ]
                }),
                encoding="utf-8",
            )

            for _ in range(2):
                fetch_plugins.import_external_plugins(
                    root=root,
                    fetch_marketplace=lambda _spec, _workspace: external,
                )

            marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [plugin["name"] for plugin in marketplace["plugins"]],
                ["document-skills"],
            )

    def test_empty_plugins_array_imports_all_marketplace_plugins(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "local"
            external = Path(temp_dir) / "external"
            root.mkdir()
            external.mkdir()
            (root / ".claude-plugin").mkdir()
            (external / ".claude-plugin").mkdir()
            (external / "skills" / "docx").mkdir(parents=True)
            (external / "skills" / "docx" / "SKILL.md").write_text("# docx\n", encoding="utf-8")
            (external / "skills" / "pdf").mkdir(parents=True)
            (external / "skills" / "pdf" / "SKILL.md").write_text("# pdf\n", encoding="utf-8")
            (root / "external_plugins.json").write_text(
                json.dumps([{"marketplace": "example/skills", "plugins": []}]),
                encoding="utf-8",
            )
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "local-marketplace", "plugins": []}),
                encoding="utf-8",
            )
            (external / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({
                    "plugins": [
                        {
                            "name": "document-skills",
                            "source": "./",
                            "description": "Document skills.",
                            "skills": ["./skills/docx"],
                        },
                        {
                            "name": "pdf-skills",
                            "source": "./",
                            "description": "PDF skills.",
                            "skills": ["./skills/pdf"],
                        },
                    ]
                }),
                encoding="utf-8",
            )

            imported = fetch_plugins.import_external_plugins(
                root=root,
                fetch_marketplace=lambda _spec, _workspace: external,
            )

            self.assertEqual(imported, ["document-skills", "pdf-skills"])
            marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
            plugins = {plugin["name"]: plugin for plugin in marketplace["plugins"]}
            self.assertEqual(set(plugins), {"document-skills", "pdf-skills"})
            self.assertEqual(plugins["document-skills"]["skills"], ["./external_plugins/example/skills/skills/docx"])
            self.assertEqual(plugins["pdf-skills"]["skills"], ["./external_plugins/example/skills/skills/pdf"])

    def test_infers_skills_from_plugin_source_when_skills_array_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "local"
            external = Path(temp_dir) / "external"
            root.mkdir()
            external.mkdir()
            (root / ".claude-plugin").mkdir()
            (external / ".claude-plugin").mkdir()
            (external / "plugin-root" / "skills" / "using-superpowers").mkdir(parents=True)
            (external / "plugin-root" / "skills" / "using-superpowers" / "SKILL.md").write_text("# using-superpowers\n", encoding="utf-8")
            (external / "plugin-root" / "skills" / "systematic-debugging").mkdir(parents=True)
            (external / "plugin-root" / "skills" / "systematic-debugging" / "SKILL.md").write_text("# systematic-debugging\n", encoding="utf-8")
            (external / "plugin-root" / "skills" / "notes-without-skill").mkdir(parents=True)
            (external / "plugin-root" / "skills" / "notes-without-skill" / "README.md").write_text("# notes\n", encoding="utf-8")
            (external / "plugin-root" / ".claude-plugin").mkdir(parents=True)
            (external / "plugin-root" / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "superpowers"}),
                encoding="utf-8",
            )
            (external / "plugin-root" / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "external-marketplace"}),
                encoding="utf-8",
            )
            (root / "external_plugins.json").write_text(
                json.dumps([{"marketplace": "example/superpowers", "plugins": ["superpowers"]}]),
                encoding="utf-8",
            )
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "local-marketplace", "plugins": []}),
                encoding="utf-8",
            )
            (external / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({
                    "plugins": [
                        {
                            "name": "superpowers",
                            "source": "./plugin-root",
                            "description": "Core skills library.",
                        }
                    ]
                }),
                encoding="utf-8",
            )

            imported = fetch_plugins.import_external_plugins(
                root=root,
                fetch_marketplace=lambda _spec, _workspace: external,
            )

            self.assertEqual(imported, ["superpowers"])
            marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
            plugins = {plugin["name"]: plugin for plugin in marketplace["plugins"]}
            self.assertEqual(
                plugins["superpowers"]["skills"],
                [
                    "./external_plugins/example/superpowers/skills/systematic-debugging",
                    "./external_plugins/example/superpowers/skills/using-superpowers",
                ],
            )
            self.assertTrue(
                (root / "external_plugins" / "example" / "superpowers" / "skills" / "using-superpowers" / "SKILL.md").exists()
            )
            self.assertFalse(
                (root / "external_plugins" / "example" / "superpowers" / "skills" / "notes-without-skill").exists()
            )
            copied_metadata_dir = root / "external_plugins" / "example" / "superpowers" / ".claude-plugin"
            self.assertEqual(
                json.loads((copied_metadata_dir / "plugin.json").read_text(encoding="utf-8")),
                {"name": "superpowers"},
            )
            self.assertFalse((copied_metadata_dir / "marketplace.json").exists())

    def test_reads_skills_from_plugin_json_when_marketplace_entry_omits_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "local"
            external = Path(temp_dir) / "external"
            root.mkdir()
            external.mkdir()
            (root / ".claude-plugin").mkdir()
            (external / ".claude-plugin").mkdir()
            (external / ".claude" / "skills" / "ui-ux-pro-max").mkdir(parents=True)
            (external / ".claude" / "skills" / "ui-ux-pro-max" / "SKILL.md").write_text("# ui-ux-pro-max\n", encoding="utf-8")
            (external / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "ui-ux-pro-max", "skills": ["./.claude/skills/ui-ux-pro-max"]}),
                encoding="utf-8",
            )
            (root / "external_plugins.json").write_text(
                json.dumps(["nextlevelbuilder/ui-ux-pro-max-skill"]),
                encoding="utf-8",
            )
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "local-marketplace", "plugins": []}),
                encoding="utf-8",
            )
            (external / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({
                    "plugins": [
                        {
                            "name": "ui-ux-pro-max",
                            "source": "./",
                            "description": "UI UX Pro Max skill.",
                        }
                    ]
                }),
                encoding="utf-8",
            )

            imported = fetch_plugins.import_external_plugins(
                root=root,
                fetch_marketplace=lambda _spec, _workspace: external,
            )

            self.assertEqual(imported, ["ui-ux-pro-max"])
            marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
            plugins = {plugin["name"]: plugin for plugin in marketplace["plugins"]}
            self.assertEqual(
                plugins["ui-ux-pro-max"]["skills"],
                ["./external_plugins/nextlevelbuilder/ui-ux-pro-max-skill/skills/ui-ux-pro-max"],
            )
            self.assertTrue(
                (root / "external_plugins" / "nextlevelbuilder" / "ui-ux-pro-max-skill" / "skills" / "ui-ux-pro-max" / "SKILL.md").exists()
            )

    def test_missing_configured_plugin_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "local"
            external = Path(temp_dir) / "external"
            root.mkdir()
            external.mkdir()
            (root / ".claude-plugin").mkdir()
            (external / ".claude-plugin").mkdir()
            (root / "external_plugins.json").write_text(
                json.dumps([{"marketplace": "example/skills", "plugins": ["document-skills"]}]),
                encoding="utf-8",
            )
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "local-marketplace", "plugins": []}),
                encoding="utf-8",
            )
            (external / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"plugins": []}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(fetch_plugins.FetchPluginsError, "document-skills"):
                fetch_plugins.import_external_plugins(
                    root=root,
                    fetch_marketplace=lambda _spec, _workspace: external,
                )

    def test_load_external_specs_defaults_missing_plugins_to_empty_tuple(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "external_plugins.json"
            config.write_text(
                json.dumps([{"marketplace": "example/skills"}]),
                encoding="utf-8",
            )

            specs = fetch_plugins.load_external_specs(config)

            self.assertEqual(specs[0].plugins, ())

    def test_load_external_specs_accepts_marketplace_string_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "external_plugins.json"
            config.write_text(
                json.dumps(["nextlevelbuilder/ui-ux-pro-max-skill"]),
                encoding="utf-8",
            )

            specs = fetch_plugins.load_external_specs(config)

            self.assertEqual(
                specs,
                [
                    fetch_plugins.ExternalPluginSpec(
                        marketplace="nextlevelbuilder/ui-ux-pro-max-skill",
                        ref=None,
                        plugins=(),
                    )
                ],
            )

    def test_load_external_specs_defaults_ref_to_none(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "external_plugins.json"
            config.write_text(
                json.dumps([{"marketplace": "example/skills", "plugins": ["document-skills"]}]),
                encoding="utf-8",
            )

            specs = fetch_plugins.load_external_specs(config)

            self.assertIsNone(specs[0].ref)

    def test_load_external_specs_accepts_ref(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "external_plugins.json"
            config.write_text(
                json.dumps([{"marketplace": "example/skills", "ref": "v5.1.0", "plugins": ["document-skills"]}]),
                encoding="utf-8",
            )

            specs = fetch_plugins.load_external_specs(config)

            self.assertEqual(specs[0].ref, "v5.1.0")

    def test_clone_marketplace_uses_ref_when_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            spec = fetch_plugins.ExternalPluginSpec(
                marketplace="example/skills",
                ref="v5.1.0",
                plugins=("document-skills",),
            )
            workspace = Path(temp_dir)

            with patch("fetch_plugins.subprocess.run") as run:
                destination = fetch_plugins.clone_marketplace(spec, workspace)

            self.assertEqual(destination, workspace / "example__skills")
            run.assert_called_once_with(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    "v5.1.0",
                    "https://github.com/example/skills.git",
                    str(workspace / "example__skills"),
                ],
                check=True,
            )

    def test_clone_marketplace_omits_branch_when_ref_is_not_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            spec = fetch_plugins.ExternalPluginSpec(
                marketplace="example/skills",
                ref=None,
                plugins=("document-skills",),
            )
            workspace = Path(temp_dir)

            with patch("fetch_plugins.subprocess.run") as run:
                destination = fetch_plugins.clone_marketplace(spec, workspace)

            self.assertEqual(destination, workspace / "example__skills")
            run.assert_called_once_with(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "https://github.com/example/skills.git",
                    str(workspace / "example__skills"),
                ],
                check=True,
            )


if __name__ == "__main__":
    unittest.main()
