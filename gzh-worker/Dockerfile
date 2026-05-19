FROM node:20-alpine

WORKDIR /app

COPY package.json ./

RUN npm install --omit=dev && npm cache clean --force

COPY . .

RUN mkdir -p /app/data

CMD ["node", "src/index.js"]