FROM node:20-alpine

WORKDIR /app

COPY package.json ./

RUN npm config set registry https://registry.npmmirror.com && \
    npm install && \
    npm cache clean --force

COPY . .

RUN mkdir -p /app/data

CMD ["npx", "tsx", "src/index.ts"]