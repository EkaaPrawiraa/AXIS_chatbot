"use client";

import {
	AlertTriangle,
	Check,
	ChevronRight,
	Download,
	Globe,
	MessageCircle,
	RotateCcw,
	ShieldCheck,
	Sprout,
	Trash2,
	Zap,
} from '@/lib/assets';
import { useState } from "react";
import type { ComponentType } from "react";
import { useRouter } from "next/navigation";
import { AuthRequired } from "@/components/session";
import { MobileAppHeader } from "@/components/v2/MobileAppHeader";
import { V2Shell } from "@/components/v2/V2Shell";
import { ResetMemorySheet } from "@/components/v2/settings/ResetMemorySheet";
import { DeleteAccountSheet } from "@/components/v2/settings/DeleteAccountSheet";
import { authAPI } from "@/lib/api/auth";
import { chatAPI } from "@/lib/api/chat";
import { memoryAPI } from "@/lib/api/memory";
import { usePreferencesStore } from "@/stores/preferences";
import { useSessionStore } from "@/stores";

export default function SettingsPage() {
	return (
		<AuthRequired>
			<SettingsContent />
		</AuthRequired>
	);
}

function SettingsContent() {
	const router = useRouter();
	const userId = useSessionStore((state) => state.userId);
	const clearSession = useSessionStore((state) => state.clearSession);
	const language = usePreferencesStore((state) => state.language);
	const setLanguage = usePreferencesStore((state) => state.setLanguage);
	const chatResponseMode = usePreferencesStore(
		(state) => state.chatResponseMode,
	);
	const setChatResponseMode = usePreferencesStore(
		(state) => state.setChatResponseMode,
	);

	const [resetOpen, setResetOpen] = useState(false);
	const [isResetting, setIsResetting] = useState(false);
	const [deleteOpen, setDeleteOpen] = useState(false);
	const [isDeleting, setIsDeleting] = useState(false);
	const [deleteError, setDeleteError] = useState<string | null>(null);
	const [notice, setNotice] = useState<string | null>(null);

	const say = (message: string) => {
		setNotice(message);
		window.setTimeout(
			() => setNotice((current) => (current === message ? null : current)),
			2600,
		);
	};

	const downloadMyData = async () => {
		if (!userId) return;
		say("Menyiapkan data kamu...");
		try {
			const conversations = await chatAPI.getConversations(userId);
			const messages = await Promise.all(
				conversations.slice(0, 50).map(async (conversation) => ({
					conversation,
					messages: await chatAPI
						.getMessages(conversation.id, 1, 200, userId)
						.catch(() => []),
				})),
			);
			const payload = {
				exportedAt: new Date().toISOString(),
				userId,
				conversations: messages,
			};
			const blob = new Blob([JSON.stringify(payload, null, 2)], {
				type: "application/json",
			});
			const url = URL.createObjectURL(blob);
			const anchor = document.createElement("a");
			anchor.href = url;
			anchor.download = `axis-data-${new Date().toISOString().slice(0, 10)}.json`;
			anchor.click();
			URL.revokeObjectURL(url);
			say("Data kamu berhasil diunduh.");
		} catch {
			say("Gagal menyiapkan data. Coba lagi ya.");
		}
	};

	const clearHistory = async () => {
		if (!userId) return;
		if (!window.confirm("Hapus SEMUA riwayat percakapan secara permanen?"))
			return;
		say("Menghapus riwayat...");
		try {
			const conversations = await chatAPI.getConversations(userId);
			for (const conversation of conversations) {
				await chatAPI
					.deleteConversation(conversation.id)
					.catch(() => undefined);
			}
			say("Riwayat percakapan terhapus.");
		} catch {
			say("Sebagian riwayat gagal dihapus.");
		}
	};

	const resetMemory = async () => {
		if (!userId) return;
		setIsResetting(true);
		try {
			await memoryAPI.resetUserMemory(userId);
			setResetOpen(false);
			say("Memori AXIS sudah direset.");
		} catch {
			say("Reset memori gagal. Coba lagi ya.");
		} finally {
			setIsResetting(false);
		}
	};

	const deleteAccount = async (password: string) => {
		if (!userId) return;
		setIsDeleting(true);
		setDeleteError(null);
		try {
			await memoryAPI.purgeAccount(userId).catch(() => undefined);
			await authAPI.deleteAccount(userId, password);
			clearSession();
			router.replace("/auth");
		} catch {
			setDeleteError("Password salah atau terjadi gangguan. Coba lagi ya.");
		} finally {
			setIsDeleting(false);
		}
	};

	return (
		<V2Shell showTopbar={false}>
			<main className="space-y-4 pb-6">
				<MobileAppHeader />

				<div>
					<h1 className="text-[25px] font-bold leading-tight text-[var(--v2-ink)]">
						Pengaturan
					</h1>
					<p className="mt-0.5 text-[12.5px] font-medium text-[var(--v2-muted)]">
						Atur pengalaman AXIS sesuai kebutuhanmu.
					</p>
				</div>

				{notice ? (
					<p className="rounded-[14px] bg-[#eef0e2] px-3.5 py-2 text-[12.5px] font-semibold text-[#4f6138]">
						{notice}
					</p>
				) : null}


				<SectionHeading
					Icon={Globe}
					title="Bahasa"
					// subtitle="Pilih bahasa yang kamu gunakan di aplikasi."
          subtitle="Fitur dalam pengembangan."
				/>
				<div className="divide-y divide-[#ece4d3] rounded-[18px] border border-[#ece4d3] bg-[#fbf7ee]">
					{(
						[
							{ id: "id", label: "Indonesia" },
							{ id: "en", label: "English" },
						] as const
					).map((option) => (
						<button
							key={option.id}
							onClick={() => setLanguage(option.id)}
							className="flex w-full items-center justify-between px-4 py-3"
						>
							<span className="text-[14.5px] font-semibold text-[var(--v2-ink)]">
								{option.label}
							</span>
							<RadioMark active={language === option.id} />
						</button>
					))}
				</div>

				<SectionHeading
					Icon={MessageCircle}
					title="Mode jawaban"
					subtitle="Pilih cara AXIS memberikan jawaban untuk kamu."
				/>
				<div className="divide-y divide-[#ece4d3] rounded-[18px] border border-[#ece4d3] bg-[#fbf7ee]">
					{(
						[
							{
								id: "normal",
								label: "Jawaban muncul sekaligus",
								helper: "AXIS memberikan jawaban lengkap dalam satu balasan.",
								Icon: Zap,
								iconBg: "#f6ead2",
								iconColor: "#d9971d",
							},
							{
								id: "stream",
								label: "Jawaban muncul bertahap",
								helper: "AXIS memberikan jawaban perlahan hingga selesai.",
								Icon: Sprout,
								iconBg: "#e9ecdb",
								iconColor: "#5c7345",
							},
						] as const
					).map((option) => (
						<button
							key={option.id}
							onClick={() => setChatResponseMode(option.id)}
							className="flex w-full items-center gap-3 px-3.5 py-3 text-left"
						>
							<span
								className="grid h-[38px] w-[38px] shrink-0 place-items-center rounded-full"
								style={{ backgroundColor: option.iconBg }}
							>
								<option.Icon
									className="h-[18px] w-[18px]"
									style={{ color: option.iconColor }}
								/>
							</span>
							<span className="min-w-0 flex-1">
								<span className="block text-[14px] font-bold text-[var(--v2-ink)]">
									{option.label}
								</span>
								<span className="block text-[11.5px] font-medium leading-snug text-[#8a8477]">
									{option.helper}
								</span>
							</span>
							<RadioMark active={chatResponseMode === option.id} />
						</button>
					))}
				</div>

				<SectionHeading
					Icon={ShieldCheck}
					title="Privasi & data"
					subtitle="Kelola informasi pribadi dan aktivitas kamu."
					tint="olive"
				/>
				<div className="divide-y divide-[#ece4d3] rounded-[18px] border border-[#ece4d3] bg-[#fbf7ee]">
					<ActionRow
						Icon={Download}
						title="Unduh data saya"
						helper="Unduh riwayat dan data yang tersimpan di AXIS."
						onClick={() => void downloadMyData()}
					/>
					<ActionRow
						Icon={Trash2}
						title="Hapus riwayat percakapan"
						helper="Bersihkan riwayat percakapan secara permanen."
						onClick={() => void clearHistory()}
					/>
				</div>

				<SectionHeading
					Icon={AlertTriangle}
					title="Zona berisiko"
					subtitle="Tindakan ini tidak dapat dibatalkan."
					tint="clay"
				/>
				<div className="divide-y divide-[#f0ddcd] rounded-[18px] border border-[#f0ddcd] bg-[#fbf5ec]">
					<ActionRow
						Icon={RotateCcw}
						title="Reset memori AXIS"
						helper="AXIS akan lupa preferensi dan memori yang tersimpan."
						danger
						onClick={() => setResetOpen(true)}
					/>
					<ActionRow
						Icon={Trash2}
						title="Hapus akun"
						helper="Hapus akun AXIS dan semua data secara permanen."
						danger
						onClick={() => {
							setDeleteError(null);
							setDeleteOpen(true);
						}}
					/>
				</div>

				{resetOpen ? (
					<ResetMemorySheet
						isBusy={isResetting}
						onConfirm={() => void resetMemory()}
						onClose={() => setResetOpen(false)}
					/>
				) : null}

				{deleteOpen ? (
					<DeleteAccountSheet
						isBusy={isDeleting}
						errorMessage={deleteError}
						onConfirm={(password) => void deleteAccount(password)}
						onClose={() => setDeleteOpen(false)}
					/>
				) : null}
			</main>
		</V2Shell>
	);
}

