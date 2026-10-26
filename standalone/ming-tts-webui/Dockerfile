FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70

ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git libnuma1 libsndfile1 libgomp1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/opt/pip-cache \
    PIP_CACHE_DIR=/opt/pip-cache pip install \
    'torch[device-gfx1032]==2.12.0+rocm7.14.0' \
    --index-url https://repo.amd.com/rocm/whl-multi-arch/ --extra-index-url https://pypi.org/simple
COPY requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/opt/pip-cache \
    PIP_CACHE_DIR=/opt/pip-cache pip install -r /tmp/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Ming uses only Kaldi fbank, resampling and SoundFile I/O. These are Python/Torch
# functions in torchaudio 2.6; omit native extensions that require another Torch ABI.
RUN git clone --depth 1 --branch v2.6.0 https://github.com/pytorch/audio.git /tmp/audio \
    && test "$(git -C /tmp/audio rev-parse HEAD)" = d8831425203385077a03c1d92cfbbe3bf2106008 \
    && python -c "from pathlib import Path; p=Path('/tmp/audio/setup.py'); s=p.read_text(); old='ext_modules=setup_helpers.get_ext_modules(),'; assert s.count(old)==1; p.write_text(s.replace(old,'ext_modules=[],'))" \
    && BUILD_VERSION=2.6.0+pythononly USE_ROCM=0 USE_CUDA=0 pip install --no-deps --no-build-isolation /tmp/audio \
    && rm -rf /tmp/audio
WORKDIR /app
RUN git clone https://github.com/inclusionAI/Ming-3.0-tts.git /app/upstream \
    && git -C /app/upstream checkout 028c1eace193e7acdb256453da89b6e9207e052b \
    && rm -rf /app/upstream/.git \
    && useradd -m -u 1000 app
COPY patches/ming-progress.patch /tmp/ming-progress.patch
RUN cd /app/upstream && git apply /tmp/ming-progress.patch
COPY app.py engine.py voices.json test_requests.py test_audio_runtime.py test_api.py /app/
COPY tools/smoke_api.py /app/tools/smoke_api.py
COPY research/long-text.txt /app/research/long-text.txt
ENV MING_MODEL_PATH=/models MING_OUTPUT_DIR=/data/outputs MING_PORT=7861 \
    GRADIO_TEMP_DIR=/data/tmp GRADIO_ANALYTICS_ENABLED=False \
    HF_HOME=/data/cache/huggingface HF_HUB_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=6
USER app
EXPOSE 7861
CMD ["python", "-u", "app.py"]
