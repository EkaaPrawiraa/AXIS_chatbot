import type { Conversation } from "@/models";

export function groupConversations(conversations: Conversation[]): {
	today: Conversation[];
	previous: Conversation[];
} {
	const today: Conversation[] = [];
	const previous: Conversation[] = [];
	const now = new Date();
	for (const conversation of conversations) {
		const date = new Date(conversation.lastMessageAt || conversation.updatedAt);
		if (
			!Number.isNaN(date.getTime()) &&
			date.toDateString() === now.toDateString()
		) {
			today.push(conversation);
		} else {
			previous.push(conversation);
		}
	}
	return { today, previous };
}

export function getSessionBadge(conversation: Conversation): string {
	const title = (conversation.title || "").toLowerCase();
	const preview = (conversation.preview || "").toLowerCase();
	if (
		title.includes("mood") ||
		title.includes("suasana") ||
		preview.includes("skor")
	) {
		return "Mood check";
	}
	const date = new Date(conversation.lastMessageAt || conversation.updatedAt);
	if (
		!Number.isNaN(date.getTime()) &&
		date.toDateString() === new Date().toDateString()
	) {
		return "Aktif";
	}
	return conversation.messageCount <= 1 ? "Belum selesai" : "";
}

export function formatSessionTime(value: number | string | Date | undefined): string {
	if (!value) return "";
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return "";
	const now = new Date();
	const sameDay = date.toDateString() === now.toDateString();
	if (sameDay) {
		return new Intl.DateTimeFormat("id-ID", {
			hour: "2-digit",
			minute: "2-digit",
		}).format(date);
	}
	return new Intl.DateTimeFormat("id-ID", {
		day: "2-digit",
		month: "short",
	}).format(date);
}
