# Music library

A self-hosted music library pipeline feeding Plex. The rules it keeps are the acceptance criteria in `spec/`.

## Development method

- Samuel and an agent write the acceptance criteria together, and agents implement everything after them: code, tests, CI, merging, deployment and rollback.
- No human reviews code or pull requests. A pull request merges when its CI run passes, and the criteria and CI are what keep a change safe.
- Criteria are written and approved before the code that satisfies them.
- Each functionality has its own file, `spec/<functionality>.md`, with a `# Context` section above a `# Criteria` list of `- AC-<n>: <rule>` lines. `spec/general.md` holds what is not large enough for a file of its own.
- A criterion is never edited. A rule that changes is deleted and added again under a new number, and a deleted number is never reused.
- A test checks exactly one criterion and carries its `[AC-<n>]` in its title. A criterion can have several tests.
- The meaning of the library's concepts is written in the `# Context` of the spec files, and the invariants are criteria.

## Stack

- The stack is a Docker Compose project with three services: `metube` (the upstream MeTube image, downloading audio into the inbox), `music` (this repo's image, running beets and the glue code) and `beets-flask` (the upstream beets-flask web UI, for reviewing and importing inbox folders).
- The image is Python 3.14 managed with `uv`, with `ffmpeg` and `fpcalc` (chromaprint) installed alongside beets.
- Dependencies are pinned in `pyproject.toml` and locked in `uv.lock`. Renovate keeps the image tags, base images and Python packages current.
- `compose.yaml` is the whole deployment: its host paths, ports and user ids are written into it directly, and the file is sent to TrueNAS unchanged.
- `mise run check` validates the compose file.

## TrueNAS Custom App

- The deployed app is a TrueNAS Custom App whose config is `compose.yaml`: `app.create` with `custom_app: true` and `custom_compose_config_string` installs it, and `app.update` with a new `custom_compose_config_string` changes it.
- `app.update` leaves running containers as they are, so it is followed by `app.redeploy` to apply the new config.
- The `music` service runs the `latest` tag, so a deploy first calls `app.pull_images` to fetch the newest build and then `app.redeploy`.
- A redeploy restarts every container in the app.
- Containers run as the `apps` user (568:568). Every host path in the compose file is a ZFS dataset or a directory in one, owned by `apps:apps` and created before the app starts, because a bind mount of a missing path is created by Docker as root.
- The beets and beets-flask databases and MeTube's state live under `/mnt/Storage/Configuration/music-library`.
- The TrueNAS host is x86_64. Images are built for `linux/amd64`.

## Inbox and library

- The inbox is `metube` inside the Downloads share, which keeps this stack's downloads apart from what other apps put there.
- The library is `/mnt/Storage/Music`. It is a different dataset from the inbox, so putting a file into the library is a copy followed by a delete.
- The `music` service moves finished files from the inbox into the library with `beet import --move`.

## MeTube

- `OUTPUT_TEMPLATE` is `%(id)s/%(title)s.%(ext)s`, so each download lands in a subfolder named after its video id.
- `YTDL_OPTIONS` writes yt-dlp's info JSON next to each download and keeps a download archive in MeTube's state directory.
- The audio format (`m4a`) is chosen per download in MeTube's web UI.

## beets

- `beets/config.yaml` is baked into the image at `/etc/beets/config.yaml`, and every `beet` call passes it with `-c`. Changing beets configuration means building a new image.
- The beets database and state file live in the `music` service's `/data` volume.
- The config sets `copy`, `move` and `write` to `no`, so an import changes nothing on disk until the run passes `--move` and `--write`.
- The `musicbrainz` plugin is listed explicitly, because beets only matches against MusicBrainz when it is enabled.
- `beet import --set FIELD=VALUE` sets a field on every imported item.

## beets-flask

- The `beets-flask` image is the upstream image pinned to a release. It bundles its own beets and keeps its own database in `/mnt/Storage/Configuration/music-library/beets-flask`.
- It reads two files from its `/config` volume: `beets/config.yaml` (the beets configuration) and `beets-flask/config.yaml` (inboxes and terminal settings). The container generates defaults when they are missing, and a restart applies a change.
- `beets-flask/beets.yaml` and `beets-flask/config.yaml` in this repo are the seeds for those two files, copied into place before the first start.
- The container sees the library at `/music` and the inbox at `/inbox`.
- An inbox in `auto` mode imports good matches without review, and `preview` mode waits for a person.
- Its config schema accepts only `import.copy: yes` with `import.move: no`.
- The `chroma` plugin is incompatible with it, so its beets configuration omits `chroma`.

## Delivery

- The delivery rules (automatic merge and deploy, a backup before every deploy, rollback) belong to the development method and are not repeated in `spec/`. These are the repo's own facts for them.
- The stack has three SQLite databases to back up: the beets database in `/mnt/Storage/Configuration/music-library/beets`, the beets-flask beets database and the beets-flask application database, both in `/mnt/Storage/Configuration/music-library/beets-flask`. MeTube's download archive is a text file in its state directory and is copied with them.
- A backup is made with the SQLite backup command, run in the container that owns the database, and its name ends in a UTC timestamp.
- Rolling back runs the previous image version against the restored databases. The library files are untouched, because the databases are caches that can be rebuilt from them.
- A deploy sends `compose.yaml` to TrueNAS through its API using a key of its own, stored as a repository secret.

## CI and images

- CI runs on the self-hosted `contabo` runners, which are registered for this repository.
- Every `uses:` reference is pinned to a full commit SHA with a trailing comment naming the tag, for example `actions/checkout@<sha> # v7.0.1`. Renovate keeps the pins current.
- The version is computed by the shared CalVer action in poppycock.
- Org-level secrets do not reach private repositories on the org's plan, so a credential CI needs is a repository secret.

## Documentation

- `spec/` holds the acceptance criteria and the meaning of the library's concepts, and this file holds the facts and constraints specific to the repo.
- The reasons for a choice and the approaches that were rejected are in the pull request that made it.
- Paragraphs are written as one line each and left to the renderer to wrap.
