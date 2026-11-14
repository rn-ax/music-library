FROM pspitzner/beets-flask:v2.0.0-rc5
# Polars' default runtime needs AVX, which the TrueNAS host's CPU lacks, so every server worker dies at import.
# Its compatibility runtime runs on any x86-64 CPU and has to match the installed polars version.
RUN v=$(/venv/bin/python -c "from importlib.metadata import version; print(version('polars'))") \
    && uv pip install --link-mode copy --python /venv/bin/python "polars[rtcompat]==$v"
