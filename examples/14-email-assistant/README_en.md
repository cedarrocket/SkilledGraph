# Email classification, policy assistance and approved drafts

Classify an email as billing, technical or general, load the relevant policy, draft a reply, and use request_input to ask whether to save it. Saves local Markdown only; sends no email.

```bash
.venv/bin/sgraph examples/14-email-assistant/workflow_en.md -- --demo
.venv/bin/sgraph examples/14-email-assistant/workflow_en.md -- --demo --approval no
.venv/bin/sgraph examples/14-email-assistant/workflow_en.md -- --input 'Email contents' --output ./drafts
```

Live terminal mode displays the draft and asks yes/no. Piped input requires explicit `--approval yes` or `--approval no` when confirmation is reached. This is a user-supplied reply, not a default bypass. Only yes and the Chinese affirmative aliases enter the save path; all other replies cancel. Demo mode defaults to yes for its synthetic draft. Without `--output`, a separate temporary directory is created and printed for later cleanup.

DSL defines every business edge. A transition table handles classification, python loads policies, pyfunction supplies drafting material, request_input collects approval, and native InMemorySaver supports resumption. Filenames are random UUIDs, not model output.

Useful for customer-service or personal reply preparation. Policies are illustrative and must be replaced before use. No mailbox fetching, attachment processing, sending or verification of refund facts is provided. Saving only completes draft preparation.
