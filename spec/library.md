---
type: Functionality
title: Library
description: What the music library holds on disk: AAC and ALAC in m4a only, conversion of other formats, file ownership, and that the review interface shows exactly what is there.
tags: [library, m4a, aac, alac, flac, mp3, conversion, ownership, apps, permissions, truenas]
---

# Context

The library is the files in the `Music` dataset of the Storage pool. It holds two formats, AAC and ALAC, both in `.m4a` and both tagged with MP4 atoms. AAC is a lossy source's own stream and ALAC is what a lossless source becomes. The format is read from the stream and never from the file name, because the two share an extension.

Audio in any other format is converted to AAC or ALAC before it enters the library. The existing FLAC, MP3 and WebM files are converted into the library's formats.

The containers run as the `apps` user (568), so every library file and directory is owned by `apps:apps` or grants it access. A file owned by another user is unreadable to the stack until its ownership is fixed.

# Criteria

- AC-22: Every audio file in the library is an `.m4a` whose audio codec is `aac` or `alac`.
- AC-23: A FLAC file placed in the inbox is imported as an ALAC `.m4a` with the same tags and the same decoded audio samples.
- AC-24: Every file and directory in the library is owned by `apps:apps` or grants `apps` read and write access.
- AC-25: The review interface lists exactly the audio files that are in the library.
