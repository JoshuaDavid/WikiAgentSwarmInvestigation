FROM node:22-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends vim jq \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code@2.1.133

CMD ["sleep", "infinity"]
