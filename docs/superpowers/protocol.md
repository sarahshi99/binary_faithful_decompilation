# Superpowers Project Protocol

This repository allows Superpowers for engineering process, but explicitly
disables subagent workflows.

## Basic Engineering Workflow

Use the allowed Superpowers skills in this sequence for normal feature work:

1. `superpowers:brainstorming`
2. `superpowers:using-git-worktrees`
3. `superpowers:writing-plans`
4. `superpowers:executing-plans`
5. `superpowers:test-driven-development`
6. `superpowers:requesting-code-review`
7. `superpowers:finishing-a-development-branch`

If a task is small enough that the user explicitly asks for a direct edit, keep
the work scoped, but preserve the same quality gates: understand the request,
make a minimal plan, test before/after where practical, verify before claiming
completion, and request review for important changes.

## Cross-Cutting Quality Gates

Use these gates whenever they apply:

1. `superpowers:systematic-debugging` for bug reports, failing tests, or unclear
   behavior. Establish root cause before fixing.
2. `superpowers:verification-before-completion` before marking work complete.
3. `superpowers:requesting-code-review` when important modifications have not
   yet gone through review.

## Disabled Subagent Workflows

Subagents are disabled for this project. Do not use or allow:

1. `superpowers:subagent-driven-development`
2. `superpowers:dispatching-parallel-agents`
3. Any workflow that spawns, dispatches, delegates to, or coordinates subagents

Do not add `superpowers:subagent-driven-development` to any allowed-skill list.

If upstream Superpowers documentation says to use
`superpowers:subagent-driven-development`, treat this project protocol as the
override and use `superpowers:executing-plans` instead.
