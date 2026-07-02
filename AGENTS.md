# Project Protocol

This project uses the Superpowers workflow with a project-specific restriction:
subagents are disabled.

## Superpowers Allowlist

Use only these Superpowers skills, in this order for normal development work:

1. `superpowers:brainstorming`
2. `superpowers:using-git-worktrees`
3. `superpowers:writing-plans`
4. `superpowers:executing-plans`
5. `superpowers:test-driven-development`
6. `superpowers:requesting-code-review`
7. `superpowers:finishing-a-development-branch`

Cross-cutting quality gates:

1. `superpowers:systematic-debugging`
2. `superpowers:verification-before-completion`
3. `superpowers:requesting-code-review` when important changes have not yet been reviewed

## Subagent Ban

Do not use subagents in this project.

Forbidden:

1. `superpowers:subagent-driven-development`
2. `superpowers:dispatching-parallel-agents`
3. Any tool or workflow that dispatches, spawns, or delegates to subagents

When a Superpowers skill recommends `subagent-driven-development`, use
`superpowers:executing-plans` instead.

See [docs/superpowers/protocol.md](/home/shx/projects/binary_faithful_decompilation/docs/superpowers/protocol.md)
for the expanded project protocol.
