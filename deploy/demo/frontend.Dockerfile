FROM node:22-bookworm-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --chown=node:node frontend/package.json frontend/next.config.ts ./
COPY --chown=node:node frontend/node_modules ./node_modules
COPY --chown=node:node frontend/.next-demo ./.next
COPY --chown=node:node frontend/public ./public
USER node
CMD ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
