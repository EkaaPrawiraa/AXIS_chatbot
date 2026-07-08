
export function humanizeSnakeCase(value: string): string {
  return value.replace(/[_-]+/g, ' ').trim().toLowerCase();
}
