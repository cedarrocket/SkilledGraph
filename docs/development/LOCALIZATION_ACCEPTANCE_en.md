# Bilingual localization acceptance

Date: 2026-10-14. Added _cn/_en standards, guides, examples, Python companions, tests and synthetic materials while retaining original entries. See [maintenance](../LOCALIZATION_en.md) for naming/shared exceptions.

- Full original/Chinese/English unittest: **822/822 passed**, 274 per version; these are three variants of the same contracts, not 822 independent new features.
- Chinese and English local MCP: **4/4 each**, using actual stdio children, discovery, direct calls, two graph rounds and cleanup with offline models.
- Coverage, Python syntax, relative links, original fixture bytes and fixture-manifest contracts checked.
- SHA256 of all 18 core DSL files matched their prechange values; syntax/execution/building/State/reducer protocols were unchanged.
- Editable installation, wheel construction, both agent CLI/module help entries checked; wheel contains both agent workflows and independent Host modules.

A translated repeated-background string increased the compaction test's input size. Its English repetition count was adjusted to preserve the original budget scale; runtime thresholds were unchanged. Standalone MCP checking found a bare from host import, corrected to the matching-language Host and successfully rerun.

No cloud models, historical live reruns or new Windows testing were performed. Original API evidence and historical reports preserve their measured scope. agent-guide remains Git-excluded.

Default discovery now runs three suites. Use maintenance -p commands for one language. Language-independent maintenance tools/manifests are shared.
