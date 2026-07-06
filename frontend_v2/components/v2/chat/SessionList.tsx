"use client";

import {
	ChevronDown,
	ChevronRight,
	ChevronUp,
	MessageCirclePlus,
	Search,
} from '@/lib/assets';
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { MobileAppHeader } from "@/components/v2/MobileAppHeader";
import { animationClasses, motionStyleVars } from "@/lib/animations";
import type { Conversation } from "@/models";

export function SessionListView({
	conversations,
	searchQuery,
	onSearchChange,
	onChoose,
	onNewChat,
}: {
	conversations: Conversation[];
	searchQuery: string;
	onSearchChange: (value: string) => void;
	onChoose: (id: string) => void;
	onNewChat: () => void;
}) {
	const grouped = useMemo(
		() => groupConversations(conversations),
		[conversations],
	);
	const [showAllPrevious, setShowAllPrevious] = useState(false);
	const [showAllToday, setShowAllToday] = useState(false);
	const visiblePrevious = showAllPrevious
		? grouped.previous
		: grouped.previous.slice(0, 4);
	const visibleToday = showAllToday ? grouped.today : grouped.today.slice(0, 2);

	return (
		<main
			className={`min-h-[100dvh] pb-[86px] pt-0 ${animationClasses.pageEnter}`}
			style={motionStyleVars({ durationMs: 300 })}
		>
			<section
				className={animationClasses.staggerItem}
				style={motionStyleVars({ delayMs: 35 })}
			>
				<MobileAppHeader />
				<div className="mt-5 flex items-center justify-between gap-4">
					<div className="min-w-0">
						<h1 className="v2-mobile-title">Cerita kamu</h1>
						<p className="v2-mobile-description mt-1">
							Pilih sesi untuk lanjut ngobrol dengan AXIS.
						</p>
					</div>
					<button
						type="button"
						onClick={onNewChat}
						aria-label="Chat baru"
						className="v2-anim-pressable grid h-[52px] w-[52px] shrink-0 place-items-center rounded-full bg-[var(--v2-olive)] text-white shadow-[0_14px_28px_rgb(83_67_46_/_0.16)]"
					>
						<MessageCirclePlus
							className="h-[25px] w-[25px]"
							strokeWidth={2.1}
						/>
					</button>
				</div>
			</section>

			<label
				className={`mt-5 flex h-[48px] items-center gap-3 rounded-[18px] border border-[var(--v2-line)] bg-[#fffaf3]/88 px-4 shadow-[0_10px_28px_rgb(83_67_46_/_0.04)] ${animationClasses.staggerItem}`}
				style={motionStyleVars({ delayMs: 95 })}
			>
				<Search
					className="h-[19px] w-[19px] shrink-0 text-[var(--v2-muted)]"
					strokeWidth={2.2}
				/>
				<input
					value={searchQuery}
					onChange={(event) => onSearchChange(event.target.value)}
					placeholder="Cari sesi atau pesan..."
					className="min-w-0 flex-1 bg-transparent text-[14px] font-medium text-[var(--v2-ink)] outline-none placeholder:text-[var(--v2-placeholder)]"
				/>
			</label>

			{conversations.length ? (
				<div className="mt-5 space-y-5">
					{grouped.today.length ? (
						<SessionGroup
							title="Hari ini"
							count={grouped.today.length}
							action={
								grouped.today.length > 2 ? (
									<button
										type="button"
										onClick={() => setShowAllToday((value) => !value)}
										aria-label={
											showAllToday
												? "Tampilkan lebih sedikit sesi"
												: "Tampilkan lebih banyak sesi"
										}
										className="v2-anim-pressable grid h-8 w-8 place-items-center rounded-full text-[var(--v2-olive-deep)]"
									>
										{showAllToday ? (
											<ChevronUp className="h-5 w-5" strokeWidth={2.5} />
										) : (
											<ChevronDown className="h-5 w-5" strokeWidth={2.5} />
										)}
									</button>
								) : null
							}
						>
							<div className="space-y-3">
								{visibleToday.map((conversation, index) => (
									<SessionFeatureCard
										key={conversation.id}
										conversation={conversation}
										index={index}
										onClick={() => onChoose(conversation.id)}
									/>
								))}
							</div>
						</SessionGroup>
					) : null}

					{grouped.previous.length ? (
						<SessionGroup
							title="Sebelumnya"
							count={grouped.previous.length}
							action={
								grouped.previous.length > 4 ? (
									<button
										type="button"
										onClick={() => setShowAllPrevious((value) => !value)}
										aria-label={
											showAllPrevious
												? "Tampilkan lebih sedikit sesi"
												: "Tampilkan lebih banyak sesi"
										}
										className="v2-anim-pressable grid h-8 w-8 place-items-center rounded-full text-[var(--v2-olive-deep)]"
									>
										{showAllPrevious ? (
											<ChevronUp className="h-5 w-5" strokeWidth={2.5} />
										) : (
											<ChevronDown className="h-5 w-5" strokeWidth={2.5} />
										)}
									</button>
								) : null
							}
						>
							<div className="overflow-hidden rounded-[22px] border border-[var(--v2-line)] bg-[#fffaf3]/62">
								{visiblePrevious.map((conversation, index) => (
									<SessionCompactRow
										key={conversation.id}
										conversation={conversation}
										index={index}
										onClick={() => onChoose(conversation.id)}
									/>
								))}
							</div>
						</SessionGroup>
					) : null}
				</div>
			) : (
				<EmptySessionState onNewChat={onNewChat} />
			)}
		</main>
	);
}

