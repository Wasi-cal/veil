# Publish to the GitHub Marketplace

The owner of the project decided this on 2026-11-03. It replaces the placeholder image name of ADR 0013.

## What we decided

- **The Action is public on the Marketplace.** The name is "Veil for Gozu Tickets". The name `Veil` is not possible, because a GitHub user named `veil` exists.
- **The owner is `Wasi-cal`.** Users write `Wasi-cal/veil@v1`. The image is `ghcr.io/wasi-cal/veil:v1`. If the repo moves to an organisation, change `action.yml`, the example workflow, the README and the tests.
- **Calfus owns the code.** The copyright line of `LICENSE`, the author in `action.yml` and the README name Calfus.
- **The license keeps all rights.** The file `LICENSE` says "all rights reserved". It lets people run the Action in their workflows. It does not let them copy or change the code.
- **A tag publishes the image.** The workflow `release-image.yml` runs for a tag such as `v1.2.3`. It runs the tests, builds the image, pushes `v1.2.3` and `v1`, and moves the git tag `v1`. It uses only the `GITHUB_TOKEN` of the workflow.
- **Everything is pinned.** The base images of the `Dockerfile` use a digest. The actions of the workflow use a commit.
- **The README and the badge are part of the listing.** The badge is the icon `git-pull-request` in purple.

## What this costs

- **The code is public.** A Marketplace Action must be in a public repo, and the image must be public. The license is the only protection. `docs/release.md` lists two ways to go further.
- **Every commit is public.** Review the files and the history before the repo changes to public.
- **A new package is private.** The owner must change the visibility of the image by hand after the first release.
- **The listing is under a personal account.** Calfus owns the code, but the repo, the listing and the image sit under `Wasi-cal`. A move to a company organisation is easier before the first release than after.
- **A digest or a pinned commit does not update by itself.** A person reviews each new one.
- **The image was built and run only on one machine.** The local run checked four cases. No real Jira, GitHub or OpenAI answered.
