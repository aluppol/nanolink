export const DEADLINE_PASSED = Symbol("deadline passed");

export async function settleWithin<Value>(
  operation: Promise<Value>,
  milliseconds: number,
): Promise<Value | typeof DEADLINE_PASSED> {
  let timer: NodeJS.Timeout | undefined;
  const deadline = new Promise<typeof DEADLINE_PASSED>((resolve) => {
    timer = setTimeout(resolve, milliseconds, DEADLINE_PASSED);
  });
  try {
    return await Promise.race([operation, deadline]);
  } finally {
    clearTimeout(timer);
  }
}
