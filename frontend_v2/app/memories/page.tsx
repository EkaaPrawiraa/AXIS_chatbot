"use client";

import Image from "next/image";
import {
	Check,
	Eye,
	EyeOff,
	ILLUSTRATIONS,
	Info,
	Loader2,
	Lock,
	Plus,
	Search,
	ShieldCheck,
	Sparkles,
	Trash2,
	User,
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
			<main className="space-y-3.5 pb-6">
				<MobileAppHeader />

				<div>
					<h1 className="v2-mobile-title">Memori Kamu</h1>
					<p className="v2-mobile-description mt-0.5">
						Tempat aman untuk mengenal dirimu lebih dalam.
					</p>
				</div>

				<div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
					{NODE_TYPES.map((item) => (
						<button
							key={item.type}
							onClick={() => setNodeType(item.type)}
							className={`h-[24px] shrink-0 whitespace-nowrap rounded-full border px-2.5 text-[11px] font-semibold ${
								nodeType === item.type
									? "border-[var(--v2-olive)] bg-[var(--v2-olive)] text-white"
									: "border-[#e3dccb] bg-transparent text-[var(--v2-ink)]"
							}`}
						>
							{item.label}
						</button>
					))}
				</div>

				<div className="flex items-center gap-2.5">
					<label className="relative min-w-0 flex-1">
						<Search className="absolute left-3 top-1/2 h-[14px] w-[14px] -translate-y-1/2 text-[var(--v2-muted)]" />
						<input
							value={searchQuery}
							onChange={(event) => setSearchQuery(event.target.value)}
							placeholder="Cari memori kamu..."
							className="h-[32px] w-full rounded-full border border-[#e7e0d0] bg-[#fbf7ef] pl-8 pr-3 text-[11.5px] font-medium text-[var(--v2-ink)] outline-none placeholder:text-[#a09a8d]"
						/>
					</label>
					<button
						onClick={() => setShowGuide((value) => !value)}
						aria-pressed={showGuide}
						aria-label={
							showGuide
								? "Sembunyikan penjelasan memori"
								: "Tampilkan penjelasan memori"
						}
						className={`grid h-[32px] w-[32px] shrink-0 place-items-center rounded-full border text-[var(--v2-ink)] transition-colors ${
							showGuide
								? "border-[var(--v2-olive)] bg-[var(--v2-olive)] text-white"
								: "border-[#e7e0d0] bg-[#fbf7ef]"
						}`}
					>
						<Info className="h-[15px] w-[15px]" strokeWidth={2.25} />
					</button>
					<button
						onClick={() => setShowSensitive((value) => !value)}
						className="flex h-[32px] shrink-0 items-center gap-1 rounded-full bg-[#f1ecdf] px-2.5 text-[11px] font-semibold text-[var(--v2-ink)]"
					>
						{showSensitive ? (
							<EyeOff className="h-[14px] w-[14px]" />
						) : (
							<Eye className="h-[14px] w-[14px]" />
						)}
						{showSensitive ? "Tampilkan sensitif" : "Sembunyikan sensitif"}
					</button>
				</div>

				{showGuide ? (
					<>
						<section className="relative flex items-center gap-3 overflow-hidden rounded-[18px] bg-[#f4f1e6] p-3 pr-[64px]">
							<span className="grid h-[40px] w-[40px] shrink-0 place-items-center rounded-full bg-[var(--v2-olive)] text-white">
								<Image
									src={ILLUSTRATIONS.memoryBook}
									alt=""
									width={140}
									height={155}
									className="h-[48px] w-auto shrink-0"
								/>
							</span>
							<div className="min-w-0">
								<h2 className="text-[13.5px] font-bold text-[#5c6549]">
									Tentang apa memori ini?
								</h2>
								<p className="mt-0.5 text-[11.5px] font-medium leading-[1.45] text-[#5f5b52]">
									{activeGuide?.description}
								</p>
							</div>
							<Image
								src={ILLUSTRATIONS.memoryLeaf}
								alt=""
								width={95}
								height={110}
								className="absolute -right-1 top-1/2 h-[64px] w-auto -translate-y-1/2"
							/>
						</section>
					</>
				) : null}

				<section className="space-y-3">
					{isLoading ? (
						<div className="grid min-h-40 place-items-center text-[var(--v2-muted)]">
							<Loader2 className="h-6 w-6 animate-spin" />
						</div>
					) : (
						<>
							{hiddenSensitive.length ? (
								<div className="flex items-center gap-3 rounded-[18px] bg-[#f0ede0] p-3">
									<span className="grid h-[46px] w-[46px] shrink-0 place-items-center rounded-full bg-[#e4e4d0]">
										<Lock className="h-[21px] w-[21px] text-[#4f6138]" />
									</span>
									<div className="min-w-0 flex-1">
										<p className="text-[13.5px] font-bold text-[var(--v2-ink)]">
											{hiddenSensitive.length} memori sensitif disembunyikan
										</p>
										<p className="text-[11.5px] font-medium leading-snug text-[#6f6a5e]">
											Memori yang kamu tandai sebagai sensitif tidak ditampilkan saat ini.
										</p>
									</div>
									<button
										onClick={() => setShowSensitive(true)}
										className="v2-anim-pressable shrink-0 rounded-full bg-[#e2e5cf] px-3.5 py-1.5 text-[12px] font-bold text-[#4f6138]"
									>
										Tampilkan
									</button>
								</div>
							) : null}

							{visibleNodes.length ? (
								visibleNodes.map((node) => (
									<MemoryCard
										key={node.id}
										node={node}
										hideSensitive={false}
										onOpen={() => setSelected(node)}
									/>
								))
							) : (
								<div className="rounded-[22px] border border-[#efe8d9] bg-[#faf5ec] px-5 pb-5 pt-3 text-center">
									<Image
										src={ILLUSTRATIONS.memoryEmpty}
										alt=""
										width={375}
										height={260}
										className="mx-auto h-[150px] w-auto"
									/>
									<p className="text-[17.5px] font-bold text-[var(--v2-ink)]">
										Belum ada memori di kategori ini
									</p>
									<p className="mx-auto mt-1 max-w-[290px] text-[12.5px] font-medium leading-snug text-[#6f6a5e]">
										Yuk, mulai catat hal-hal penting dalam hidupmu. Setiap memori, sekecil apa pun, berarti untukmu.
									</p>
									<button
										onClick={() => router.push("/chat")}
										className="v2-anim-pressable mx-auto mt-3.5 flex h-[44px] w-[min(100%,230px)] items-center justify-center gap-2 rounded-full bg-[var(--v2-clay)] text-[14.5px] font-bold text-white shadow-[0_14px_26px_-14px_rgba(195,108,69,0.9)]"
									>
										<Plus className="h-[17px] w-[17px]" /> Buat memori baru
									</button>
								</div>
							)}

							{hiddenSensitive.length ? (
								<div className="rounded-[20px] border border-[#ece4d3] bg-[#faf5ec] p-3">
									<p className="flex items-center gap-2 text-[13px] font-bold text-[var(--v2-ink)]">
										<Lock className="h-[14px] w-[14px]" /> Memori sensitif yang disembunyikan
									</p>
									<div className="mt-2.5 space-y-2">
										{hiddenSensitive.slice(0, 3).map((node) => (
											<div
												key={node.id}
												className="flex items-center gap-3 rounded-[14px] border border-[#eee6d6] bg-[#fdfaf3] p-2"
											>
												<span className="grid h-[52px] w-[56px] shrink-0 place-items-center rounded-[10px] bg-[#b9ac97]/60 backdrop-blur">
													<Lock className="h-[18px] w-[18px] text-white" />
												</span>
												<div className="min-w-0 flex-1 space-y-1.5" aria-hidden>
													<span className="block h-[9px] w-[82%] rounded-full bg-[#e8e0cd]" />
													<span className="block h-[9px] w-[55%] rounded-full bg-[#ede6d5]" />
												</div>
												<button
													onClick={() =>
														setRevealedIds((current) => new Set(current).add(node.id))
													}
													className="v2-anim-pressable shrink-0 rounded-full bg-[#e2e5cf] px-3 py-1.5 text-[11.5px] font-bold text-[#4f6138]"
												>
													Tampilkan
												</button>
											</div>
										))}
									</div>
									<p className="mt-2.5 flex items-center justify-center gap-1.5 text-[11.5px] font-medium text-[#6f6a5e]">
										<ShieldCheck className="h-[13px] w-[13px]" /> Hanya kamu yang bisa melihat memori sensitif ini.
									</p>
								</div>
							) : null}
						</>
					)}

					<button
						onClick={resetMemory}
						className="mx-auto flex items-center gap-1.5 pt-1 text-[12px] font-semibold text-[var(--v2-muted)]"
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
