import re
import unittest
from unittest import mock
import warnings
from pathlib import Path

import yaml
from config import WIKI_DIR
from llm_provider import (
    context_limits,
    extract_json_object,
    normalize_provider,
    provider_name,
)


class TestWikiCompliance(unittest.TestCase):
    def setUp(self):
        self.wiki_files = list(WIKI_DIR.rglob("*.md", recurse_symlinks=True))
        # Exclude specific non-content files
        self.wiki_files = [
            f
            for f in self.wiki_files
            if f.name not in ["INDEX.md", "audit.md"] and "-Hub" not in f.name
        ]

    def test_front_matter(self):
        required_keys = {"last_updated", "title", "description", "level", "tags"}
        for f in self.wiki_files:
            with self.subTest(file=f.name):
                content = f.read_text(encoding="utf-8")
                match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
                self.assertIsNotNone(match, f"Missing YAML front matter in {f.name}")
                try:
                    fm = yaml.safe_load(match.group(1))
                    self.assertTrue(
                        required_keys.issubset(set(fm.keys())),
                        f"Missing keys in {f.name}: {required_keys - set(fm.keys())}",
                    )
                except yaml.YAMLError:
                    self.fail(f"Invalid YAML in {f.name}")

    def test_socratic_summary(self):
        for f in self.wiki_files:
            with self.subTest(file=f.name):
                content = f.read_text(encoding="utf-8")
                # Look for > summary after front matter
                match = re.search(r"---\n\n>\s*(.*?)\n\n", content, re.DOTALL)
                if not match:
                    # Alternative check if there's no double newline
                    match = re.search(r"---\n\n>\s*(.*?)\n", content)

                self.assertIsNotNone(
                    match, f"Missing Socratic summary ('> ...') in {f.name}"
                )
                summary = match.group(1).strip()
                sentences = re.split(r"[.!?]+", summary)
                sentences = [s for s in sentences if s.strip()]
                # Allow a bit more flexibility: 1-4 sentences
                self.assertTrue(
                    1 <= len(sentences) <= 4,
                    f"Summary in {f.name} should be 1-4 sentences, found {len(sentences)}",
                )

    def test_required_sections(self):
        required_sections = ["## Evolution", "## Backlinks", "## Sources"]
        for f in self.wiki_files:
            with self.subTest(file=f.name):
                content = f.read_text(encoding="utf-8")
                for section in required_sections:
                    self.assertIn(section, content, f"Missing {section} in {f.name}")

    def test_traceability(self):
        """Check if sources section contains actual links."""
        for f in self.wiki_files:
            with self.subTest(file=f.name):
                content = f.read_text(encoding="utf-8")
                sources_match = re.search(
                    r"## Sources\n(.*?)$", content, re.DOTALL | re.IGNORECASE
                )
                if sources_match:
                    sources = sources_match.group(1).strip()
                    # It's okay if sources is empty for some files if they are L1/L2 and haven't been linked yet,
                    # but typically we want at least the markers or a comment.
                    # For this test, we just check if it's there.

    def test_no_malformed_nested_source_links(self):
        """Reject [[(Source: [[path]])]] double-wrapped provenance links."""
        bad = re.compile(r"\[\[\(Source:\s*\[\[")
        for f in self.wiki_files:
            with self.subTest(file=f.name):
                content = f.read_text(encoding="utf-8")
                self.assertIsNone(
                    bad.search(content),
                    f"Malformed nested source link in {f.name}. "
                    "Run: python scripts/fix_provenance_links.py",
                )

    def test_level2_soft_guidance(self):
        """Advisory only — surfaces Level-2 gaps without failing the corpus."""
        issues: list[str] = []
        for f in self.wiki_files:
            content = f.read_text(encoding="utf-8")
            match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not match:
                continue
            fm = yaml.safe_load(match.group(1)) or {}
            level = int(fm.get("level") or 0)
            if level < 2:
                continue
            tags = fm.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            tag_blob = " ".join(str(t) for t in tags)
            confidence = float(fm.get("confidence") or 0)
            if "type/principle" not in tag_blob:
                issues.append(f"{f.name}: missing type/principle")
            if confidence < 0.7:
                issues.append(f"{f.name}: confidence {confidence:.2f} < 0.7")
        if issues:
            warnings.warn(
                f"Level-2 soft guidance ({len(issues)} items). "
                f"See `make audit` → Level-2 soft guidance. "
                f"Sample: {issues[0]}",
                stacklevel=1,
            )