function SectionHeading({
	Icon,
	title,
	subtitle,
	tint = "ink",
}: {
	Icon: ComponentType<{ className?: string }>;
	title: string;
	subtitle: string;
	tint?: "ink" | "olive" | "clay";
}) {
	const circle =
		tint === "clay"
			? "bg-[#f6e3d3] text-[#c05b33]"
			: tint === "olive"
				? "bg-[#e5e7d4] text-[#4f6138]"
				: "bg-[#f1ead9] text-[var(--v2-ink)]";
	return (
		<div className="flex items-center gap-3 pt-1">
			<span
				className={`grid h-[40px] w-[40px] shrink-0 place-items-center rounded-full ${circle}`}
			>
				<Icon className="h-[19px] w-[19px]" />
			</span>
			<div>
				<h2 className="text-[17px] font-bold leading-tight text-[var(--v2-ink)]">
					{title}
				</h2>
				<p className="text-[12px] font-medium text-[#8a8477]">{subtitle}</p>
			</div>
		</div>
	);
}

function RadioMark({ active }: { active: boolean }) {
	return active ? (
		<span className="grid h-[21px] w-[21px] shrink-0 place-items-center rounded-full bg-[#616f51] text-white">
			<Check className="h-[12px] w-[12px]" strokeWidth={3.2} />
		</span>
	) : (
		<span
			className="h-[21px] w-[21px] shrink-0 rounded-full border-[1.5px] border-[#d8cfba]"
			aria-hidden
		/>
	);
}

function ActionRow({
	Icon,
	title,
	helper,
	danger = false,
	onClick,
}: {
	Icon: ComponentType<{ className?: string }>;
	title: string;
	helper: string;
	danger?: boolean;
	onClick: () => void;
}) {
	return (
		<button
			onClick={onClick}
			className="flex w-full items-center gap-3 px-3.5 py-3 text-left"
		>
			<Icon
				className={`h-[19px] w-[19px] shrink-0 ${danger ? "text-[#c05b33]" : "text-[var(--v2-ink)]"}`}
			/>
			<span className="min-w-0 flex-1">
				<span
					className={`block text-[14px] font-bold ${danger ? "text-[#b1502a]" : "text-[var(--v2-ink)]"}`}
				>
					{title}
				</span>
				<span className="block text-[11.5px] font-medium leading-snug text-[#8a8477]">
					{helper}
				</span>
			</span>
			<ChevronRight
				className={`h-[17px] w-[17px] shrink-0 ${danger ? "text-[#c05b33]" : "text-[#8a8477]"}`}
			/>
		</button>
	);
}
