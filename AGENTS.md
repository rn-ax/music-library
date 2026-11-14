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

- The stack has three SQLite databases to back up: the beets database in `/mnt/Storage/Configuration/music-library/beets`, and the beets-flask beets database and the beets-flask application database, both in `/mnt/Storage/Configuration/music-library/beets-flask`. MeTube's download archive is a text file in its state directory and is copied with them.
- The databases cache what the library files say, so a rollback leaves the files as they are.
- A deploy sends `compose.yaml` to TrueNAS through its API using a key of its own, stored as a repository secret.

## CI and images

- CI runs on the self-hosted `contabo` runners, which are registered for this repository.
- Each job writes its Docker config to its own temp directory, because a stale registry login in a runner's shared config makes even a public `ghcr.io` pull fail.
- Every `uses:` reference is pinned to a full commit SHA with a trailing comment naming the tag, and Renovate keeps the pins current.
- Org-level secrets do not reach private repositories on the org's plan, so a credential CI needs is a repository secret.
