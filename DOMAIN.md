# Music library domain

The music library is the household's collection of audio files, kept on a TrueNAS dataset and served by Plex to Plexamp. The library is the files themselves: a track is a file with tags inside it, and its place in the folder tree follows from those tags.

Everything that matters about a track is stored in the file. Title, artist, album, year, track number, cover art and where the track was downloaded from are all tags, so the files stay complete and portable if every tool around them is replaced. Tools that keep their own database, such as beets, treat it as a cache that can be rebuilt by reading the files again, and a fact is kept in a database only when no file or service already holds it.

New audio arrives in an inbox, outside the library. Most of it comes from YouTube, where titles, uploaders and thumbnails are not a reliable source of tags, so a person confirms or enters the metadata before a file is filed. Once its tags are final, the file is moved into the library at the path its tags dictate: `Artist/Album (Year)/Artist - Album - NN - Title`, with a single directly under its artist.

The library holds two formats, AAC and ALAC, both in `.m4a`. AAC is the source's own stream taken from a lossy source without re-encoding, and ALAC is what a lossless source becomes. Audio in any other format is converted to one of them before it enters the library. The format is read from the stream and never from the file name, because the two share an extension.

Plex reads the library and nothing else. A file appears in the library only when it is finished, because Plex identifies items by path: a file moved or renamed after Plex has scanned it appears as a new item and loses its play counts, ratings and playlist membership. Fixing a tag in place keeps the path and is safe; a fix that changes the path is a deliberate rename.

A person can see which downloads are waiting in the inbox and what the library holds, and nothing downloaded is lost between the two: a file is either in the inbox, in the library, or listed as failing to import.
