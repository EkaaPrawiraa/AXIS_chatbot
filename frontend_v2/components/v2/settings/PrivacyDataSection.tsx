import { ShieldCheck } from '@/lib/assets';
import { SectionHeading, ActionRow } from './SettingsComponents';
import { settingsStyles } from '@/lib/styles/settingsStyles';
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
		<div className={settingsStyles.sectionContainer}>
			<SectionHeading
				Icon={ShieldCheck}
				title="Privasi & data"
				subtitle="Kelola informasi pribadi dan aktivitas kamu."
			/>
			<div className={settingsStyles.listWrapper}>
				<ActionRow
					title="Unduh data saya"
					helper="Unduh riwayat dan data yang tersimpan di AXIS."
					onClick={() => void downloadMyData()}
				/>
				<ActionRow
					title="Hapus riwayat percakapan"
					helper="Bersihkan riwayat percakapan secara permanen."
					onClick={() => void clearHistory()}
				/>
			</div>
		</div>
	);
}
