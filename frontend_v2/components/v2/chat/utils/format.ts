export function formatChatTime(value?: string | number): string {
  const date = typeof value === 'number' ? new Date(value) : value ? new Date(value) : new Date();
  return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }).replace('.', ':');
}
export function formatChatDateDivider(value: string | number): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Hari ini';
  const now = new Date();
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const dayDiff = Math.round((startOfDay(now) - startOfDay(date)) / 86_400_000);
  if (dayDiff === 0) return 'Hari ini';
  if (dayDiff === 1) return 'Kemarin';
  const sameYear = date.getFullYear() === now.getFullYear();
  return date.toLocaleDateString('id-ID', {
    day: 'numeric',
    month: 'short',
    year: sameYear ? undefined : 'numeric',
  });
}
export function isDifferentCalendarDay(a: string | number, b: string | number): boolean {
  const dateA = new Date(a);
  const dateB = new Date(b);
  return dateA.toDateString() !== dateB.toDateString();
}
