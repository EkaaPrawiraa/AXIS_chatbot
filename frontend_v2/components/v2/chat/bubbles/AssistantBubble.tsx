"use client";

import ReactMarkdown from "react-markdown";
import type { Message } from "@/models";
import { MessageActions } from "@/components/v2/chat/bubbles/MessageActions";
import { PhqCard, parsePhqContent } from "@/components/v2/chat/cards/PhqCard";
import { TypingDots } from "@/components/v2/chat/bubbles/TypingDots";
import { formatChatTime } from "@/components/v2/chat/utils/format";
import { animationClasses } from "@/lib/animations";
import { chatRoomStyles } from "@/lib/styles/chatRoom";

// assistant chat bubble: cream fill, timestamp below-left, optional action pills and PHQ answer chips
export function AssistantBubble({
	message,
	showActions = true,
	onPhqAnswer,
	phqDisabled = false,
	onRegenerate,
	showRegenerate = false,
	onPlay,
	isPlaying = false,
	isRegenerating = false,
	isStreaming = false,
}: {
	message: Message;
	showActions?: boolean;
	onPhqAnswer?: (label: string) => void;
	phqDisabled?: boolean;
	onRegenerate?: () => void;
	showRegenerate?: boolean;
	onPlay?: () => void;
	isPlaying?: boolean;
	isRegenerating?: boolean;
	isStreaming?: boolean;
}) {
	// show typing dots during the gap before the first streamed token, instead of an empty bubble that looks frozen
	const awaitingFirstToken = isStreaming && !message.content.trim();
	const phq = message.metadata?.phq9;
	const isPhqItem =
		phq?.active &&
		!!phq.options?.length &&
		(phq.phase === "in_progress" || phq.phase === "awaiting_clar");
	const showPhqChips = phq?.active && !!phq.options?.length && !isPhqItem;
	const parsed = isPhqItem ? parsePhqContent(message.content) : null;

	if (isPhqItem && phq?.options) {
		const introText = parsed?.intro || message.content;
		const questionText = parsed?.question || "Silakan pilih jawaban yang paling sesuai:";

		return (
			<div
				data-bubble="assistant"
				className={`${chatRoomStyles.assistantBubbleWrapper} ${animationClasses.chatBubbleIn}`}
			>
				{introText ? (
					<div className={chatRoomStyles.assistantBubbleBody}>
						<ReactMarkdown>{introText}</ReactMarkdown>
					</div>
				) : null}
				<PhqCard
					question={questionText}
					current={phq.progress?.current ?? phq.item_id ?? 1}
					total={phq.progress?.total ?? 9}
					options={phq.options}
					disabled={phqDisabled}
					onAnswer={(label) => onPhqAnswer?.(label)}
					onAskWhat={() => onPhqAnswer?.("Bisa jelasin maksud pertanyaan ini?")}
				/>
				<p className={chatRoomStyles.assistantTimestamp}>
					{formatChatTime(message.createdAt)}
				</p>
			</div>
		);
	}

	return (
		<div
			data-bubble="assistant"
			className={`${chatRoomStyles.assistantBubbleWrapper} ${animationClasses.chatBubbleIn}`}
		>
			<div className={chatRoomStyles.assistantBubbleBody}>
				{awaitingFirstToken ? <TypingDots /> : <ReactMarkdown>{message.content}</ReactMarkdown>}
				{showPhqChips ? (
					<div className={chatRoomStyles.assistantPhqChipsWrapper}>
						<div className={chatRoomStyles.assistantPhqChipsGrid}>
							{phq?.options?.map((option) => (
								<button
									key={`${message.id}-${option.label}`}
									disabled={phqDisabled}
									onClick={() => onPhqAnswer?.(option.label)}
									className={chatRoomStyles.assistantPhqChipBtn}
								>
									{option.label}
								</button>
							))}
						</div>
					</div>
				) : null}
			</div>
			{showActions ? (
				<div className={chatRoomStyles.assistantActionRow}>
					<MessageActions
						content={message.content}
						onPlay={onPlay}
						onRegenerate={onRegenerate}
						showRegenerate={showRegenerate}
						isPlaying={isPlaying}
						isRegenerating={isRegenerating}
					/>
					<span className={chatRoomStyles.assistantTimestampAction}>
						{formatChatTime(message.createdAt)}
					</span>
				</div>
			) : (
				<p className={chatRoomStyles.assistantTimestamp}>
					{formatChatTime(message.createdAt)}
				</p>
			)}
		</div>
	);
}
