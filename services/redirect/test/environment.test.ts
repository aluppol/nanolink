import assert from "node:assert/strict";
import { test } from "node:test";
import {
  type Environment,
  type RedirectSettings,
  readSettings,
} from "../src/adapters/environment.js";
import { type Case, mismatchesOf } from "./support/cases.js";

const COMPLETE: Environment = {
  MONGO_HOST: "mongo",
  MONGO_DATABASE: "nanolink",
  MONGO_USERNAME: "redirect",
  MONGO_REDIRECT_PASSWORD: "mongo-secret",
  VALKEY_HOST: "cache",
  VALKEY_PASSWORD: "valkey-secret",
};

const DEFAULTS: RedirectSettings = {
  port: 8080,
  logLevel: "warn",
  mongo: {
    host: "mongo",
    port: 27017,
    database: "nanolink",
    username: "redirect",
    password: "mongo-secret",
  },
  valkey: { host: "cache", port: 6379, password: "valkey-secret" },
};

function without(variableName: string): Environment {
  return { ...COMPLETE, [variableName]: undefined };
}

const CASES: readonly Case<Environment, RedirectSettings | { threw: string }>[] = [
  { id: "required variables only use the defaults", input: COMPLETE, expected: DEFAULTS },
  {
    id: "ports and log level are read when set",
    input: {
      ...COMPLETE,
      PORT: "9090",
      MONGO_PORT: "27018",
      VALKEY_PORT: "6380",
      LOG_LEVEL: "info",
    },
    expected: {
      ...DEFAULTS,
      port: 9090,
      logLevel: "info",
      mongo: { ...DEFAULTS.mongo, port: 27018 },
      valkey: { ...DEFAULTS.valkey, port: 6380 },
    },
  },
  {
    id: "empty optional value falls back to the default",
    input: { ...COMPLETE, PORT: "" },
    expected: DEFAULTS,
  },
  ...[
    "MONGO_HOST",
    "MONGO_DATABASE",
    "MONGO_USERNAME",
    "MONGO_REDIRECT_PASSWORD",
    "VALKEY_HOST",
    "VALKEY_PASSWORD",
  ].map((variableName) => ({
    id: `missing ${variableName} names the variable`,
    input: without(variableName),
    expected: { threw: `Required environment variable ${variableName} is not set` },
  })),
  {
    id: "empty secret counts as missing",
    input: { ...COMPLETE, VALKEY_PASSWORD: "" },
    expected: { threw: "Required environment variable VALKEY_PASSWORD is not set" },
  },
  {
    id: "non-numeric port is rejected",
    input: { ...COMPLETE, PORT: "http" },
    expected: { threw: "Environment variable PORT must be a TCP port number from 1 to 65535" },
  },
  {
    id: "out-of-range port is rejected",
    input: { ...COMPLETE, MONGO_PORT: "70000" },
    expected: {
      threw: "Environment variable MONGO_PORT must be a TCP port number from 1 to 65535",
    },
  },
  {
    id: "fractional port is rejected",
    input: { ...COMPLETE, VALKEY_PORT: "63.5" },
    expected: {
      threw: "Environment variable VALKEY_PORT must be a TCP port number from 1 to 65535",
    },
  },
  {
    id: "unknown log level is rejected",
    input: { ...COMPLETE, LOG_LEVEL: "verbose" },
    expected: {
      threw:
        "Environment variable LOG_LEVEL must be one of fatal, error, warn, info, debug, trace, silent",
    },
  },
];

test("readSettings reads the §10 variables and names whatever is wrong", async () => {
  assert.deepEqual(await mismatchesOf(CASES, readSettings), []);
});
