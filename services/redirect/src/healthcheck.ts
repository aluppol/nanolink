const port = process.env.PORT ?? "8080";

const response = await fetch(`http://127.0.0.1:${port}/healthz`, {
  signal: AbortSignal.timeout(2000),
}).catch(() => undefined);

process.exit(response?.ok === true ? 0 : 1);
