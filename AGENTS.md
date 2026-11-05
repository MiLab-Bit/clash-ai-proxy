# clash-ai-proxy — Code review and Agent guidance

This repository has project-specific constraints: OneMi Mihomo/Shadowrocket platform-specific generator. Verify rule ordering, DNS leaks, subscription token exposure, node credential handling and generator/config parity. Never publish private node URLs, tokens, infrastructure addresses or unrelated credentials.

Review genuine correctness, architecture ownership, auth/data trust boundaries and business regressions. Preserve existing interfaces and validated workflows; avoid speculative abstractions, arbitrary LOC thresholds and generic refactors. Every finding must cite changed file, exact SHA, impact, safe reproduction and smallest correction. Report no findings when none can be verified. Use actual commands/CI evidence and distinguish synthetic tests from production. Read SECURITY.md before security assessments. ChatGPT implements, Codex reviews, MiLab-Bit accepts merge/production decisions; never auto-merge or publish secrets.
