---
type: Functionality
title: General
description: What the music library is for, what is out of scope, where each component's responsibility ends, the words that mean different things in different components, and how secrets are kept.
tags: [music-library, scope, non-goals, components, vocabulary, state, files, secrets, 1password]
---

# Context

The household's music is files on a TrueNAS dataset, served by Plex to Plexamp. The library turns a URL into a tagged file at a predictable path and keeps the files as the durable truth, so every tool around them can be replaced. One person adds music and the household listens. It replaces the songbird app in monocoque.

Out of scope are following artists or playlists to fetch new music by itself, a player or listening interface (Plex and Plexamp are the listening side), songbird's track, recording and cover-link data model, rating Spotify playlists (a separate app), and any exposure outside the household.

Everything that matters about a track is stored in its file: title, artist, album, year, track number, disc number, cover art and where it was downloaded from are all tags. Tools that keep a database of their own, such as beets, treat it as a cache that can be rebuilt by reading the files again. A fact is kept in a database only when no file or service already holds it.

The stack is built from components that each have their own model of music, used on their own terms. Acquisition (MeTube and yt-dlp) knows videos, not songs, and its identity is the video id. Cataloguing (beets) knows tagged audio files, owns the tags and the path each file is filed at, and keeps a database that caches what the files say. Review (beets-flask) is a web interface around its own installation of beets with its own database. Listening (Plex and Plexamp) derives artists, albums and tracks from tags and paths, identifies an item by its path, and keeps play counts, ratings and playlists that exist nowhere else. Storage (TrueNAS) decides who can read and write each directory. Each component's private store is written only by that component, and the components meet at the filesystem and the tags in the files.

Words that differ between components:
- **Library** is the files in the Music dataset in this spec. A beets library is its database together with that directory, and a Plex library is a section pointing at a directory.
- **Track** is a file with tags. Beets calls it an item.
- **Title** is the song's title tag in beets and Plex, and the video's title in MeTube.
- **Artist** is the performer tag in beets and Plex, and the uploader's name in MeTube, which often is not the performer.
- **Single** is a track filed with no album. Beets calls it a singleton.
- **Import** is beets moving or copying a folder into the library. Plex's counterpart is a scan, which reads the library without changing it.
- **Inbox** is the directory MeTube writes into and beets and beets-flask import from.

Secrets live in 1Password and reach containers as files, because environment variables and compose values are visible in `docker inspect`, in the TrueNAS app config and in the config sent through the API. The files are populated from 1Password and not edited by hand on the NAS. A container reads its file at start, so rotating a secret means rewriting the file and restarting that container.

# Criteria

- AC-1: Deleting the beets database and re-importing the library with `beet import -A -C -W` produces the same items with the same tags.
- AC-2: No value stored in 1Password for this stack appears in `compose.yaml`, in any container's environment, or in the repository.
- AC-3: The directory `/mnt/Storage/Configuration/music-library/secrets` has mode 700, its files have mode 600, all are owned by `apps:apps`, and every container mounts them read-only.
- AC-4: Every host path that `compose.yaml` mounts into more than one service is the inbox or the library.
