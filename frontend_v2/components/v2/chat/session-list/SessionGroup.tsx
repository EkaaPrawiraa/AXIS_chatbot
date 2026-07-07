import type { ReactNode } from "react";
import { animationClasses, motionStyleVars } from "@/lib/animations";
import { sessionListStyles } from "@/lib/styles/sessionList";

export function SessionGroup({
	title,
	count,
	action,
	children,
}: {
	title: string;
	count: number;
	action?: ReactNode;
	children: ReactNode;
}) {
	return (
		<section
			className={animationClasses.staggerItem}
			style={motionStyleVars({ delayMs: 150 })}
		>
			<div className={sessionListStyles.groupHeader}>
				<div className={sessionListStyles.groupTitleContainer}>
					<h2 className={sessionListStyles.groupTitle}>{title}</h2>
					<span className={sessionListStyles.groupCountBadge}>
						{count}
					</span>
				</div>
				{action}
			</div>
			{children}
		</section>
	);
}
