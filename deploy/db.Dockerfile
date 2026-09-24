FROM mongo:7.0@sha256:9854f7139445d766a9523571d6f047530c45547460ffcf8259eb2bf4264632ca
# The server allows no bind mounts, so the first-start script that creates both service users and the index is baked in.
COPY database/mongo-init.js /docker-entrypoint-initdb.d/mongo-init.js
