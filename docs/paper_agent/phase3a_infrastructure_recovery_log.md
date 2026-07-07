# Phase 3a Infrastructure Recovery Log

Created: 2026-07-07

Scope: infrastructure recovery only. No candidate generation, semantic labeling,
auditor policy, libFuzzer run, or budget-curve generation is part of this
recovery step.

## Local Preservation

Branch before recovery: `phase3a-prospective-natural-error-census`

Local HEAD before recovery: `c647f856e69da0dcc0037abd44f8976af3d70d10`

Initial status: working tree clean.

Backup bundle:

- Path: `backups/phase3a_corpus_blocker_c647f85.bundle`
- Verification: passed.
- Verified ref:
  `c647f856e69da0dcc0037abd44f8976af3d70d10 refs/heads/phase3a-prospective-natural-error-census`
- Bundle completeness: complete history.

Patch backups:

- `backups/0001-Preregister-Phase-3a-natural-error-census.patch`
- `backups/0002-Record-Phase-3a-producer-availability.patch`
- `backups/0003-Add-Phase-3a-corpus-blocker-census.patch`

## GitHub Push Authentication Diagnosis

Remote:

- `origin git@github.com:sarahshi99/binary_faithful_decompilation.git`

GitHub CLI:

- `gh` is not installed.

Git LFS:

- `git lfs status` reported no staged or unstaged LFS objects.

SSH configuration:

- `~/.ssh/config` maps `github.com` to
  `~/.ssh/id_ed25519_dllm_infilling`.
- Public key fingerprint:
  `SHA256:/biWJh6M4cpeW85SGEg4gTyR5kFt8be3a52St1zDHlM`.

SSH auth test:

- `ssh -T git@github.com` succeeded at network/auth level, but authenticated as
  `sarahshi99/dllm_infilling`.
- Interpretation: the configured key is a deploy key for the
  `sarahshi99/dllm_infilling` repository, not a write-capable credential for
  `sarahshi99/binary_faithful_decompilation`.

Push status:

- Previous and current pushes to
  `phase3a-prospective-natural-error-census` failed with
  `Permission to sarahshi99/binary_faithful_decompilation.git denied to deploy key`.

Push credential status:

- `push_blocked_no_write_credential`

Recommended user-side fix:

1. Create a new repo-specific SSH key on this server:
   `ssh-keygen -t ed25519 -C "h200-binary-faithful-phase3a" -f ~/.ssh/id_ed25519_binary_faithful -N ""`
2. Print only the public key:
   `cat ~/.ssh/id_ed25519_binary_faithful.pub`
3. In GitHub, open
   `sarahshi99/binary_faithful_decompilation` -> Settings -> Deploy keys ->
   Add deploy key.
4. Paste the public key, give it a clear title such as
   `h200-binary-faithful-phase3a`, and enable `Allow write access`.
5. Update `~/.ssh/config` to use this key for this repository, preferably via
   a host alias:
   `Host github-bfd`
   `HostName github.com`
   `User git`
   `IdentityFile ~/.ssh/id_ed25519_binary_faithful`
   `IdentitiesOnly yes`
6. Set the repo remote to:
   `git remote set-url origin git@github-bfd:sarahshi99/binary_faithful_decompilation.git`
7. Verify:
   `ssh -T git@github-bfd`
8. Push:
   `git push -u origin phase3a-prospective-natural-error-census`

Alternative fix: configure an HTTPS remote plus an existing GitHub PAT through
the credential helper, without printing the token.

## Outbound Network Diagnosis

Date:

- `Tue Jul  7 05:51:46 UTC 2026`

Proxy environment:

- `HTTP_PROXY=http://127.0.0.1:7890`
- `HTTPS_PROXY=http://127.0.0.1:7890`
- `ALL_PROXY=http://127.0.0.1:7890`

Shell proxy alias:

- Interactive bash defines `proxy` as:
  `export http_proxy=http://127.0.0.1:7890;export https_proxy=http://127.0.0.1:7890`
- This alias only sets environment variables; it does not start the proxy
  process.

Sandbox connectivity:

- DNS for `github.com`, `api.github.com`, and `gitlab.com` failed inside the
  restricted network namespace.
- `curl -I https://github.com` and `curl -I https://api.github.com` failed with
  `Couldn't connect to server`.
- `git ls-remote https://github.com/yaml/libyaml.git HEAD` failed inside the
  sandbox with `Couldn't connect to server`.

Host-side approved git connectivity:

- `git ls-remote https://github.com/akheron/jansson.git HEAD` succeeded and
  returned `a8b3c5999e752d895030360c553ba66fa6630ed0`.
- A first `git ls-remote https://github.com/yaml/libyaml.git HEAD` attempt
  failed with `gnutls_handshake() failed: The TLS connection was non-properly
  terminated`, so project acquisition should retry individual repositories.

Interpretation:

- The Codex sandbox cannot use the host proxy via `127.0.0.1:7890`.
- Approved top-level `git clone` / `git ls-remote` commands can reach the
  external network from the host context, though individual repositories may
  require retry.
