export type Environment = Readonly<Record<string, string | undefined>>;

export interface MongoSettings {
  readonly host: string;
  readonly port: number;
  readonly database: string;
  readonly username: string;
  readonly password: string;
}

export interface ValkeySettings {
  readonly host: string;
  readonly port: number;
  readonly password: string;
}

export interface RedirectSettings {
  readonly port: number;
  readonly logLevel: string;
  readonly mongo: MongoSettings;
  readonly valkey: ValkeySettings;
}

export class MissingEnvironmentVariable extends Error {
  constructor(variableName: string) {
    super(`Required environment variable ${variableName} is not set`);
    this.name = "MissingEnvironmentVariable";
  }
}

export class InvalidEnvironmentVariable extends Error {
  constructor(variableName: string, expectation: string) {
    super(`Environment variable ${variableName} must be ${expectation}`);
    this.name = "InvalidEnvironmentVariable";
  }
}

const LOG_LEVELS = new Set(["fatal", "error", "warn", "info", "debug", "trace", "silent"]);

export function readSettings(environment: Environment): RedirectSettings {
  return {
    port: readPort(environment, "PORT", 8080),
    logLevel: readLogLevel(environment),
    mongo: readMongoSettings(environment),
    valkey: readValkeySettings(environment),
  };
}

function readMongoSettings(environment: Environment): MongoSettings {
  return {
    host: requireValue(environment, "MONGO_HOST"),
    port: readPort(environment, "MONGO_PORT", 27017),
    database: requireValue(environment, "MONGO_DATABASE"),
    username: requireValue(environment, "MONGO_USERNAME"),
    password: requireValue(environment, "MONGO_REDIRECT_PASSWORD"),
  };
}

function readValkeySettings(environment: Environment): ValkeySettings {
  return {
    host: requireValue(environment, "VALKEY_HOST"),
    port: readPort(environment, "VALKEY_PORT", 6379),
    password: requireValue(environment, "VALKEY_PASSWORD"),
  };
}

function readLogLevel(environment: Environment): string {
  const level = optionalValue(environment, "LOG_LEVEL") ?? "warn";
  if (!LOG_LEVELS.has(level)) {
    throw new InvalidEnvironmentVariable("LOG_LEVEL", `one of ${[...LOG_LEVELS].join(", ")}`);
  }
  return level;
}

function readPort(environment: Environment, variableName: string, fallback: number): number {
  const value = optionalValue(environment, variableName);
  if (value === undefined) {
    return fallback;
  }
  const port = Number(value);
  if (!/^[0-9]+$/.test(value) || port < 1 || port > 65535) {
    throw new InvalidEnvironmentVariable(variableName, "a TCP port number from 1 to 65535");
  }
  return port;
}

function requireValue(environment: Environment, variableName: string): string {
  const value = optionalValue(environment, variableName);
  if (value === undefined) {
    throw new MissingEnvironmentVariable(variableName);
  }
  return value;
}

function optionalValue(environment: Environment, variableName: string): string | undefined {
  const value = environment[variableName];
  return value === undefined || value === "" ? undefined : value;
}
