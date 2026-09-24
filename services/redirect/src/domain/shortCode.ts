const SHORT_CODE_PATTERN = /^[0-9A-Za-z]{6}$/;

export function isShortCode(candidate: string): boolean {
  return SHORT_CODE_PATTERN.test(candidate);
}
