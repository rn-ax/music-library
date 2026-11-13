---
type: Functionality
title: Plex
description: How Plex reads the library: scanning only after an import completes, keeping play counts and ratings, and showing new tracks under the right artist and album.
tags: [plex, plexamp, scan, library, play-count, rating, playlist, path, history]
---

# Context

Plex reads the library and never changes it. It derives artists, albums and tracks from the files' tags and paths and keeps what only it can know: play counts, ratings and playlists. It identifies an item by its path, so a file moved or renamed after a scan appears as a new item and loses that history.

A file reaches the library only when its tags are final and its path is the one beets computed from them. Putting a file into the library is a copy followed by a delete, because the inbox and the library are on different datasets, so the library can briefly hold a partly written file. Plex's automatic scanning is therefore off and a scan is requested after an import completes.

How Plex presents a track that has no album tag has not been established.

# Criteria

- AC-26: Plex's automatic scanning of the Music library is off.
- AC-27: A Plex scan is requested after an import completes and never while an import is running.
- AC-28: An import changes the path of no file that was already in the library.
- AC-29: An import leaves the play count, rating and playlist membership of every existing item in Plex unchanged.
- AC-30: After the scan that follows an import, Plex lists each imported track under its artist and album.
