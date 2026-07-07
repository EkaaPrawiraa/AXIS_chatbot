'use client';

import type { ComponentType, ReactNode } from 'react';

import { profileStyles } from '@/lib/styles/profileStyles';

/**
 * Profile settings row per the v3 design: tinted icon circle on the left,
 * small label + bold value + muted helper, optional accessory on the right.
 */
export function ProfileRow({
  Icon,
  label,
  value,
  helper,
  accessory,
  onClick,
}: {
  Icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
  helper?: string;
  accessory?: ReactNode;
  onClick?: () => void;
}) {
  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(event) => {
        if (onClick && (event.key === 'Enter' || event.key === ' ')) onClick();
      }}
      className={`${profileStyles.rowContainer} ${
        onClick ? profileStyles.rowPressable : ''
      }`}
    >
      <span className={profileStyles.rowTextGroup}>
        <span className={profileStyles.rowLabel}>
          <Icon className={profileStyles.rowInlineIcon} /> {label}
        </span>
        <span className={profileStyles.rowValue}>{value}</span>
        {helper ? (
          <span className={profileStyles.rowHelper}>{helper}</span>
        ) : null}
      </span>
      {accessory ? <span className={profileStyles.rowAccessoryWrapper}>{accessory}</span> : null}
    </div>
  );
}
