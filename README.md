# music-library

A self-hosted music library pipeline feeding Plex.

Downloads from [MeTube](https://github.com/alexta69/metube) land in an inbox. [beets](https://beets.io) tags them, files them into the library by their metadata, and Plex serves the finished library to Plexamp.

## Layout

- `compose.yaml` is the source of truth for the deployed stack, parameterized by an env file.
- `env/<name>.env` holds the host paths, ports and user ids for one deployment of the stack.
- `Dockerfile` and `pyproject.toml` build the image that runs beets and the glue code around it.
- `beets/config.yaml` is the beets configuration baked into that image.
- `beets-flask/` holds the seed configuration for the beets-flask service.
- `DOMAIN.md` records what the library holds and the rules it keeps.
- `AGENTS.md` records the technical conventions.

## Checks

`mise run check` renders the compose file against every env file.

`docker build --platform linux/amd64 .` builds the image.

## Rendering the stack

`docker compose --env-file env/<name>.env config` prints the fully resolved compose file for a deployment.

## Setting up a deployment

1. Create the host directories named in the env file (`MUSIC_DIR`, `INBOX_DIR`, and `DATA_DIR` with `metube`, `beets`, `beets-flask/beets` and `beets-flask/beets-flask` inside it), owned by `PUID:PGID`.
2. Copy `beets-flask/beets.yaml` to `$DATA_DIR/beets-flask/beets/config.yaml` and `beets-flask/config.yaml` to `$DATA_DIR/beets-flask/beets-flask/config.yaml`.
3. Render the compose file with the env file and install it as the app's compose config.
