FROM nats:2.12-alpine@sha256:b270f5e2428354c0335612694d7dd2fb588148e567a5757fdff325ef9c9332e6
LABEL org.opencontainers.image.source="https://github.com/aluppol/nanolink" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.description="NanoLink queue: NATS JetStream with a file store"
COPY nats.conf /etc/nats/nanolink.conf
RUN mkdir -p /data && chown 1000:1000 /data
USER 1000:1000
EXPOSE 4222
ENTRYPOINT ["nats-server"]
CMD ["--config", "/etc/nats/nanolink.conf"]