function SessionGroup({
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
			<div className="mb-2.5 flex items-center justify-between gap-3">
				<div className="flex items-center gap-2.5">
					<h2 className="v2-section-heading">{title}</h2>
					<span className="rounded-full bg-[var(--v2-olive-soft)] px-2.5 py-0.5 text-[11.5px] font-bold text-[var(--v2-olive-deep)]">
						{count}
					</span>
				</div>
				{action}
			</div>
			{children}
		</section>
	);
}

function SessionFeatureCard({
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
			className={`v2-anim-pressable flex w-full items-center gap-3.5 rounded-[20px] border border-[var(--v2-line)] bg-[#fffaf3]/78 px-4 py-3.5 text-left shadow-[0_12px_30px_rgb(83_67_46_/_0.05)] ${animationClasses.staggerItem}`}
			style={motionStyleVars({ delayMs: 195 + index * 40 })}
		>
			<div className="min-w-0 flex-1">
				<div className="flex items-center gap-2">
					<p className="line-clamp-1 text-[16px] font-bold leading-tight text-[var(--v2-ink)]">
						{conversation.title || "Cerita baru"}
					</p>
					<SessionBadge conversation={conversation} />
				</div>
				<p className="mt-1.5 line-clamp-2 text-[13px] font-medium leading-[1.5] text-[var(--v2-muted)]">
					{conversation.preview || "Belum ada pesan."}
				</p>
			</div>
			<div className="flex shrink-0 flex-col items-end gap-5">
				<span className="text-[12px] font-bold text-[var(--v2-muted)]">
					{formatSessionTime(
						conversation.lastMessageAt || conversation.updatedAt,
					)}
				</span>
				<ChevronRight
					className="h-5 w-5 text-[var(--v2-muted)]"
					strokeWidth={2.4}
				/>
			</div>
		</button>
	);
}

function SessionCompactRow({
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
			className={`v2-anim-pressable flex w-full items-start gap-3 border-b border-[var(--v2-line)] px-4 py-3.5 text-left last:border-b-0 ${animationClasses.staggerItem}`}
			style={motionStyleVars({ delayMs: 210 + index * 30 })}
		>
			<div className="min-w-0 flex-1">
				<div className="flex items-start justify-between gap-3">
					<p className="line-clamp-1 text-[15.5px] font-bold leading-tight text-[var(--v2-ink)]">
						{conversation.title || "Cerita baru"}
					</p>
					<span className="shrink-0 text-[12px] font-bold text-[var(--v2-muted)]">
						{formatSessionTime(
							conversation.lastMessageAt || conversation.updatedAt,
						)}
					</span>
				</div>
				<div className="mt-2 flex items-start justify-between gap-3">
					<p className="line-clamp-2 text-[13px] font-medium leading-[1.4] text-[var(--v2-muted)]">
						{conversation.preview || "Belum ada pesan."}
					</p>
					<SessionBadge conversation={conversation} compact />
				</div>
			</div>
		</button>
	);
}

function SessionBadge({
	conversation,
	compact = false,
}: {
	conversation: Conversation;
	compact?: boolean;
}) {
	const label = getSessionBadge(conversation);
	if (!label) return null;
	return (
		<span
			className={`shrink-0 rounded-full bg-[var(--v2-olive-soft)] font-bold text-[var(--v2-olive-deep)] ${
				compact ? "px-2.5 py-1 text-[11px]" : "px-3 py-1 text-[11px]"
			}`}
		>
			{label}
		</span>
	);
}

function EmptySessionState({ onNewChat }: { onNewChat: () => void }) {
	return (
		<section
			className={`mt-8 rounded-[28px] border border-[var(--v2-line)] bg-[#fffaf3]/72 px-6 py-9 text-center shadow-[0_14px_34px_rgb(83_67_46_/_0.05)] ${animationClasses.cardEnter}`}
			style={motionStyleVars({ delayMs: 160 })}
		>
			<p className="text-[18px] font-bold text-[var(--v2-ink)]">
				Belum ada sesi
			</p>
			<p className="mx-auto mt-3 max-w-[260px] text-[13px] font-medium leading-[1.55] text-[var(--v2-muted)]">
				Mulai cerita baru saat kamu siap. AXIS akan menyimpan percakapanmu
				sebagai sesi.
			</p>
			<button
				type="button"
				onClick={onNewChat}
				className="v2-button v2-button-secondary mt-6 min-h-[46px] px-5 text-[14px]"
			>
				Mulai cerita baru
			</button>
		</section>
	);
}

function groupConversations(conversations: Conversation[]): {
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

function getSessionBadge(conversation: Conversation): string {
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

function formatSessionTime(value: number | string | Date | undefined): string {
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
