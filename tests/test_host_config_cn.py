"""Host environment config; never reads actual user credentials."""
from pathlib import Path
import tempfile
import unittest

from sgraph_chat_host.host_config_cn import model_options


class HostConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_provider_environment_stays_native(self):
        self.assertEqual(model_options(base_dir=self.directory, environ={"DEEPSEEK_API_KEY": "dummy"}), {})

    def test_full_configuration(self):
        options = model_options(base_dir=self.directory, environ={
            "SGRAPH_API_KEY": "dummy", "SGRAPH_BASE_URL": "https://example.test",
            "SGRAPH_TEMPERATURE": "0", "SGRAPH_TIMEOUT": "20",
            "SGRAPH_MAX_TOKENS": "256", "SGRAPH_MAX_RETRIES": "0",
        })
        self.assertEqual(options, {"api_key": "dummy", "base_url": "https://example.test",
                                  "temperature": 0.0, "timeout": 20.0,
                                  "max_tokens": 256, "max_retries": 0})

    def test_file_relative_absolute_and_no_env_mutation(self):
        path = self.directory / "key.txt"
        path.write_text("dummy\n", encoding="utf-8")
        for value in ("key.txt", str(path)):
            env = {"SGRAPH_API_KEY_FILE": value}
            original = env.copy()
            self.assertEqual(model_options(base_dir=self.directory, environ=env), {"api_key": "dummy"})
            self.assertEqual(env, original)

    def test_file_validation_does_not_echo_secret(self):
        path = self.directory / "key.txt"
        for value in ("", "sensitive wrong key"):
            path.write_text(value, encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                model_options(base_dir=self.directory, environ={"SGRAPH_API_KEY_FILE": str(path)})
            self.assertNotIn("sensitive", str(caught.exception))

    def test_key_conflict_and_invalid_numbers(self):
        with self.assertRaises(ValueError):
            model_options(base_dir=self.directory, environ={"SGRAPH_API_KEY": "dummy", "SGRAPH_API_KEY_FILE": "key.txt"})
        for name, value in (("TIMEOUT", "0"), ("TEMPERATURE", "-1"), ("TEMPERATURE", "nan"),
                            ("TIMEOUT", "inf"), ("MAX_TOKENS", "-1"), ("MAX_RETRIES", "-1"),
                            ("MAX_TOKENS", "1.5"), ("MAX_RETRIES", "oops")):
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                model_options(base_dir=self.directory, environ={"SGRAPH_" + name: value})

    def test_missing_file_error(self):
        with self.assertRaises(FileNotFoundError):
            model_options(base_dir=self.directory, environ={"SGRAPH_API_KEY_FILE": "missing.txt"})

    def test_go_session_is_fresh_per_model_and_does_not_mutate_options(self):
        from uuid import UUID
        from sgraph_chat_host.host_config_cn import opencode_go_options
        source = {"base_url": "https://opencode.ai/zen/go/v1/", "default_headers": {"X-Custom": "value"}}
        first, second = opencode_go_options(source), opencode_go_options(source)
        a = first["default_headers"]["x-opencode-session"]
        b = second["default_headers"]["x-opencode-session"]
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("sgraph-harness-agent-"))
        UUID(a.removeprefix("sgraph-harness-agent-"))
        self.assertEqual(first["default_headers"]["User-Agent"], "sgraph-harness-agent/0.1.0.dev0")
        self.assertEqual(source["default_headers"], {"X-Custom": "value"})

    def test_go_explicit_headers_are_case_insensitive_and_preserved(self):
        from sgraph_chat_host.host_config_cn import opencode_go_options
        headers = {"USER-AGENT": "my-host/1.0", "X-OpenCode-Session": "my-conversation"}
        result = opencode_go_options({"base_url": "https://opencode.ai/zen/go/v1", "default_headers": headers})
        self.assertEqual(result["default_headers"], headers)

    def test_other_endpoints_do_not_get_go_identity(self):
        from sgraph_chat_host.host_config_cn import opencode_go_options
        for address in ("https://api.openai.com/v1", "https://api.deepseek.com", "https://opencode.ai/zen/v1",
                        "https://opencode.ai.example.test/zen/go/v1", "https://example.test/opencode.ai/zen/go/v1"):
            source = {"base_url": address}
            self.assertEqual(opencode_go_options(source), source)
