# music-library

A self-hosted music library pipeline feeding Plex.

Downloads from [MeTube](https://github.com/alexta69/metube) land in an inbox. [beets](https://beets.io) tags them, files them into the library by their metadata, and Plex serves the finished library to Plexamp.

## Layout

- `compose.yaml` is the source of truth for the deployed stack.
- `Dockerfile` and `pyproject.toml` build the image that runs beets and the glue code around it.
- `beets/config.yaml` is the beets configuration baked into that image.
- `beets-flask/` holds the seed configuration for the beets-flask service.
- `DOMAIN.md` records what the library holds and the rules it keeps.
- `AGENTS.md` records the technical conventions.

## Checks

`mise run check` validates the compose file.

`docker build --platform linux/amd64 .` builds the image.

## Setting up a deployment

1. Create the host directories the compose file mounts that do not exist yet (`/mnt/Storage/Downloads/metube`, and `/mnt/Storage/Configuration/music-library` with `metube`, `beets`, `beets-flask/beets` and `beets-flask/beets-flask` inside it), owned by `apps:apps`.
2. Copy `beets-flask/beets.yaml` to `/mnt/Storage/Configuration/music-library/beets-flask/beets/config.yaml` and `beets-flask/config.yaml` to `/mnt/Storage/Configuration/music-library/beets-flask/beets-flask/config.yaml`.
3. Install `compose.yaml` as the app's compose config.
