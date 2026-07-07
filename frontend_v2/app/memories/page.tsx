"use client";

import {
	Eye,
	EyeOff,
	Info,
	Loader2,
	Lock,
	Search,
	ShieldCheck,
	Trash2,
} from "@/lib/assets";
import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthRequired } from "@/components/session";
import { MobileAppHeader } from "@/components/v2/MobileAppHeader";
import { V2Shell } from "@/components/v2/V2Shell";
import {
	MemoryCard,
	isSensitiveNode,
} from "@/components/v2/memories/MemoryCard";
import { MemoryEditSheet } from "@/components/v2/memories/MemoryEditSheet";
import { memoryAPI } from "@/lib/api/memory";
import { NODE_TYPES } from "@/lib/memoryNodeTypes";
import type { MemoryNode, MemoryNodeType } from "@/models";
import { useMemoryNodes } from "@/hooks";
import { useSessionStore } from "@/stores";
import { memoryStyles } from "@/lib/styles/memoryStyles";
import { ArrowRight } from "lucide-react";

export default function MemoriesPage() {
	return (
		<AuthRequired>
			<Suspense
				fallback={<main className="v2-screen v2-center">Memuat memori...</main>}
			>
				<MemoriesContent />
			</Suspense>
		</AuthRequired>
	);
}

const VALID_TYPES = new Set(NODE_TYPES.map((item) => item.type));

function MemoriesContent() {
	const userId = useSessionStore((state) => state.userId);
	const searchParams = useSearchParams();
	const initialType = searchParams.get("type") as MemoryNodeType | null;
	const [nodeType, setNodeType] = useState<MemoryNodeType>(
		initialType && VALID_TYPES.has(initialType) ? initialType : "subject",
	);
	const [searchQuery, setSearchQuery] = useState("");
	const [showSensitive, setShowSensitive] = useState(false);
	const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set());
	const router = useRouter();
	const [showGuide, setShowGuide] = useState(true);
	const [selected, setSelected] = useState<MemoryNode | null>(null);
	const { data, isLoading, refetch } = useMemoryNodes(
		userId,
		nodeType,
		searchQuery,
	);
	
	const allNodes = data?.nodes || [];
	const hiddenSensitive = showSensitive
		? []
		: allNodes.filter((node) => isSensitiveNode(node) && !revealedIds.has(node.id));
	const visibleNodes = allNodes.filter((node) => !hiddenSensitive.includes(node));

	const activeGuide = useMemo(
		() => NODE_TYPES.find((item) => item.type === nodeType),
		[nodeType],
	);

	const [isMutating, setIsMutating] = useState(false);

	const saveNode = async (properties: Record<string, unknown>) => {
		if (!userId || !selected) return;
		setIsMutating(true);
		try {
			await memoryAPI.updateMemoryNode(userId, selected.type, selected.id, {
				properties,
			});
			setSelected(null);
			await refetch();
		} finally {
			setIsMutating(false);
		}
	};

	const deleteNode = async () => {
		if (!userId || !selected) return;
		if (!window.confirm("Hapus memori ini?")) return;
		setIsMutating(true);
		try {
			await memoryAPI.deleteMemoryNode(userId, selected.type, selected.id);
			setSelected(null);
			await refetch();
		} finally {
			setIsMutating(false);
		}
	};

	const resetMemory = async () => {
		if (!userId) return;
		if (!window.confirm("Hapus semua memori AXIS untuk akun ini?")) return;
		await memoryAPI.resetUserMemory(userId);
		await refetch();
	};

	return (
		<V2Shell showTopbar={false}>
			<main className={memoryStyles.pageWrapper}>
				<div className={memoryStyles.headerContainer}>
					<MobileAppHeader />
				</div>

				<div className={memoryStyles.pageHeaderWrapper}>
					<div>
						<h1 className={memoryStyles.pageTitle}>Memori Kamu</h1>
						<p className={memoryStyles.pageDescription}>
							Apa yang AXIS pahami tentang dirimu.
						</p>
					</div>
					<button
						onClick={() => setShowGuide((value) => !value)}
						aria-pressed={showGuide}
						aria-label={
							showGuide
								? "Sembunyikan penjelasan memori"
								: "Tampilkan penjelasan memori"
						}
						className={`${memoryStyles.infoButton} ${
							showGuide
								? memoryStyles.infoButtonActive
								: memoryStyles.infoButtonInactive
						}`}
					>
						<Info className="h-[20px] w-[20px]" strokeWidth={2.25} />
					</button>
				</div>

				<div className={memoryStyles.filterScrollWrapper}>
					{NODE_TYPES.map((item) => (
						<button
							key={item.type}
							onClick={() => setNodeType(item.type)}
							className={`${memoryStyles.filterChip} ${
								nodeType === item.type
									? memoryStyles.filterChipActive
									: memoryStyles.filterChipInactive
							}`}
						>
							{item.label}
						</button>
					))}
				</div>

				<div className={memoryStyles.controlsContainer}>
					<label className={memoryStyles.searchWrapper}>
						<Search className={memoryStyles.searchIcon} />
						<input
							value={searchQuery}
							onChange={(event) => setSearchQuery(event.target.value)}
							placeholder="Cari memori kamu..."
							className={memoryStyles.searchInput}
						/>
					</label>


					
					<button
						onClick={() => setShowSensitive((value) => !value)}
						className={memoryStyles.sensitiveToggleBtn}
					>
						{showSensitive ? (
							<EyeOff className="h-[15px] w-[15px]" />
						) : (
							<Eye className="h-[15px] w-[15px]" />
						)}
						{showSensitive ? "Tampilkan" : "Sembunyikan"}
					</button>
					
				</div>

				{showGuide && <GuideBanner activeGuide={activeGuide} />}

				<section className={memoryStyles.contentSection}>
					{isLoading ? (
						<div className={memoryStyles.loadingWrapper}>
							<Loader2 className="h-6 w-6 animate-spin" />
						</div>
					) : (
						<>
							<SensitiveHiddenBanner hiddenSensitive={hiddenSensitive} setRevealedIds={setRevealedIds} />

							{visibleNodes.length ? (
								<div className={memoryStyles.listWrapper}>
									{visibleNodes.map((node) => (
										<MemoryCard
											key={node.id}
											node={node}
											hideSensitive={false}
											onOpen={() => setSelected(node)}
										/>
									))}
								</div>
							) : (
								<EmptyState router={router} />
							)}

							<SensitiveRevealedBanner 
								hiddenSensitive={hiddenSensitive} 
								setSelected={setSelected}
							/>
						</>
					)}

					<button
						onClick={resetMemory}
						className={memoryStyles.resetButton}
					>
						<Trash2 className="h-[13px] w-[13px]" /> Reset semua memori
					</button>
				</section>

				{selected ? (
					<MemoryEditSheet
						key={selected.id}
						node={selected}
						isBusy={isMutating}
						onSave={(properties) => void saveNode(properties)}
						onDelete={() => void deleteNode()}
						onClose={() => setSelected(null)}
					/>
				) : null}
			</main>
		</V2Shell>
	);
}

