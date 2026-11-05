# clash-ai-proxy — Security review boundaries

OneMi Mihomo/Shadowrocket platform-specific generator. Verify rule ordering, DNS leaks, subscription token exposure, node credential handling and generator/config parity. Never publish private node URLs, tokens, infrastructure addresses or unrelated credentials.

Only use synthetic/isolated probes and authorized test endpoints. No real credentials, user information, production systems or wallet/payment activity in testing. Flag vulnerabilities only with reproducible input path, exact commit, consequence and narrow fix; avoid invented issues and do not weaken security checks to obtain green CI. Report sensitive issues privately to the owner or through private GitHub advisories if enabled. This file is guidance, not a claim of certified security.
