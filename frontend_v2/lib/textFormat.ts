/**
 * KG-extracted names (topics, etc.) are often snake_case English tokens
 * (e.g. `relationship_conflict`) rather than natural phrases — turn them
 * into something readable before ever showing them to the user. Shared
 * between the dashboard insight card and the KG node-detail sheet.
 */
export function humanizeSnakeCase(value: string): string {
  return value.replace(/[_-]+/g, ' ').trim().toLowerCase();
}
