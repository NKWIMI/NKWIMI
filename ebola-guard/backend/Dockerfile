FROM node:22-slim
WORKDIR /app
# Skip the optional GPU add-on of the embedding library (not needed on a server CPU).
ENV ONNXRUNTIME_NODE_INSTALL=skip \
    HF_HOME=/app/.cache
COPY package*.json ./
RUN npm install --omit=dev
COPY . .
# Build the document index if it is not committed, and download the embedding
# model once at build time so the first question is fast.
RUN if [ ! -f data/index.json ]; then npm run ingest || echo "Ingest failed: answers will not cite sources"; fi \
 && node -e "import('./src/embedder.js').then(m => m.createEmbedder().embed(['warm up'], 'query')).then(() => console.log('model ready')).catch(e => console.log('model not ready:', e.message))"
ENV PORT=8080
EXPOSE 8080
CMD ["node", "server.js"]