// Subcomponents

function GuideBanner({ activeGuide }: { activeGuide: any }) {
	if (!activeGuide) return null;
	return (
		<section className={memoryStyles.guideBanner}>
			<div className={memoryStyles.guideHeader}>
				<span className={memoryStyles.guideIconWrapper}>
					<Info className="h-[13px] w-[13px]" strokeWidth={2.5} />
				</span>
				<h2 className={memoryStyles.guideTitle}>Tentang apa memori ini?</h2>
			</div>
			<p className={memoryStyles.guideDescription}>
				{activeGuide.description}
			</p>
		</section>
	);
}

function EmptyState({ router }: { router: any }) {
	return (
		<div className={memoryStyles.emptyStateWrapper}>
			<span className={memoryStyles.emptyStateIconWrapper}>
				<Info className="h-[24px] w-[24px]" strokeWidth={2.5} />
			</span>
			<p className={memoryStyles.emptyStateTitle}>Belum ada memori di kategori ini</p>
			<p className={memoryStyles.emptyStateDescription}>
				Mulai percakapan dan AXIS akan membantu mengingat hal-hal tentang dirimu.
			</p>
			<button
				onClick={() => router.push("/chat")}
				className={memoryStyles.emptyStateButton}
			>
				Ceritakan kepada AXIS <ArrowRight className={memoryStyles.emptyStateIcon} strokeWidth={2.5} />
			</button>
		</div>
	);
}

function SensitiveHiddenBanner({ hiddenSensitive, setRevealedIds }: { hiddenSensitive: MemoryNode[], setRevealedIds: any }) {
	if (!hiddenSensitive.length) return null;
	return (
		<div className={memoryStyles.sensitiveHiddenBanner}>
			<span className={memoryStyles.sensitiveHiddenIconWrapper}>
				<Lock className={memoryStyles.sensitiveHiddenIcon} />
			</span>
			<div className={memoryStyles.sensitiveHiddenTextWrapper}>
				<h3 className={memoryStyles.sensitiveHiddenTitle}>
					{hiddenSensitive.length} memori sensitif terkunci
				</h3>
				<p className={memoryStyles.sensitiveHiddenDescription}>
					Memori yang kamu tandai sensitif tidak ditampilkan saat ini.
				</p>
			</div>
			<button
				onClick={() =>
					setRevealedIds(
						(prev: Set<string>) =>
							new Set([...prev, ...hiddenSensitive.map((n) => n.id)]),
					)
				}
				className={memoryStyles.sensitiveHiddenRevealBtn}
			>
				Tampilkan
			</button>
		</div>
	);
}

function SensitiveRevealedBanner({ hiddenSensitive, setSelected }: { hiddenSensitive: MemoryNode[], setSelected: any }) {
	if (!hiddenSensitive.length) return null;
	return (
		<div className={memoryStyles.sensitiveRevealedBanner}>
			<p className={memoryStyles.sensitiveRevealedHeader}>
				<Lock className="h-[14px] w-[14px]" /> Memori sensitif yang terkunci
			</p>
			<div className={memoryStyles.sensitiveRevealedList}>
				{hiddenSensitive.slice(0, 3).map((node) => (
					<div
						key={node.id}
						className={memoryStyles.sensitiveRevealedItem}
					>
						<span className={memoryStyles.sensitiveRevealedIconWrapper}>
							<Lock className="h-[18px] w-[18px] text-[var(--v2-olive-deep)]" />
						</span>
						<div className={memoryStyles.sensitiveRevealedLinesWrapper}>
							<span className={memoryStyles.sensitiveRevealedLine1} />
							<span className={memoryStyles.sensitiveRevealedLine2} />
						</div>
						<button
							onClick={() => setSelected(node)}
							className={memoryStyles.sensitiveRevealedBtn}
						>
							Tampilkan
						</button>
					</div>
				))}
			</div>
			<p className={memoryStyles.sensitiveFooter}>
				<ShieldCheck className="h-[13px] w-[13px]" /> Hanya kamu yang bisa melihat memori sensitif ini.
			</p>
		</div>
	);
}
