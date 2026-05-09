"""Unit tests for registry/command_specs.py."""

from __future__ import annotations

import unittest

from aicoreutils.parser._parser import build_parser
from aicoreutils.registry.command_specs import (
    ArgumentSpec,
    CommandSpec,
    all_command_specs,
    command_specs_from_parser,
    pilot_spec_names,
    specs_by_name,
)


class ArgumentSpecTests(unittest.TestCase):
    def test_create_argument_spec(self) -> None:
        spec = ArgumentSpec(name="paths", kind="positional", required=True, help="Input files")
        self.assertEqual(spec.name, "paths")
        self.assertEqual(spec.kind, "positional")
        self.assertTrue(spec.required)
        self.assertEqual(spec.help, "Input files")
        self.assertIsNone(spec.nargs)

    def test_create_argument_spec_with_nargs(self) -> None:
        spec = ArgumentSpec(name="paths", kind="positional", required=False, help="Files", nargs="+")
        self.assertEqual(spec.nargs, "+")


class CommandSpecTests(unittest.TestCase):
    def test_create_command_spec(self) -> None:
        spec = CommandSpec(
            name="ls",
            category="fs",
            stability="stable",
            risk_level="read-only",
            handler_name="command_ls",
            summary="List files",
            gnu_compatibility="full",
            arguments=(),
        )
        self.assertEqual(spec.name, "ls")
        self.assertEqual(spec.risk_level, "read-only")
        self.assertEqual(spec.stability, "stable")


class ParserSpecTests(unittest.TestCase):
    def test_command_specs_from_parser(self) -> None:
        parser = build_parser()
        specs = command_specs_from_parser(parser)
        self.assertIsInstance(specs, tuple)
        self.assertGreater(len(specs), 80)
        names = {s.name for s in specs}
        self.assertIn("ls", names)
        self.assertIn("cat", names)
        self.assertIn("sort", names)

    def test_all_command_specs(self) -> None:
        specs = all_command_specs()
        self.assertGreater(len(specs), 80)

    def test_specs_by_name(self) -> None:
        all_specs = all_command_specs()
        by_name = specs_by_name(all_specs)
        self.assertIn("ls", by_name)
        self.assertIn("sort", by_name)
        self.assertEqual(by_name["true"].name, "true")

    def test_pilot_spec_names(self) -> None:
        names = pilot_spec_names()
        self.assertIsInstance(names, set)
        self.assertGreater(len(names), 0)

    def test_specs_consistency(self) -> None:
        """Every parser-derived spec should have a valid handler name."""
        specs = all_command_specs()
        for spec in specs:
            self.assertIsInstance(spec.name, str)
            self.assertIsInstance(spec.handler_name, str)
            self.assertIn(spec.risk_level, ("read-only", "write", "destructive", "process-exec", "platform-sensitive"))
            self.assertIn(spec.stability, ("stable", "experimental", "platform-limited"))


if __name__ == "__main__":
    unittest.main()
