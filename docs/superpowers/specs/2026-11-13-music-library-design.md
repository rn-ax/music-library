# Music library design

This spec is the source of intent for the music library. Implementation works against its goals and acceptance checks, and a change of intent changes this document first. `DOMAIN.md` holds the domain rules and `AGENTS.md` holds the technical conventions, and this spec refers to them where they already say something.

## Intent

The household keeps its music as files on a TrueNAS dataset and listens through Plex and Plexamp. The library turns "I found a song online" into "it is in Plexamp with correct tags, at a predictable path" with as little manual work as the source allows, and keeps the files as the durable truth so every tool around them can be replaced.

It replaces the songbird app in monocoque. It stands on three jobs: acquiring audio from many sources the way MeTube does, keeping track of what is on disk and importing new files into it the way Radarr does for films, and reading and writing the tags that iTunes-style software reads.

The user is one person who adds music and a household that listens. Success is a pipeline the owner trusts enough to forget about: a URL goes in, the tags get a quick review, and the track shows up in Plexamp without losing anything that was already there.

## Goals

- **Acquire.** Audio from a URL, from any source yt-dlp supports, lands in an inbox as AAC in `.m4a` without re-encoding.
- **Review and file.** A person confirms or enters the metadata for what is in the inbox, and the file is tagged and filed into the library at the path its tags dictate.
- **Listen.** Plex serves the library, and a new file appears after its import completes. No avoidable path change costs an existing item its play counts, ratings or playlist places.
- **One standard.** The library holds only AAC and ALAC in `.m4a`, and the existing FLAC and MP3 files are converted into it.
- **Visibility.** A person can see what waits in the inbox and what the library holds, and a download is always in the inbox, in the library, or listed as failing.
- **Automatic delivery.** A merge to `main` builds the image and updates the TrueNAS app with no manual step.

## Non-goals

- **Wanted lists.** Following artists or playlists and fetching new music by itself is out of scope. This is the spec's own call, made because the pipeline is useful without it and Radarr's monitoring model is built around films with a canonical release, which music from YouTube lacks. It can be added later without changing the pipeline.
- **A player or a listening UI.** Plex and Plexamp are the listening side, and songbird's player is not carried over.
- **Songbird's data model.** Its track, recording and cover-link tables are not carried over. A cover or live version says so in its title.
- **Ratings and Spotify.** Rating a Spotify playlist stays in the separate Rater app.
- **Other formats in the library.** Anything that is not AAC or ALAC is converted before it enters.
- **Public exposure.** Nothing here is reachable from outside the household.

## Anti-goals

- A second database holding facts that the files or another service already hold, so it can drift from them.
- Plex reading a half-written or half-tagged file.
- Secrets in `compose.yaml`, in environment variables, or in the repository.
- Glue code that bends one component to another's vocabulary instead of translating at a named seam.

## Constraints

- The stack runs as a TrueNAS Custom App on an x86_64 host, with its config sent through the TrueNAS API. Containers run as the `apps` user.
- Plex identifies an item by path, so a rename after a scan resets that item's history.
- beets-flask only accepts `copy: yes` with `move: no`, and its `chroma` plugin is incompatible with it.
- MeTube gives nothing to rely on for completion, so new downloads are found by watching the inbox.
- The repository is private. CI runs on the self-hosted `contabo` runners, and its credentials are repository secrets because org secrets do not reach private repos on the org's plan.
- The inbox is the `metube` directory of the Downloads share and the library is the Music dataset. They are on different datasets, so filing a file is a copy and a delete.

## Approaches

**Platform.** Three ways to build it were weighed.
- A Windmill-based rewrite, which was the original idea, with Windmill orchestrating and owning the data model.
- A compose stack of existing tools with thin glue, chosen because beets provides a working import, tagging and filing model and what is left to write is glue.
- Lidarr, which fits Radarr's model but is organised around MusicBrainz albums and handles YouTube singles, covers and live versions poorly.

The chosen approach keeps Windmill as an optional hook for notifications and similar glue. A table app of the library built in Windmill exists as unmerged local work and is not part of the stack.

**Engine.** Our own mover was weighed against beets. Beets is chosen for its model, its plugins and its MusicBrainz matching, with beets-flask as the review interface. beets-flask is open source and is forked if it falls short.

**Packaging.** One image holding MeTube, beets and the watcher was weighed against a compose project of upstream images. The compose project is chosen: MeTube and beets-flask stay upstream and updatable, and our image holds beets and the glue.

**Tag writer.** Either beets is the only writer and edits go through it, or the files are the truth and any tool edits them followed by `beet update`. The first is the default, and the second stays available for desktop tag editors. `AGENTS.md` holds the rules.

