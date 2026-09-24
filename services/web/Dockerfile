FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS build
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY biome.json tsconfig.json ./
COPY scripts ./scripts
COPY src ./src
COPY test ./test
RUN npm run check && npm run build

FROM nginxinc/nginx-unprivileged:1.29-alpine@sha256:0c79d56aee561a1d81c63f00eee5fb5fe29279560cdc55e91425133104c7fbe6
LABEL org.opencontainers.image.title="nanolink-web" \
      org.opencontainers.image.description="NanoLink entry service: the UI and the router in front of the API gateway, the notifier and the redirect service" \
      org.opencontainers.image.source="https://github.com/aluppol/nanolink" \
      org.opencontainers.image.licenses="AGPL-3.0-only"
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --chmod=0755 bin/demo-reset /usr/local/bin/demo-reset
COPY --from=build /build/dist/ /usr/share/nginx/html/
RUN nginx -t
EXPOSE 8080
