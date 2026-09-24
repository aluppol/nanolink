import { isDeepStrictEqual } from "node:util";

export interface Case<Input, Expected> {
  readonly id: string;
  readonly input: Input;
  readonly expected: Expected;
}

export interface Mismatch {
  readonly id: string;
  readonly expected: unknown;
  readonly actual: unknown;
}

export function mismatchesOf<Input, Expected>(
  cases: readonly Case<Input, Expected>[],
  run: (input: Input, expected: Expected) => unknown,
): readonly Mismatch[] {
  return cases.flatMap((entry) => {
    const actual = run(entry.input, entry.expected);
    return isDeepStrictEqual(actual, entry.expected)
      ? []
      : [{ id: entry.id, expected: entry.expected, actual }];
  });
}

export function errorMessageOf(run: () => unknown): string {
  try {
    run();
    return "no error";
  } catch (error) {
    return error instanceof Error ? error.message : String(error);
  }
}
