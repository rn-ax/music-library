# music-library

A self-hosted music library pipeline feeding Plex.

## Setup

1. Create the host directories the compose file mounts that do not exist yet (`/mnt/Storage/Downloads/metube`, and `/mnt/Storage/Configuration/music-library` with `metube`, `beets`, `beets-flask/beets` and `beets-flask/beets-flask` inside it), owned by `apps:apps`.
2. Copy `beets-flask/beets.yaml` to `/mnt/Storage/Configuration/music-library/beets-flask/beets/config.yaml` and `beets-flask/config.yaml` to `/mnt/Storage/Configuration/music-library/beets-flask/beets-flask/config.yaml`.
3. Install `compose.yaml` as the app's compose config.

## Tests

`mise run check` validates the compose file.
