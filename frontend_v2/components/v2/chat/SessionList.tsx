"use client";

import {
	ChevronDown,
	ChevronRight,
	ChevronUp,
	Plus,
	Search,
} from '@/lib/assets';
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { MobileAppHeader } from "@/components/v2/MobileAppHeader";
import { animationClasses, motionStyleVars } from "@/lib/animations";
import { sessionListStyles } from "@/lib/styles/sessionList";
import type { Conversation } from "@/models";

import { EmptySessionState } from "./session-list/EmptySessionState";
import { SessionGroup } from "./session-list/SessionGroup";
import { SessionListItem } from "./session-list/SessionListItem";
import { groupConversations } from "./session-list/utils";

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
			className={`${sessionListStyles.pageContainer} ${animationClasses.pageEnter}`}
			style={motionStyleVars({ durationMs: 300 })}
		>
			<section
				className={animationClasses.staggerItem}
				style={motionStyleVars({ delayMs: 35 })}
			>
				<MobileAppHeader />
				<div className={sessionListStyles.headerGroup}>
					<div className="min-w-0">
						<h1 className={sessionListStyles.pageTitle}>Cerita kamu</h1>
						<p className={sessionListStyles.pageSubtext}>
							Pilih sesi untuk lanjut ngobrol dengan AXIS.
						</p>
					</div>
					<button
						type="button"
						onClick={onNewChat}
						aria-label="Chat baru"
						className={sessionListStyles.newChatButton}
					>
						<Plus
							className={sessionListStyles.newChatIcon}
							strokeWidth={2.1}
						/>
					</button>
				</div>
			</section>

			<label
				className={`${sessionListStyles.searchBarContainer} ${animationClasses.staggerItem}`}
				style={motionStyleVars({ delayMs: 95 })}
			>
				<Search
					className={sessionListStyles.searchIcon}
					strokeWidth={2.2}
				/>
				<input
					value={searchQuery}
					onChange={(event) => onSearchChange(event.target.value)}
					placeholder="Cari sesi atau pesan..."
					className={sessionListStyles.searchInput}
				/>
			</label>

			{conversations.length ? (
				<div className={sessionListStyles.groupContainer}>
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
										className={sessionListStyles.groupActionButton}
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
							<div>
								{visibleToday.map((conversation, index) => (
									<SessionListItem
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
										className={sessionListStyles.groupActionButton}
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
							<div>
								{visiblePrevious.map((conversation, index) => (
									<SessionListItem
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


