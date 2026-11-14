---
type: Functionality
title: Acquisition
description: Downloading audio from a URL with MeTube and yt-dlp into the inbox as AAC in m4a, without re-encoding and without downloading the same video twice.
tags: [metube, yt-dlp, download, youtube, inbox, aac, m4a, info-json, archive]
---

# Context

MeTube is a web interface over yt-dlp and downloads from any source yt-dlp supports. It knows videos, with the video id as identity, and has no notion of albums or tags. `m4a` is the format this library uses.

YouTube serves AAC and Opus. The AAC stream is taken as it is, so the file stays AAC without a second lossy encoding.

Each download goes into its own subfolder of the inbox named after the video id, and that subfolder is the unit that is later imported. Beside the audio, an info JSON records the source URL and uploader. An archive in MeTube's state directory remembers which videos have been fetched.

MeTube has no server-side default for a download's type or format, because its web interface chooses them per browser. The global yt-dlp options therefore ask for `m4a` audio, and they apply to every submission whatever it asks for.

MeTube gives nothing to rely on for knowing when a download has finished, so new downloads are found by looking at the inbox.

The inbox is the `metube` directory of the Downloads share.

# Criteria

- AC-5: A URL submitted to MeTube as m4a audio produces `<inbox>/<video id>/<title>.m4a` and `<inbox>/<video id>/<title>.info.json`.
- AC-6: The audio codec of a downloaded file is `aac` when the source stream is AAC.
- AC-7: The audio bitrate of a downloaded AAC file equals the bitrate of the source stream.
- AC-9: MeTube mounts only the inbox and its own state directory.
- AC-31: A download submitted in MeTube without choosing a format is `m4a` audio.
- AC-32: A download uses the highest-bitrate AAC stream the source offers.
- AC-33: Submitting a URL whose audio was already downloaded creates no new file in the inbox.
