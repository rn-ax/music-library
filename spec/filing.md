---
type: Functionality
title: Filing
description: Reviewing what is in the inbox, entering or confirming tags, importing with beets and beets-flask, and filing each file at the path its tags dictate, including albums, compilations and singles.
tags: [beets, beets-flask, import, tags, metadata, review, musicbrainz, path, album, compilation, single, singleton, inbox]
---

# Context

A person confirms or enters the metadata for what arrives in the inbox. Most downloads come from YouTube, where titles, uploaders and thumbnails are not a reliable source of tags, and covers, live versions and remixes often have no MusicBrainz match. Automatic matching only suggests tags, and typing them by hand is a normal path.

Beets-flask is the review interface. Its inbox is the same directory MeTube writes into, each subfolder of it is one import session, and in preview mode it fetches candidate matches and waits for a person to import. It runs its own installation of beets with its own database, and it only accepts copying, so the original stays in the inbox after an import. The `chroma` plugin is incompatible with it. Both installations of beets write to the same library, so one import tool is used at a time against the same inbox.

A track is part of an album, part of a compilation, or a single. An album track is filed under its album artist and album, a compilation track under `Compilations` with its own artist in the file name, and a single directly under its artist with no album folder. A single has no album to tell versions apart, so a live version, remix or cover says so in its title.

Beets is the one writer of tags in the library. A tag changes through an import or `beet modify`, so its database and the file agree. A tool that edits a file's tags directly is followed by `beet update`. A tag change that alters a file's path is a rename, and Plex treats the renamed file as a new item.

A value that has to survive in the file, such as the source URL, is written to a tag the file can hold, because fields that exist only in the beets database are invisible to tools that read the file.

# Criteria

- AC-35: Every folder directly inside the inbox, other than hidden ones, appears in beets-flask for review within 60 seconds of its last file change.
- AC-11: Importing a reviewed folder writes exactly the confirmed tags into the imported file.
- AC-12: An imported AAC or ALAC file keeps its audio stream unchanged.
- AC-13: An imported album track is filed at `<Album Artist>/<Album> (<Year>)/<NN> <Title>.m4a`.
- AC-14: An imported track of a multi-disc album is filed as `<DD>-<NN> <Title>.m4a`, with the disc number before the track number.
- AC-15: An imported compilation track is filed at `Compilations/<Album> (<Year>)/<NN> <Artist> - <Title>.m4a`.
- AC-16: An imported single is filed at `<Artist>/<Title>.m4a`.
- AC-17: Running `beet import` with the music service's configuration and no flags changes no file.
- AC-18: After a tag in a library file is changed directly, `beet update` makes the beets database report the new value.
- AC-19: The source URL of a download is stored in a tag of the imported file.
- AC-20: An import that fails is listed with its error in the review interface.
- AC-21: After an import, the inbox holds no file of the imported folder.
