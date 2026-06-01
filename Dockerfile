# syntax=docker/dockerfile:1

FROM node:20-alpine AS validation

WORKDIR /app

ENV NODE_ENV=production

COPY package.json package-lock.json ./
RUN npm ci --include=dev --ignore-scripts

COPY tsconfig.json ./
COPY src ./src
COPY scripts ./scripts
COPY tests ./tests

RUN npm run build --if-present
