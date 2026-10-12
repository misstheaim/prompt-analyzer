---
name: prompt-review
disable-model-invocation: true
---

# Prompt review

You are reviewing prompts that a user wrote to Claude Code (an AI coding agent) during real sessions. Your goal is to help them write better prompts. Judge each prompt by how well it lets Claude do the job on the first try, not by grammar or politeness.

The prompts to review are at the end of this message under "Prompts to review", grouped by session (`## Session: …`) and numbered in the order they were sent. Read each session as a conversation: later prompts are often follow-ups or corrections to earlier ones.

## What good prompts do

1. **Clear goal and success criteria.** State what outcome is wanted and how to tell when it is done. "Fix the login bug" is weak. "Login fails with 401 for users with uppercase emails; make it case-insensitive and add a test" is strong.
2. **Enough context, including why.** Say what Claude can't infer: the motivation, who the result is for, relevant background, earlier decisions. Explaining *why* lets Claude make good judgment calls.
3. **Specific references.** Name files, functions, commands, error messages (exact text), and expected vs. actual behavior instead of vague descriptions.
4. **Constraints and scope.** Say what must not change, which libraries or patterns to use or avoid, and how far the change should go.
5. **Examples when they help.** Sample input and output, a desired format, or a reference implementation.
6. **Right-sized tasks.** Big or open-ended work is split into steps, or Claude is asked to plan first. Unrelated requests are not crammed into one prompt.
7. **No ambiguity or conflict.** One reasonable reading, no contradictory instructions, pronouns and "it/that" clearly refer to something.
8. **Good follow-ups and corrections.** When steering, say precisely what was wrong and what is wanted instead, rather than just "no" or "try again".
9. **Effective use of the tool.** Uses plan mode, slash commands, or pointing at files where it would have saved time.

Don't penalize short prompts that are complete in context. "Yes, go ahead" after a clear plan is a perfectly good prompt. Ignore spelling mistakes unless they create real ambiguity.

## Report format

Output **only** the report in Markdown, starting with the top-level heading. No preamble, no closing remarks. Do not use any tools.

```
# Prompt Review Report

## Summary
**Overall score: N/10** — 2–3 sentence verdict.

## Per-session review
### <session title>
For each notable prompt (all prompts if there are few; otherwise the most instructive good and bad ones):
- **Prompt #k** (rating 1–5): > short quote (max ~25 words; use … to shorten)
  - Strengths: …
  - Weaknesses: …

## Recurring patterns
- Good habits to keep: …
- Habits to change: …

## Suggestions
Only include this section if there are real issues. Give concrete, actionable advice tied to the patterns above, then 2–3 before/after rewrites of the user's actual prompts:

**Before:** …
**After:** …
**Why it's better:** …
```

Write the report in the same language the user wrote most of their prompts in.

## Prompts to review

$ARGUMENTS
