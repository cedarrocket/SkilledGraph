# Documentation Index

[中文](README_cn.md) | [English](README_en.md) | [语言版本 / Languages](LOCALIZATION_en.md)

Welcome to the SkilledGraph documentation hub. If you are **new to SkilledGraph or learning how to author `.md` workflows**, start directly with the first row: **[Tutorials & DSL Authoring Handbook](tutorials/README_en.md)**!

| Category | Entry Points | Best For |
| --- | --- | --- |
| **Tutorials & Authoring Handbook (Start Here)** | **[10-Minute Quickstart](tutorials/01-QUICKSTART_en.md)**, **[Step-by-Step Tutorial](tutorials/02-STEP-BY-STEP_en.md)**, **[DSL & Python Cheat Sheet](tutorials/03-DSL-HANDBOOK_en.md)** ([Index](tutorials/README_en.md)) | Users & workflow authors: visual mental models, progressive examples, Python integration, and troubleshooting |
| **CLI & Usage Reference** | [Usage Guide](development/USAGE_en.md), [Development Guide](standard/v0.1/DEVELOPMENT_GUIDE_en.md) | Checking `sgraph` CLI flags, environment variables, setup wizard options, and contributor checks |
| **Normative Standards** | [v0.1 Standards](standard/v0.1/README_en.md) ([Language Spec](standard/v0.1/LANGUAGE_SPEC_en.md), [Implementation Whitepaper](standard/v0.1/IMPLEMENTATION_WHITEPAPER_en.md)) | Framework maintainers & parser authors: exact grammar rules, execution contracts, and public API boundaries |
| **Status & Test Evidence** | [Project Status](development/STATUS_en.md) | Implemented scope, offline/live acceptance reports, and platform boundaries |

### How Documents Relate

- `tutorials/` and `development/USAGE_en.md` are practical guides for human developers; `examples/` contains 18 runnable workflows, and `tests/fixtures/` holds parser verification cases.
- `standard/v0.1/LANGUAGE_SPEC_en.md` and `IMPLEMENTATION_WHITEPAPER_en.md` define the normative language grammar and runtime contracts.
- Reports and JSON artifacts under `development/` are non-normative evidence from specific test runs and do not override the current standards.
