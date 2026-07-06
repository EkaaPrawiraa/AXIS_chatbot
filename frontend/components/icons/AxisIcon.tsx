import { cn } from '@/lib/utils';

interface AxisIconProps {
  className?: string;
  size?: number;
  variant?: 'filled' | 'outline';
}

export function AxisIcon({ className, size = 24, variant = 'filled' }: AxisIconProps) {
  const isFilled = variant === 'filled';

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="AXIS"
      role="img"
      className={cn(className)}
    >
      <rect
        x="1"
        y="1"
        width="22"
        height="22"
        rx="6"
        ry="6"
        fill={isFilled ? 'var(--axis-brand, oklch(0.22 0.006 84))' : 'none'}
        stroke={isFilled ? 'none' : 'currentColor'}
        strokeWidth="1.5"
      />
      <text
        x="12"
        y="15.5"
        textAnchor="middle"
        fontFamily="Georgia, 'Times New Roman', 'DejaVu Serif', serif"
        fontSize="9"
        fontWeight="700"
        fill={isFilled ? 'var(--axis-brand-fg, white)' : 'currentColor'}
        letterSpacing="-0.3"
      >
        X&#8217;s
      </text>
    </svg>
  );
}