**Image tag.** A pinned version from CI was weighed against `latest`. `latest` is chosen, with a pull before each redeploy, and CI also tags each build with its CalVer version so a rollback is possible.

**Environments.** There is one deployment, so `compose.yaml` holds its values directly.

## Decisions

These are settled and recorded where they belong.
- The component contexts and the words that differ between them are in `DOMAIN.md`.
- The path layout is `Artist/Album (Year)/NN Title`, with a disc prefix on multi-disc albums, `Compilations/` for compilations, and singles directly under the artist.
- The formats are AAC and ALAC. Lossy sources are taken as their own stream and lossless sources become ALAC.
- Plex scans only on an explicit trigger after an import, with its automatic scanning off.
- Secrets live in 1Password and reach containers as read-only files under `Configuration/music-library/secrets`.
- The conventions for MeTube, beets, beets-flask, TrueNAS and CI are in `AGENTS.md`.

## Open questions

Each question says what settles it. Until it is settled the stated default applies.

- **Singles in Plex.** How Plex presents a track with no album tag. Settled by importing an existing single and looking at it. Default if it shows an invented album: tag each single's album with its title and keep the folder layout.
- **Editing existing files in beets-flask.** Whether it can edit tags of files already in the library, and how it cleans the copy left in the inbox. Settled by trying it on a real download. If it cannot, the options are a fork of beets-flask or a small form in this repository that calls beets.
- **Autotag value.** How often MusicBrainz matches downloads from YouTube. Settled by previewing real downloads. Default: manual entry is the normal path and a match is a convenience.
- **Source URL as a tag.** Whether a beets plugin or the glue writes it into the file. Settled when the first import runs. Default: written into a real tag the file can hold.
- **Inbox trigger.** Whether beets-flask's own watching is enough or the pipeline needs a watcher of its own. Settled by the first week of use.
- **MeTube settings.** How to make `m4a` and metadata embedding the default instead of a per-download choice, probably with a `YTDL_OPTIONS_PRESETS` preset, and whether yt-dlp remuxes AAC without re-encoding. Settled by inspecting downloaded files.
- **YouTube cookies.** Whether to supply cookies for higher-quality audio. Default: not until quality is a problem.
- **Existing library.** Converting the FLAC and MP3 files and renaming everything to the new layout resets each item's Plex history. Settled by deciding whether to accept the reset or to read the ratings through Plex's API before the rename and write them back after.
- **Plex scan.** Whether the `plexupdate` plugin or a direct API call triggers the scan, and where its token lives.
- **Private image access.** How TrueNAS pulls the private ghcr image: stored registry credentials or a public package. Default: stored credentials.
- **Songbird.** What, if anything, to carry over from it, and when to remove the monocoque app. The parked Windmill table app is either committed as its own change or discarded.
- **Failure notice.** Whether an import that fails sends a notification. Default: it appears in the review interface only.

## Acceptance

These checks are what implementation is measured against.

- A URL submitted in MeTube produces `<inbox>/<video id>/<title>.m4a` and an info JSON, and `ffprobe` reports the audio codec as `aac`.
- Submitting the same video again downloads nothing.
- A folder in the inbox appears in beets-flask for review, and after confirmation the file sits at the path its tags dictate with exactly the confirmed tags, still in its original codec.
- Plex lists the new track under the right artist and album after the scan, and never lists a file that is still being written.
- A FLAC placed in the inbox ends up in the library as ALAC with its tags intact.
- The review interface shows every folder waiting in the inbox and every item in the library, and an import that fails is listed there.
- A listing of the library finds no file that is not `.m4a` and no file whose codec is neither `aac` nor `alac`.
- Deleting the beets database and re-reading the library reproduces the same set of items.
- Adding files to the library changes no existing item's path and no existing item's Plex history.
- A merge to `main` publishes the image, and the running container on TrueNAS uses the new image digest after the next deploy.
- `compose.yaml` and the environment of every container contain no secret value, and the secrets directory has mode 700 with files at mode 600.
- Every file and directory in the library is owned by `apps:apps` or grants it access.

## What is left to the builder

- The order of work, which follows the open questions: the first real download through the whole pipeline answers most of them.
- The shape and size of the glue code, which is only what the first real run shows to be missing.
- How the checks above are run, as scripts in this repository or as manual steps.
- The CI deploy job that sends `compose.yaml` to TrueNAS, with its own TrueNAS API key stored as a repository secret.
- The access setup on TrueNAS that the first deploy needs: a snapshot of the Music dataset, the directories and their ownership, and the registry credentials.
