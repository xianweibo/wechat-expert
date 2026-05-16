FROM node:20-alpine

WORKDIR /app

COPY package.json ./

RUN npm config set registry https://registry.npmmirror.com && \
    npm install --omit=dev && \
    npm cache clean --force

COPY . .

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["node", "src/index.js"]
