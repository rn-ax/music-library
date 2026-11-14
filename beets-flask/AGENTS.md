# beets-flask

- The image is the upstream release with polars' compatibility runtime swapped in (`Dockerfile` here), because the TrueNAS host's CPU has no AVX and polars' default runtime crashes on it. The Dockerfile follows the upstream release it starts from. Renovate versions the upstream image as semver, because its default Docker versioning treats a release-candidate suffix as a separate flavor and never proposes the final release, and it excludes pre-release tags, because Renovate otherwise follows release candidates for as long as the current tag is one. The pin is a release candidate only because upstream has no stable v2 yet, and the next proposal is the final v2.0.0.
- The upstream image bundles its own beets and keeps its own database, separate from the `music` service's.
- It reads `beets/config.yaml` and `beets-flask/config.yaml` from its `/config` volume. The container generates defaults when they are missing, and a restart applies a change. The files in this directory are the seeds, copied into place before the first start.
- Its config schema accepts only `import.copy: yes` with `import.move: no`.
- A uvicorn worker that crashes at startup logs nothing, because the server runs with logging disabled. Running `create_app()` from `beets_flask.server.app` by hand inside the container shows the exception.
- The `chroma` plugin is incompatible with it, so its beets configuration leaves `chroma` out.
- An inbox in `auto` mode imports good matches without review, and `preview` mode waits for a person.
