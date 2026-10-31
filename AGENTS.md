# Music library

A self-hosted music library pipeline feeding Plex. `DOMAIN.md` describes what the library holds and the rules it keeps.

## Stack

- The stack is a Docker Compose project with three services: `metube` (the upstream MeTube image, downloading audio into the inbox), `music` (this repo's image, running beets and the glue code) and `beets-flask` (the upstream beets-flask web UI, for reviewing and importing inbox folders).
- The image is Python 3.14 managed with `uv`, with `ffmpeg` and `fpcalc` (chromaprint) installed alongside beets.
- Dependencies are pinned in `pyproject.toml` and locked in `uv.lock`. Renovate keeps the image tags, base images and Python packages current.

## Component boundaries

- Each component is operated through its own documented interface: MeTube through its environment and `YTDL_OPTIONS`, beets through its YAML configuration, CLI and plugins, beets-flask through its two configuration files, and Plex through its API.
- A component's private store is written only by that component. Other components read files or call its interface.
- Components meet at the filesystem (the inbox and the library) and at the tags in the files, and they share no databases.
- Translation between one component's vocabulary and another's lives in this repo, in one place per seam, so a change in a component's behaviour changes one place. `DOMAIN.md` names the contexts and the seams.

## Compose file

- `compose.yaml` is the whole deployment: its host paths, ports and user ids are written into it directly, and the file is sent to TrueNAS unchanged.
- `mise run check` validates the compose file.

## TrueNAS Custom App

- The deployed app is a TrueNAS Custom App whose config is `compose.yaml`: `app.create` with `custom_app: true` and `custom_compose_config_string` installs it, and `app.update` with a new `custom_compose_config_string` changes it.
- `app.update` leaves running containers as they are, so it is followed by `app.redeploy` to apply the new config.
- The `music` service runs the `latest` tag, so a deploy first calls `app.pull_images` to fetch the newest build and then `app.redeploy`.
- A redeploy restarts every container in the app.
- Containers run as the `apps` user (568:568). Every host path in the compose file is a ZFS dataset or a directory in one, owned by `apps:apps` and created before the app starts, because a bind mount of a missing path is created by Docker as root.
- Library files and directories are owned by `apps:apps`, or carry an ACL granting it access, so the containers running as 568 can read and write them. A file owned by another user is unreadable until its ownership is fixed.
- The beets and beets-flask databases and MeTube's download archive live under `/mnt/Storage/Configuration/music-library`. The beets databases can be rebuilt from the files.
- The TrueNAS host is x86_64. Images are built for `linux/amd64`.

## Inbox and library

- MeTube writes into the inbox, one subfolder per download (`OUTPUT_TEMPLATE` is `%(id)s/%(title)s.%(ext)s`), and a subfolder is the unit that gets imported.
- The `music` service moves finished files from the inbox into the library with `beet import --move`.
- The inbox is a directory of its own, `metube` inside the Downloads share, which keeps this stack's downloads apart from what other apps put there.
- The inbox and the library are on different datasets, so putting a file into the library is a copy followed by a delete, and the library can briefly hold a partly written file.
- Plex's automatic scanning of the Music library is off, and the pipeline asks Plex to scan after an import completes, so Plex never reads a partly written file.
- The library holds only finished files. Plex scans the library, so a file reaches it only after its tags are final and its path is the one beets computed from them.
- Plex tracks items by path. Moving or renaming a file after Plex has scanned it makes Plex see a new item and lose its play counts, ratings and playlist membership.

## MeTube

- MeTube downloads audio into the inbox, and the audio format (`m4a`) is chosen per download in its web UI.
- `OUTPUT_TEMPLATE` is `%(id)s/%(title)s.%(ext)s`, so each download lands in a subfolder named after its video id.
- `YTDL_OPTIONS` writes yt-dlp's info JSON next to each download, which carries the source URL and uploader for prefilling tags, and keeps a download archive in MeTube's state directory so a video is fetched once.
- Nothing in this stack depends on a MeTube completion event. New downloads are found by looking at the inbox.

## beets

- `beets/config.yaml` is baked into the image at `/etc/beets/config.yaml`, and every `beet` call passes it with `-c`. Changing beets configuration means building a new image.
- The beets database and state file live in the `music` service's `/data` volume.
- The config sets `copy`, `move` and `write` to `no`, so an import changes nothing on disk until the run passes `--move` and `--write`.
- Path templates produce `Artist/Album (Year)/NN Title`, with a disc prefix on multi-disc albums, `Compilations/Album (Year)/NN Artist - Title` for compilations, and singles directly under the artist folder.
- The `musicbrainz` plugin is listed explicitly, because beets only matches against MusicBrainz when it is enabled.
- `beet import --set FIELD=VALUE` sets a field on every imported item, which is how provenance can be stamped during an import.

## beets-flask

- The `beets-flask` image is the upstream image pinned to a release. It bundles its own beets and keeps its own database in `${DATA_DIR}/beets-flask`, separate from the `music` service's database.
- It reads two files from its `/config` volume: `beets/config.yaml` (the beets configuration) and `beets-flask/config.yaml` (inboxes and terminal settings). The container generates defaults when they are missing, and a restart applies a change.
- `beets-flask/beets.yaml` and `beets-flask/config.yaml` in this repo are the seeds for those two files, copied into place before the first start.
- The container sees the library at `/music` and the inbox at `/inbox`.
- Its inbox in `preview` mode fetches candidate matches and waits for a person to review them. `auto` mode imports good matches without review.
- Its config schema accepts only `import.copy: yes` with `import.move: no`, so it copies from the inbox into the library and leaves the original in the inbox.
- The `chroma` plugin is incompatible with it, so its beets configuration omits `chroma`.
- Both beets installations write to the same library. Run one import tool at a time against the same inbox.

## Tag changes

- beets is the one writer of tags in the library. A tag change goes through beets (`beet modify`, or an import), so its database and the file agree.
- A tool that edits tags in the file directly is followed by `beet update`, which reads the files back into the beets database.
- Beets writes tags only on an explicit import or modify, because `write` is `no` in the configuration.
- A tag change that alters a file's path is a deliberate rename, because Plex treats the renamed file as a new item.
- Fields that exist only in the beets database, such as flexible attributes, are invisible to tools that read the file. A value that has to survive in the file, such as the source URL, is written to a tag the file can hold.

## Audio formats

- The library holds AAC and ALAC, both in `.m4a`. Both are tagged with MP4 atoms.
- AAC comes from lossy sources as the source's own stream without re-encoding. ALAC comes from lossless sources.
- Other audio is converted to one of the two before it enters the library.

## Secrets

- Secrets live in 1Password and reach containers as read-only files mounted from `/mnt/Storage/Configuration/music-library/secrets`, a directory with mode 700 whose files have mode 600, owned by `apps:apps`.
- A secret is never an environment variable or a value in `compose.yaml`, because those are visible in `docker inspect`, in the TrueNAS app config and in the compose config sent through the API.
- The secret files are populated from 1Password and not edited by hand on the NAS. A container reads its file at start, so rotating a secret means rewriting its file and restarting the container that reads it.
- A credential CI needs is a repository secret.

## CI and images

- CI runs on the self-hosted `contabo` runners, which are registered for this repository.
- Every `uses:` reference is pinned to a full commit SHA with a trailing comment naming the tag, for example `actions/checkout@<sha> # v7.0.1`. Renovate keeps the pins current.
- A push to `main` builds the image and pushes it to `ghcr.io/rn-ax/music-library` tagged `latest` and with a CalVer version, `YYYY.MM.DD.<run number>`, which keeps every build available by version.
- Org-level secrets do not reach private repositories on the org's plan, so a credential CI needs is a repository secret.

## Documentation

- `AGENTS.md` holds technical conventions and `DOMAIN.md` holds the domain rules. Each stays within its own concern.
- Paragraphs are written as one line each and left to the renderer to wrap.
