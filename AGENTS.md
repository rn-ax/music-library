# Music library

A self-hosted music library pipeline feeding Plex. The rules it keeps are the acceptance criteria in `spec/`.

## Development method

- No human reviews code or pull requests. A pull request merges when its CI run passes.
- The acceptance criteria are in `spec/`, and each test carries the `[AC-<n>]` it checks.

## TrueNAS Custom App

- `app.update` with a new compose config leaves running containers as they are, so it is followed by `app.redeploy`, which restarts every container in the app.
- The `music` service runs the `latest` tag, so a deploy first calls `app.pull_images`.
- A bind mount of a missing path is created by Docker as root, so every host path exists and is owned by `apps:apps` (568:568, the user the containers run as) before the app starts.
- The TrueNAS host is x86_64, so images are built for `linux/amd64`.
- The inbox (`metube` in the Downloads share) and the library (the Music dataset) are different datasets, so filing a file is a copy followed by a delete.
- MeTube's global `YTDL_OPTIONS` ask for `m4a` audio, which overrides the type and format chosen in its web UI.

## Delivery

- `scripts/deploy.py` deploys `compose.yaml` through the TrueNAS API. The CI `deploy` job runs it for the head commit of `main` with a key of its own (`TRUENAS_API_KEY`, a repository secret, with the `TRUENAS_URL` and `TRUENAS_USERNAME` variables).
- Before anything changes it takes a snapshot of `Storage/Configuration/music-library`, named `deploy-<UTC timestamp>`. That dataset holds the three SQLite databases (the beets database, and the beets-flask beets and application databases) and MeTube's download archive. The deploy stops when the snapshot fails, and the newest ten are kept.
- It sends the compose file with this repo's two images pinned to the build's CalVer version, so a config that was deployed names the version to return to.
- The deploy is healthy when all three services run and each answers HTTP 200 on its port. When that does not hold within five minutes, it stops the app, rolls the dataset back to the snapshot, applies the previous config and redeploys.
- The databases cache what the library files say, so a rollback leaves the files as they are.
- The first deploy after a config that used `latest` has no earlier version to return to, so a rollback then redeploys `latest`.
- A private-registry pull goes through the `GHCR rn-ax` credential stored in TrueNAS. `app.image.pull` does not use it on its own, so the script passes it explicitly.

## CI and images

- CI runs on every push to a branch. Its jobs run on the self-hosted `contabo` runners, which are registered for this repository.
- A branch whose checks passed is merged by the `merge` job, using the shared `merge-pr` action, which also starts CI on `main` because a merge made with `GITHUB_TOKEN` starts no workflows.
- A run on `main` publishes both images and then deploys, and the deploy runs only when the run's commit is still the head of `main`.
- Each job writes its Docker config to its own temp directory, because a stale registry login in a runner's shared config makes even a public `ghcr.io` pull fail.
- Every `uses:` reference to a third party is pinned to a full commit SHA with a trailing comment naming the tag, and Renovate keeps the pins current. References to `rn-ax/poppycock` actions follow `main`.
- Org-level secrets do not reach private repositories on the org's plan, so a credential CI needs is a repository secret.
