from __future__ import annotations

import io
import json
import unittest

from agentutils.protocol import EXIT, AgentError, envelope, error_envelope, write_json


class UnitProtocolTests(unittest.TestCase):
    def test_success_envelope_is_stable(self) -> None:
        payload = envelope("example", {"value": 1})
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["tool"], "agentutils")
        self.assertEqual(payload["command"], "example")
        self.assertEqual(payload["result"], {"value": 1})
        self.assertEqual(payload["warnings"], [])

    def test_error_envelope_uses_semantic_code(self) -> None:
        error = AgentError("not_found", "missing", path="x", suggestion="check path")
        payload = error_envelope("cat", error)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "not_found")
        self.assertEqual(payload["error"]["path"], "x")
        self.assertEqual(error.exit_code, EXIT["not_found"])

    def test_write_json_emits_parseable_single_document(self) -> None:
        stream = io.StringIO()
        write_json(stream, {"b": 2, "a": 1})
        self.assertEqual(json.loads(stream.getvalue()), {"a": 1, "b": 2})
        self.assertTrue(stream.getvalue().endswith("\n"))


if __name__ == "__main__":
    unittest.main()
