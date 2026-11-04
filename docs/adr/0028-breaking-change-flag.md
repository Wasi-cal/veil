# A Fix is flagged when it may break something

The owner of the project decided this on 2026-11-04. The plan is in the Jira map GR-32.

## What we decided

- **A Fix is a Breaking change when something outside the lines it edits may stop working or work differently.** The glossary has the full term. An incompatible change to a public interface counts. A Fix that rejects input that worked before counts. A dependency bump counts only with a reason, for example a new major version, a new runtime requirement or a removed API that the code uses.
- **The flag has two values.** A Fix is a Breaking change or it is not. There are no kinds and no levels. A suspicion counts, but only with a concrete reason.
- **The model says it in the `finish` call.** `finish` has a required `breaking` and a `breaking_reason`. The reason is required when `breaking` is true. It follows the rules of the three parts: at most 3 sentences, at most 25 words in a sentence, no copy of the ticket and no secret. A bad answer gets an error text and the model can finish again, inside the existing caps. This adds no model call.
- **A person decides what to do.** The flag never blocks a Fix. The Fix PR still opens, ready for review (ADR 0020).
- **The Engine can add to the flag, and never remove it.** Later tickets add Engine checks. A check never clears a flag that the model set.

## What this costs

- **The model can be wrong.** It can miss a break, or flag a safe Fix. The flag is a hint for a reviewer and is not a proof.
- **Each `finish` call is a little longer.** The prompt has a short block, and a flagged Fix has one more part. The cost is small against the token cap of the ticket.
