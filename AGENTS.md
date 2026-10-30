# Music library

A self-hosted music library pipeline feeding Plex. `DOMAIN.md` describes what the library holds and the rules it keeps.

## Stack

- The stack is a Docker Compose project with two services: `metube` (the upstream MeTube image, downloading audio into the inbox) and `music` (this repo's image, running beets and the glue code).
- The image is Python 3.14 managed with `uv`, with `ffmpeg` and `fpcalc` (chromaprint) installed alongside beets.
- Dependencies are pinned in `pyproject.toml` and locked in `uv.lock`. Renovate keeps the image tags, base images and Python packages current.

## Compose and env files

- `compose.yaml` holds no host-specific values. Every host path, port and user id is a `${VARIABLE}` resolved from `env/<name>.env`.
- One env file describes one deployment. `docker compose --env-file env/<name>.env config` renders the stack with everything resolved, and that rendered YAML is what a TrueNAS Custom App receives as its compose config.
- An env file can build one variable from another (`INBOX_DIR=${MUSIC_DIR}/_inbox`).
- `mise run check` renders the compose file against every env file, so a missing variable fails the check.

## TrueNAS Custom App

- The deployed app is a TrueNAS Custom App whose config is the rendered compose YAML: `app.create` with `custom_app: true` and `custom_compose_config_string` installs it, and `app.update` with a new `custom_compose_config_string` changes it.
- `app.update` leaves running containers as they are, so it is followed by `app.redeploy` to apply the new config.
- A redeploy restarts every container in the app.
- Containers run as the `apps` user (568:568). Every host path in an env file is a ZFS dataset or a directory in one, owned by `apps:apps` and created before the app starts, because a bind mount of a missing path is created by Docker as root.
- The TrueNAS host is x86_64. Images are built for `linux/amd64`.

## Inbox and library

- MeTube writes into the inbox, and beets moves finished files from the inbox into the library. Both sit on the same filesystem, so a move is a rename and a reader never sees a half-written file.
- The library holds only finished files. Plex scans the library, so a file reaches it only after its tags are final and its path is the one beets computed from them.
- Plex tracks items by path. Moving or renaming a file after Plex has scanned it makes Plex see a new item and lose its play counts, ratings and playlist membership.

## beets

- `beets/config.yaml` is baked into the image at `/etc/beets/config.yaml`, and every `beet` call passes it with `-c`. Changing beets configuration means building a new image.
- The beets database and state file live in the `music` service's `/data` volume.
- The config sets `copy`, `move` and `write` to `no`, so an import changes nothing on disk until the run passes `--move` and `--write`.
- Path templates reproduce the library's existing layout: `Artist/Album (Year)/Artist - Album - NN - Title`, with singles directly under the artist folder.
- `beet import --set FIELD=VALUE` sets a field on every imported item, which is how provenance can be stamped during an import.

## Audio formats

- The library holds AAC and ALAC, both in `.m4a`. Both are tagged with MP4 atoms.
- AAC comes from lossy sources as the source's own stream without re-encoding. ALAC comes from lossless sources.
- Other audio is converted to one of the two before it enters the library.

## CI and images

- CI runs on the self-hosted `contabo` runners.
- Every `uses:` reference is pinned to a full commit SHA with a trailing comment naming the tag, for example `actions/checkout@<sha> # v7.0.1`. Renovate keeps the pins current.
- A push to `main` builds the image and pushes it to `ghcr.io/rn-ax/music-library` tagged with a CalVer version, `YYYY.MM.DD.<run number>`.
- Org-level secrets do not reach private repositories on the org's plan, so a credential CI needs is a repository secret.

## Documentation

- `AGENTS.md` holds technical conventions and `DOMAIN.md` holds the domain rules. Each stays within its own concern.
- Paragraphs are written as one line each and left to the renderer to wrap.
