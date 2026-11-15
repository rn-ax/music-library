---
type: Functionality
title: Filer
description: The script that files finished downloads from the staging folder into the library, converting audio that is not AAC or ALAC, and the triggers that run it.
tags: [filer, script, staging, library, convert, flac, alac, aac, mp3, move, watcher, trigger]
---

# Context

Finished downloads wait in a staging folder that nobody reviews. One script holds all the logic for getting them into the library: it looks at what is waiting, converts what needs converting, moves each file to its place and removes what it staged. Running it with nothing waiting changes nothing, so anything can trigger it, and tests run it directly.

A file's place in the library is built from its own tags: `<artist>/<title>.m4a`, with the uploader standing in as the artist for a download. Fixing tags and paths afterwards is optional and done by hand.

Lossless sources become ALAC and other formats become AAC, so the library holds only the two formats.

# Criteria

- AC-36: Running the filing script moves each finished file in the staging folder into the library at `<artist>/<title>.m4a`, converted to ALAC or AAC first when its format is neither.
- AC-37: A file that finishes in the staging folder is in the library within two minutes, without anyone starting the filing script.
