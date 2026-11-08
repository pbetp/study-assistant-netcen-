# Packages the web app so a host (Hugging Face Spaces) can run it.
# Needs a `chroma_db/` folder (the index) next to this file in the build folder.
# See DEPLOY.md. The slides themselves are NOT copied into the image.
FROM python:3.11-slim

# Hugging Face runs containers as user 1000, so create that user and use it.
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

# CPU-only PyTorch (the host has no GPU): a far smaller download than the default build.
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

COPY --chown=user app ./app

# Download the embedding model while building, so the first search does not have to.
# The folder matches the default cache folder in app/embed.py.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('intfloat/multilingual-e5-small', cache_folder='.cache/models')"

# The pre-built index (made on your computer with `python -m app.cli index`).
COPY --chown=user chroma_db ./chroma_db

# Hugging Face expects the app on port 7860.
EXPOSE 7860
CMD ["uvicorn", "app.api:create_default_app", "--factory", "--host", "0.0.0.0", "--port", "7860"]
