"use client";

import ReactMarkdown from "react-markdown";
import type { Message } from "@/models";
import { MessageActions } from "@/components/v2/chat/MessageActions";
import { PhqCard, parsePhqContent } from "@/components/v2/chat/PhqCard";
import { TypingDots } from "@/components/v2/chat/TypingDots";
import { formatChatTime } from "@/components/v2/chat/format";
import { animationClasses } from "@/lib/animations";

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

	if (isPhqItem && parsed?.question && phq?.options) {
		return (
			<div
				data-bubble="assistant"
				className={`w-full max-w-[92%] space-y-1.5 ${animationClasses.chatBubbleIn}`}
			>
				{parsed.intro ? (
					<div className="w-fit rounded-[12px] bg-[#efeae0] px-3.5 py-2.5 text-[14px] font-medium leading-[1.5] text-[var(--v2-ink)] [&_p]:whitespace-pre-wrap">
						<ReactMarkdown>{parsed.intro}</ReactMarkdown>
					</div>
				) : null}
				<PhqCard
					question={parsed.question}
					current={phq.progress?.current ?? phq.item_id ?? 1}
					total={phq.progress?.total ?? 9}
					options={phq.options}
					disabled={phqDisabled}
					onAnswer={(label) => onPhqAnswer?.(label)}
					onAskWhat={() => onPhqAnswer?.("Bisa jelasin maksud pertanyaan ini?")}
				/>
				<p className="pl-1 text-[11px] font-medium text-[#8d8880]">
					{formatChatTime(message.createdAt)}
				</p>
			</div>
		);
	}

	return (
		<div
			data-bubble="assistant"
			className={`w-fit max-w-[84%] space-y-1.5 ${animationClasses.chatBubbleIn}`}
		>
			<div className="rounded-[12px] bg-[#efeae0] px-3.5 py-2.5 text-[14px] font-medium leading-[1.5] text-[var(--v2-ink)] [&_p]:whitespace-pre-wrap">
				{awaitingFirstToken ? <TypingDots /> : <ReactMarkdown>{message.content}</ReactMarkdown>}
				{showPhqChips ? (
					<div className="mt-3 space-y-2 rounded-[12px] bg-[var(--v2-olive-soft)] p-2.5">
						<div className="grid gap-1.5">
							{phq?.options?.map((option) => (
								<button
									key={`${message.id}-${option.label}`}
									disabled={phqDisabled}
									onClick={() => onPhqAnswer?.(option.label)}
									className="v2-anim-pressable rounded-[10px] border border-[var(--v2-line)] bg-white/80 px-3 py-2 text-left text-[13px] font-semibold disabled:opacity-45"
								>
									{option.label}
								</button>
							))}
						</div>
					</div>
				) : null}
			</div>
			{showActions ? (
				<div className="flex items-center gap-2.5 pl-1">
					<MessageActions
						content={message.content}
						onPlay={onPlay}
						onRegenerate={onRegenerate}
						showRegenerate={showRegenerate}
						isPlaying={isPlaying}
						isRegenerating={isRegenerating}
					/>
					<span className="shrink-0 text-[11px] font-medium text-[#8d8880]">
						{formatChatTime(message.createdAt)}
					</span>
				</div>
			) : (
				<p className="pl-1 text-[11px] font-medium text-[#8d8880]">
					{formatChatTime(message.createdAt)}
				</p>
			)}
		</div>
	);
}
