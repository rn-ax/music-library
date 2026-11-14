# beets-flask

- The upstream image bundles its own beets and keeps its own database, separate from the `music` service's.
- It reads `beets/config.yaml` and `beets-flask/config.yaml` from its `/config` volume. The container generates defaults when they are missing, and a restart applies a change. The files in this directory are the seeds, copied into place before the first start.
- Its config schema accepts only `import.copy: yes` with `import.move: no`.
- The `chroma` plugin is incompatible with it, so its beets configuration leaves `chroma` out.
- An inbox in `auto` mode imports good matches without review, and `preview` mode waits for a person.
