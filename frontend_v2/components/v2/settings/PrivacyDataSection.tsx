import { ShieldCheck, Download, Trash2, ChevronRight } from 'lucide-react';
import { profileStyles } from '@/lib/styles/profileStyles';
import { ProfileRow } from '@/components/v2/profile/ProfileRow';
import { chatAPI } from '@/lib/api/chat';

export function PrivacyDataSection({
	userId,
	say,
}: {
	userId: string | null;
	say: (message: string) => void;
}) {
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

	return (
		<section className={profileStyles.sectionHeaderGroup}>
			<p className={profileStyles.sectionTitle}>
				<ShieldCheck className={profileStyles.rowInlineIcon} strokeWidth={2.5} />
				Privasi & data
			</p>
			<p className={profileStyles.sectionSubtitle}>
				Kelola informasi pribadi dan aktivitas kamu.
			</p>
			<div className={profileStyles.settingsListWrapper}>
				<ProfileRow
					Icon={Download}
					label="Ekspor Data"
					value="Unduh data saya"
					helper="Unduh riwayat percakapan yang tersimpan di AXIS."
					accessory={<ChevronRight className="h-[19px] w-[19px] text-[var(--v2-muted-secondary)]" />}
					onClick={() => void downloadMyData()}
				/>
				<ProfileRow
					Icon={Trash2}
					label="Penghapusan"
					value="Hapus riwayat percakapan"
					helper="Bersihkan riwayat percakapan secara permanen."
					accessory={<ChevronRight className="h-[19px] w-[19px] text-[var(--v2-muted-secondary)]" />}
					onClick={() => void clearHistory()}
				/>
			</div>
		</section>
	);
}
