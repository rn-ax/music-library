# beets

- The configuration is baked into the image at `/etc/beets/config.yaml` and every `beet` call passes it with `-c`, so changing it means building a new image.
- The `musicbrainz` plugin has to be listed, because beets only matches against MusicBrainz when it is enabled.
- `beet import --set FIELD=VALUE` sets a field on every imported item.