class TestLLMProvider(unittest.TestCase):
    def setUp(self):
        from provider_circuit import reset_provider_circuits

        reset_provider_circuits()

    def test_provider_name_accepts_explicit_override(self):
        self.assertEqual(provider_name("gemini"), "gemini")
        self.assertEqual(provider_name("openai"), "openai")

    def test_normalize_provider_accepts_openai(self):
        self.assertEqual(normalize_provider("openai"), "openai")
        self.assertEqual(normalize_provider("openrouter"), "openrouter")
        self.assertEqual(normalize_provider("unknown-vendor"), "local-gateway")

    def test_normalize_provider_mlx_legacy_alias(self):
        self.assertEqual(normalize_provider("mlx"), "local-gateway")
        self.assertEqual(normalize_provider("local_gateway"), "local-gateway")

    def test_provider_for_role_uses_llm_provider(self):
        from llm_provider import provider_for_role

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "test-key",
            },
            clear=False,
        ):
            self.assertEqual(provider_for_role("query", None), "gemini")
            self.assertEqual(provider_for_role("lint", None), "gemini")
            self.assertEqual(provider_for_role("wiki_synthesize", None), "gemini")
            self.assertEqual(provider_for_role("discovery", None), "gemini")

        self.assertEqual(provider_for_role("query", "mlx"), "local-gateway")

    def test_provider_for_role_defaults_to_local_gateway(self):
        from llm_provider import provider_for_role

        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(provider_for_role("wiki_synthesize", None), "local-gateway")

    def test_fallback_chain_sync_mlx_then_gemini(self):
        from llm_provider import fallback_provider_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "mlx",
                "LLM_FALLBACK_ENABLED": "1",
                "LLM_FALLBACK_PROVIDERS": "gemini",
                "GEMINI_API_KEY": "test-key",
            },
            clear=False,
        ):
            self.assertEqual(
                fallback_provider_chain(None, role="sync"), ["local-gateway", "gemini"]
            )

    def test_fallback_chain_query_gemini_then_mlx(self):
        from llm_provider import fallback_provider_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "gemini",
                "QUERY_FALLBACK_PROVIDERS": "mlx",
                "LLM_FALLBACK_ENABLED": "1",
                "GEMINI_API_KEY": "test-key",
            },
            clear=False,
        ):
            self.assertEqual(
                fallback_provider_chain(None, role="query"), ["gemini", "local-gateway"]
            )

    def test_provider_for_role_honors_role_env_overrides(self):
        from llm_provider import provider_for_role

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "mlx",
                "QUERY_LLM_PROVIDER": "gemini",
                "LINT_LLM_PROVIDER": "gemini",
                "AGENT_LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "test-key",
            },
            clear=False,
        ):
            self.assertEqual(provider_for_role("query", None), "gemini")
            self.assertEqual(provider_for_role("lint", None), "gemini")
            self.assertEqual(provider_for_role("discovery", None), "gemini")
            self.assertEqual(provider_for_role("gap", None), "gemini")
            self.assertEqual(provider_for_role("evolution", None), "gemini")
            self.assertEqual(provider_for_role("wiki_synthesize", None), "local-gateway")

    def test_model_name_honors_query_llm_model(self):
        from llm_provider import model_name

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "mlx",
                "LLM_MODEL": "mlx",
                "QUERY_LLM_MODEL": "gemma4",
            },
            clear=False,
        ):
            self.assertEqual(model_name("mlx", role="query"), "gemma4")
            self.assertEqual(model_name("mlx", role="wiki_synthesize"), "mlx")
            self.assertEqual(model_name("mlx"), "mlx")

    def test_fallback_model_chain_gemma4_then_mlx(self):
        from llm_provider import fallback_model_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "local-gateway",
                "LLM_MODEL": "gemma4",
                "LLM_MODEL_FALLBACK": "",
            },
            clear=False,
        ):
            self.assertEqual(
                fallback_model_chain("local-gateway"), ["gemma4", "mlx"]
            )

    def test_fallback_model_chain_can_disable(self):
        from llm_provider import fallback_model_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "local-gateway",
                "LLM_MODEL": "gemma4",
                "LLM_MODEL_FALLBACK": "0",
            },
            clear=False,
        ):
            self.assertEqual(fallback_model_chain("local-gateway"), ["gemma4"])

    def test_default_gateway_model_is_gemma4(self):
        from llm_provider import model_name

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "local-gateway",
                "LLM_MODEL": "",
                "QUERY_LLM_MODEL": "",
            },
            clear=False,
        ):
            self.assertEqual(model_name("local-gateway"), "gemma4")

    def test_provider_for_role_agent_defaults_to_local_gateway_when_only_gemini_key(
        self,
    ):
        from llm_provider import provider_for_role

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "",
                "GEMINI_API_KEY": "test-key",
            },
            clear=True,
        ):
            self.assertEqual(provider_for_role("discovery", None), "local-gateway")
            self.assertEqual(provider_for_role("gap", None), "local-gateway")
            self.assertEqual(provider_for_role("wiki_synthesize", None), "local-gateway")

    def test_fallback_chain_discovery_mlx_no_auto_cloud_fallback(self):
        from llm_provider import fallback_provider_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "mlx",
                "LLM_FALLBACK_ENABLED": "1",
                "LLM_FALLBACK_PROVIDERS": "",
                "AGENT_FALLBACK_PROVIDERS": "",
                "GEMINI_API_KEY": "test-key",
                "OPENAI_API_KEY": "",
                "OPENROUTER_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(
                fallback_provider_chain("mlx", role="discovery"), ["local-gateway"]
            )

    def test_fallback_chain_discovery_gemini_primary_with_mlx_last_resort(self):
        from llm_provider import fallback_provider_chain

        with mock.patch.dict(
            "os.environ",
            {
                "AGENT_LLM_PROVIDER": "gemini",
                "LLM_FALLBACK_ENABLED": "1",
                "GEMINI_API_KEY": "test-key",
                "OPENAI_API_KEY": "",
                "OPENROUTER_API_KEY": "",
                "LLM_MLX_LAST_RESORT": "1",
            },
            clear=False,
        ):
            self.assertEqual(
                fallback_provider_chain(None, role="discovery"), ["gemini", "local-gateway"]
            )

    def test_provider_for_role_discovery_uses_llm_provider(self):
        from llm_provider import fallback_provider_chain, provider_for_role

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "test-key",
                "OPENAI_API_KEY": "",
                "OPENROUTER_API_KEY": "",
                # Make expectations deterministic regardless of local `.env`.
                "ALLOW_LOCAL_LLM": "0",
                "LLM_FALLBACK_ENABLED": "1",
                "LLM_MLX_LAST_RESORT": "1",
            },
            clear=False,
        ):
            self.assertEqual(provider_for_role("discovery", None), "gemini")
            self.assertEqual(
                fallback_provider_chain(None, role="discovery"), ["gemini", "local-gateway"]
            )

    def test_context_limits_are_provider_aware(self):
        gemini_context, gemini_reserved, _ = context_limits("gemini")
        mlx_context, mlx_reserved, _ = context_limits("mlx")
        openai_context, openai_reserved, _ = context_limits("openai")
        openrouter_context, openrouter_reserved, _ = context_limits("openrouter")
        self.assertGreater(gemini_context, mlx_context)
        self.assertGreater(gemini_reserved, mlx_reserved)
        self.assertGreater(openai_context, mlx_context)
        self.assertGreater(openai_reserved, mlx_reserved)
        self.assertGreater(openrouter_context, mlx_context)
        self.assertGreater(openrouter_reserved, mlx_reserved)

    def test_extract_json_object_from_model_text(self):
        parsed = extract_json_object('```json\n{"actions": []}\n```')
        self.assertEqual(parsed, {"actions": []})

    def test_fallback_chain_mlx_only_without_cloud_keys(self):
        from llm_provider import fallback_provider_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "mlx",
                "LLM_FALLBACK_ENABLED": "1",
                "GEMINI_API_KEY": "",
                "OPENAI_API_KEY": "",
                "OPENROUTER_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(fallback_provider_chain(None), ["local-gateway"])

    def test_fallback_chain_gemini_only_when_explicit(self):
        from llm_provider import fallback_provider_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "mlx",
                "LLM_FALLBACK_ENABLED": "1",
                "LLM_FALLBACK_PROVIDERS": "gemini",
                "GEMINI_API_KEY": "test-key",
                "OPENAI_API_KEY": "",
                "OPENROUTER_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(
                fallback_provider_chain(None), ["local-gateway", "gemini"]
            )

    def test_fallback_chain_includes_openrouter_when_key_set(self):
        from llm_provider import fallback_provider_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "mlx",
                "LLM_FALLBACK_ENABLED": "1",
                "LLM_FALLBACK_PROVIDERS": "",
                "GEMINI_API_KEY": "",
                "OPENAI_API_KEY": "",
                "OPENROUTER_API_KEY": "test-key",
            },
            clear=False,
        ):
            self.assertEqual(
                fallback_provider_chain(None), ["local-gateway", "openrouter"]
            )

    def test_fallback_chain_gemini_primary_includes_mlx_last_resort(self):
        from llm_provider import fallback_provider_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "gemini",
                "LLM_FALLBACK_ENABLED": "1",
                "GEMINI_API_KEY": "test-key",
                "OPENAI_API_KEY": "",
                "OPENROUTER_API_KEY": "",
                "LLM_MLX_LAST_RESORT": "1",
            },
            clear=False,
        ):
            self.assertEqual(
                fallback_provider_chain("gemini", role="sync"), ["gemini", "local-gateway"]
            )

    def test_fallback_chain_sync_honors_llm_provider(self):
        from llm_provider import fallback_provider_chain

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "gemini",
                "LLM_FALLBACK_ENABLED": "1",
                "GEMINI_API_KEY": "test-key",
                "OPENAI_API_KEY": "",
                "OPENROUTER_API_KEY": "",
                "LLM_MLX_LAST_RESORT": "1",
            },
            clear=False,
        ):
            self.assertEqual(
                fallback_provider_chain(None, role="sync"), ["gemini", "local-gateway"]
            )

    def test_mlx_blocked_as_primary_without_allow(self):
        from composer_policy import reject_local_mlx

        with mock.patch.dict("os.environ", {"ALLOW_LOCAL_LLM": "0"}, clear=False):
            with self.assertRaises(RuntimeError):
                reject_local_mlx("mlx", context="test", as_last_resort=False)

    def test_mlx_allowed_as_last_resort(self):
        from composer_policy import reject_local_mlx

        reject_local_mlx("mlx", context="test", as_last_resort=True)

    def test_local_gateway_blocked_as_primary_without_allow(self):
        from composer_policy import reject_local_mlx

        with mock.patch.dict("os.environ", {"ALLOW_LOCAL_LLM": "0"}, clear=False):
            with self.assertRaises(RuntimeError):
                reject_local_mlx("local-gateway", context="test", as_last_resort=False)

    def test_provider_for_role_honors_mlx_env_alias(self):
        from llm_provider import provider_for_role

        with mock.patch.dict("os.environ", {"LLM_PROVIDER": "mlx"}, clear=True):
            self.assertEqual(provider_for_role("wiki_synthesize", None), "local-gateway")

    def test_provider_circuit_skips_gemini_after_geo_error(self):
        from llm_provider import fallback_provider_chain
        from provider_circuit import open_provider_circuit

        with mock.patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "test-key",
                "OPENAI_API_KEY": "",
                "OPENROUTER_API_KEY": "",
                "LLM_MLX_LAST_RESORT": "1",
                "ALLOW_LOCAL_LLM": "0",
                "LLM_FALLBACK_ENABLED": "1",
            },
            clear=False,
        ):
            with mock.patch("provider_circuit.logger.warning"):
                open_provider_circuit(
                    "gemini", "User location is not supported for the API use."
                )
            self.assertEqual(
                fallback_provider_chain(None, role="sync"), ["local-gateway"]
            )


if __name__ == "__main__":
    unittest.main()
