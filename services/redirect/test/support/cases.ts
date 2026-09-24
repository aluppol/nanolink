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

export async function mismatchesOf<Input, Expected>(
  cases: readonly Case<Input, Expected>[],
  evaluate: (input: Input) => Expected | Promise<Expected>,
): Promise<Mismatch[]> {
  const mismatches: Mismatch[] = [];
  for (const testCase of cases) {
    const actual = await outcomeOf(evaluate, testCase.input);
    if (!isDeepStrictEqual(actual, testCase.expected)) {
      mismatches.push({ id: testCase.id, expected: testCase.expected, actual });
    }
  }
  return mismatches;
}

async function outcomeOf<Input, Expected>(
  evaluate: (input: Input) => Expected | Promise<Expected>,
  input: Input,
): Promise<unknown> {
  try {
    return await evaluate(input);
  } catch (error) {
    return { threw: error instanceof Error ? error.message : String(error) };
  }
}
