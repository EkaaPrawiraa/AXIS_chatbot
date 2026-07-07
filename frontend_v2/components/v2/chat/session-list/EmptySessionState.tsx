import { animationClasses, motionStyleVars } from "@/lib/animations";
import { sessionListStyles } from "@/lib/styles/sessionList";

export function EmptySessionState({ onNewChat }: { onNewChat: () => void }) {
	return (
		<section
			className={`${sessionListStyles.emptyStateContainer} ${animationClasses.cardEnter}`}
			style={motionStyleVars({ delayMs: 160 })}
		>
			<p className={sessionListStyles.emptyStateTitle}>
				Belum ada sesi
			</p>
			<p className={sessionListStyles.emptyStateDescription}>
				Mulai cerita baru saat kamu siap.
			</p>
			<button
				type="button"
				onClick={onNewChat}
				className={sessionListStyles.emptyStateButton}
			>
				Mulai cerita baru
			</button>
		</section>
	);
}
