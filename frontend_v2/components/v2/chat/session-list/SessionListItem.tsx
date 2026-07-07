import type { Conversation } from "@/models";
import { animationClasses, motionStyleVars } from "@/lib/animations";
import { sessionListStyles } from "@/lib/styles/sessionList";
import { getSessionBadge, formatSessionTime } from "./utils";

export function SessionListItem({
	conversation,
	index,
	onClick,
}: {
	conversation: Conversation;
	index: number;
	onClick: () => void;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			className={`${sessionListStyles.itemBase} ${animationClasses.staggerItem}`}
			style={motionStyleVars({ delayMs: 195 + index * 40 })}
		>
			<div className={sessionListStyles.itemContent}>
				<div className={sessionListStyles.itemHeader}>
					<p className={sessionListStyles.itemTitle}>
						{conversation.title || "Cerita baru"}
					</p>
					<span className={sessionListStyles.itemTime}>
						{formatSessionTime(
							conversation.lastMessageAt || conversation.updatedAt,
						)}
					</span>
				</div>
				<div className={sessionListStyles.itemBody}>
					<p className={sessionListStyles.itemPreview}>
						{conversation.preview || "Belum ada pesan."}
					</p>
					<SessionBadge conversation={conversation} />
				</div>
			</div>
		</button>
	);
}

export function SessionBadge({
	conversation,
}: {
	conversation: Conversation;
}) {
	const label = getSessionBadge(conversation);
	if (!label) return null;
	return (
		<span className={sessionListStyles.badgeBase}>
			{label}
		</span>
	);
}
