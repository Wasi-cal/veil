# Release checklist

Use this list to publish "Veil for Gozu Tickets" to the GitHub Marketplace. The code is ready. These steps are for the owner of the repo. Only you can do them.

Do the steps in order. Do not skip the first part. A public repo shows every file and every commit.

## 1. Before the repo is public

- [ ] **Review the files that name your company.** These files hold internal names, such as the Jira site `gozu-calfus.atlassian.net` and the repo `Wasi-cal/Odyssey-port6-RAG`:
  - `CLAUDE.md`
  - `docs/trial/` (both files)
  - `docs/walkthrough/` (it describes the design that we removed)
  - `docs/diagrams/`
  - `docs/adr/` (read each ADR once)

  Remove a file, or keep it on purpose. The history keeps every file that was ever committed. If a name must not be public, publish from a new repo with a clean history.
- [ ] **Run the security review.** The project rules ask for `security-review` before a release. This list does not replace it.
- [ ] **Check the name of the copyright holder.** `LICENSE`, `action.yml` and the README say "Calfus". Use the full legal name of the company if it differs, for example with "Inc." or "Ltd.". Ask a lawyer to read `LICENSE`. I am not a lawyer.
- [ ] **Get the approval of Calfus to publish.** The company owns the code. The repo, the Marketplace listing and the image are under the personal account `Wasi-cal`. Ask Calfus if it wants them under a company organisation instead (ADR 0025 says how to change the owner).
- [ ] **Merge to `main`.** Release from `main`, not from a working branch.
- [ ] **Check the name.** The name in `action.yml` is "Veil for Gozu Tickets". The name `Veil` is not possible, because a GitHub user named `veil` exists. GitHub checks the name again when you publish.

I scanned all 46 commits for token and key patterns. I found none. Scan again before you go public if more commits come in.

## 2. Accounts

- [ ] Two-factor authentication is on for the account `Wasi-cal`.
- [ ] You accept the GitHub Marketplace Developer Agreement. GitHub shows it when you draft the release. Until you accept, the publish box stays off.

## 3. Make the repo public

- [ ] Settings, General, Danger Zone, Change visibility, Public. A Marketplace Action must be in a public repo.

## 4. Publish the image

The workflow `.github/workflows/release-image.yml` runs when you push a version tag. It runs the tests, builds the image, pushes it to `ghcr.io/wasi-cal/veil`, and moves the tag `v1`.

- [ ] Push the tag `v1.0.0` from `main`.
- [ ] Wait for the run in the Actions tab. Read it. Both jobs must pass.
- [ ] **Make the package public.** GitHub makes a new package private. Go to your profile, Packages, `veil`, Package settings, Change visibility, Public. If you skip this step, every run of your users fails with an "unauthorized" error.
- [ ] Check it. From a machine that is not logged in to GitHub, run `docker pull ghcr.io/wasi-cal/veil:v1`.

## 5. Publish to the Marketplace

- [ ] Releases, Draft a new release.
- [ ] Choose the tag `v1.0.0`.
- [ ] Turn on "Publish this Action to the GitHub Marketplace".
- [ ] Choose a primary category, for example "Security" or "Code quality".
- [ ] Write a release title and a short note. Publish.

## 6. Check it from another repo

- [ ] In a test repo, use `Wasi-cal/veil@v1` as the README shows. Start it by hand. Read the run summary.
- [ ] Look at one Fix PR that the Action opened.

## Later releases

Push a new tag, for example `v1.0.1`. The workflow builds the image again and moves `v1`. Users of `@v1` get the new version at once. Draft a new Marketplace release only when you want a new listing entry.

A change that breaks a setting file needs a new major version, `v2`. The file `action.yml` then points at the image tag `v2`.

## About "nobody may take the code"

No setting can promise this. Know these facts:

- A Marketplace Action must be in a public repo. Everyone can read and fork it. GitHub's Terms of Service allow this, whatever the license says.
- The image must be public, or no runner can pull it. The image holds the Python source. Anyone can run `docker pull` and read it.
- `LICENSE` is the legal protection. It says "all rights reserved". It does not stop a person from copying. It gives you the right to act if someone does.

Two ways to go further:

1. **A thin public repo.** Keep this repo private. Make a second public repo that holds only `action.yml`, `README.md` and `LICENSE`. The Marketplace listing and the `uses:` line then use the public repo. The release workflow builds the image from the private repo. The image still holds the source.
2. **A compiled image.** Compile the Python code in the image, for example with Nuitka. This makes reading harder. It does not make it impossible. It adds build work and new places for bugs.

## Things that stay open

- The Docker image runs as root. GitHub needs this for the workspace of a Docker Action.
- The base images are pinned to a digest. A new digest is a change that a person reviews. Use Dependabot or Renovate to propose it.
- The actions in the release workflow are pinned to a commit. The same rule applies to a new commit.
- Only one real trial ran, on one repo with one ticket. A first run with real services can still find a problem.
