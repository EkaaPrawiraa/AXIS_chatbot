import { createAvatar } from '@dicebear/core';
import { adventurer } from '@dicebear/collection';

/**
 * Deterministic per-user avatar: same seed always renders the same SVG, so
 * every user gets a unique picture with no upload/storage needed. Replaces
 * the old two-static-PNG-by-gender scheme, where every male user shared one
 * literal picture and every female user shared another.
 */
export function avatarSrcForUser(seed?: string | null): string {
  const avatar = createAvatar(adventurer, {
    seed: seed || 'axis-guest',
    backgroundColor: ['e9eee1', 'f4ebe0'],
    backgroundType: ['solid'],
  });
  return avatar.toDataUri();
}
