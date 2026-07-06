import { cn } from '@/lib/utils';

interface AxisAvatarIconProps {
  className?: string;
  size?: number;
}

export function AxisAvatarIcon({ className, size = 14 }: AxisAvatarIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="AXIS"
      role="img"
      className={cn(className)}
    >
      <text
        x="7"
        y="10"
        textAnchor="middle"
        fontFamily="Georgia, 'Times New Roman', 'DejaVu Serif', serif"
        fontSize="7"
        fontWeight="700"
        fill="currentColor"
        letterSpacing="-0.2"
      >
        X&#8217;s
      </text>
    </svg>
  );
}
