import { createAvatar } from '@dicebear/core';
import { adventurer } from '@dicebear/collection';


export function avatarSrcForUser(seed?: string | null): string {
  const avatar = createAvatar(adventurer, {
    seed: seed || 'axis-guest',
    backgroundColor: ['e9eee1', 'f4ebe0'],
    backgroundType: ['solid'],
  });
  return avatar.toDataUri();
}
