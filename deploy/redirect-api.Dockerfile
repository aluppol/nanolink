FROM node:22-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c AS build
WORKDIR /src
COPY services/redirect_api/package*.json services/redirect_api/tsconfig.json ./
RUN npm install --no-audit --no-fund
COPY services/redirect_api/src ./src
RUN npm run build && npm prune --omit=dev

FROM node:22-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /src/package.json ./package.json
COPY --from=build /src/node_modules ./node_modules
COPY --from=build /src/dist ./dist
USER node
EXPOSE 3000
CMD ["node", "dist/server.js"]
