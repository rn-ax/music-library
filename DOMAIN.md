# Music library domain

The music library is the household's collection of audio files, kept on a TrueNAS dataset and served by Plex to Plexamp. The library is the files themselves: a track is a file with tags inside it, and its place in the folder tree follows from those tags.

Everything that matters about a track is stored in the file. Title, artist, album, year, track number, cover art and where the track was downloaded from are all tags, so the files stay complete and portable if every tool around them is replaced. Tools that keep their own database, such as beets, treat it as a cache that can be rebuilt by reading the files again, and a fact is kept in a database only when no file or service already holds it.

New audio arrives in an inbox, outside the library. Most of it comes from YouTube, where titles, uploaders and thumbnails are not a reliable source of tags, so a person confirms or enters the metadata before a file is filed. Once its tags are final, the file is moved into the library at the path its tags dictate: `Artist/Album (Year)/NN Title`, with a single directly under its artist.

A track is part of an album, part of a compilation, or stands alone as a single. An album track is filed under its album artist and album, a compilation track under `Compilations` with its own artist in the file name, and a single directly under its artist with no album folder. beets calls a single a singleton. A single has no album to tell versions apart, so a live version, remix or cover says so in its title, as in `Kryptonite (Live @ The Song)`.

Automatic matching against MusicBrainz suggests tags, and a person has the final say. Downloads of covers, live recordings and remixes often have no match, so typing the tags by hand is a normal path and not a failure.

A video is downloaded once. The downloader keeps an archive of the videos it has fetched, so asking for the same one again does nothing.

The library holds two formats, AAC and ALAC, both in `.m4a`. AAC is the source's own stream taken from a lossy source without re-encoding, and ALAC is what a lossless source becomes. Audio in any other format is converted to one of them before it enters the library. The format is read from the stream and never from the file name, because the two share an extension.

Plex reads the library and nothing else. A file appears in the library only when it is finished, because Plex identifies items by path: a file moved or renamed after Plex has scanned it appears as a new item and loses its play counts, ratings and playlist membership. Fixing a tag in place keeps the path and is safe; a fix that changes the path is a deliberate rename.

A person can see which downloads are waiting in the inbox and what the library holds, and nothing downloaded is lost between the two: a file is either in the inbox, in the library, or listed as failing to import.

## Contexts

The library is built from components that each have their own model of music and their own words for it. Each component is used on its own terms, and the places where their meanings meet are named, so nothing is assumed to mean the same thing on both sides.

**Acquisition (MeTube and yt-dlp)** knows videos, not songs. A video's id is its identity, and its words are video, playlist, channel, uploader and title, where the title belongs to the video and the uploader is whoever published it. It produces a folder per video holding the audio file and an info JSON describing the source. It knows nothing about albums, tags or the library.

**Cataloguing (beets)** knows tagged audio files. Its unit is the item, a file with tags, and an item is either grouped into an album by shared album tags or stands alone as a singleton. It owns the tags in the library and the path each file is filed at, computed from those tags by path templates. It keeps a database of the library that is a cache of what the files say, and it matches against MusicBrainz and stores its identifiers. An import moves or copies a folder from the inbox into the library.

**Review (beets-flask)** is a web interface around beets with its own installation and database. Its words are inbox, preview and import: an inbox is a watched folder, each subfolder of it is one import session, a preview shows the candidate matches for a session, and an import commits it. It follows beets' model and adds the workflow around it, and it always copies.

**Listening (Plex and Plexamp)** knows artists, albums and tracks, which it derives from the files' tags and paths, and it keeps what only it can know: play counts, ratings and playlists. It identifies an item by its path. It reads the library and never changes it, and a scan is how it learns what the library holds.

**Storage (TrueNAS)** knows datasets, shares, ownership and ACLs. It decides who can read and write each directory.

**This repository** deploys the other components together and holds the glue between them: the compose stack, the image that runs beets, and the configuration that makes the output of one component usable by the next.

## Words that differ between contexts

- **Library** is the files in the Music dataset in this document. A beets library is its database together with that directory, and a Plex library is a section pointing at a directory.
- **Track** is a file with tags. Beets calls it an item and Plex calls it a track.
- **Title** is the song's title tag in beets and Plex, and the video's title in MeTube.
- **Artist** is the performer tag in beets and Plex, with the album artist used for filing, and the uploader's name in MeTube, which often is not the performer.
- **Single** is a track filed with no album. Beets calls it a singleton, and Plex sees it only through its tags and path.
- **Import** is beets moving or copying a folder into the library. Plex's counterpart is a scan, which reads the library without changing it.
- **Inbox** is the directory MeTube writes into and beets and beets-flask import from.

## Where the contexts meet

MeTube hands over a folder per video holding the audio and its info JSON. The translation into tags happens at that point: the video's title and uploader become suggested title and artist, and a person confirms them.

Beets hands Plex files. The tags and the path are the whole contract, so the path templates must give Plex paths it groups sensibly, and the album and album artist tags must agree across an album's tracks because Plex builds an album from them. A scan after an import tells Plex that something changed.

MusicBrainz is an outside authority that beets consults for matches. A person's decision overrides what it suggests.

The meeting points between components are the filesystem and the tags inside the files. Each component's private store, which is MeTube's state, the beets database, the beets-flask database and Plex's database, is written only by that component. Play counts live only in Plex and are never written back into the files.
