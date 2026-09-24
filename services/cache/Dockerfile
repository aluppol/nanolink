FROM valkey/valkey:8.1-alpine@sha256:081c2f5cb575efc901aa80ff9cdbd1ec6a301682fd35e1ebb4b0990a4a4a8507
LABEL org.opencontainers.image.source="https://github.com/aluppol/nanolink" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.description="NanoLink cache: Valkey as a bounded LRU cache without persistence"
COPY --chmod=0755 start-valkey valkey-health /usr/local/bin/
USER valkey
EXPOSE 6379
ENTRYPOINT ["tini", "--", "start-valkey"]
