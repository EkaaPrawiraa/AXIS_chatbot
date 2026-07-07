import { AlertTriangle, RotateCcw, Trash2 } from '@/lib/assets';
import { SectionHeading, ActionRow } from './SettingsComponents';
import { settingsStyles } from '@/lib/styles/settingsStyles';
import { ResetMemorySheet } from "./ResetMemorySheet";
import { DeleteAccountSheet } from "./DeleteAccountSheet";
import { useState } from 'react';
import { memoryAPI } from '@/lib/api/memory';
import { authAPI } from '@/lib/api/auth';
import { useRouter } from 'next/navigation';

export function DangerZoneSection({
	userId,
	say,
	clearSession,
}: {
	userId: string | null;
	say: (message: string) => void;
	clearSession: () => void;
}) {
	const router = useRouter();
	const [resetOpen, setResetOpen] = useState(false);
	const [isResetting, setIsResetting] = useState(false);
	const [deleteOpen, setDeleteOpen] = useState(false);
	const [isDeleting, setIsDeleting] = useState(false);
	const [deleteError, setDeleteError] = useState<string | null>(null);

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
		<>
			<div className={settingsStyles.sectionContainer}>
				<SectionHeading
					Icon={AlertTriangle}
					title="Zona berisiko"
					subtitle="Tindakan ini tidak dapat dibatalkan."
				/>
				<div className={settingsStyles.listWrapper}>
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
		</>
	);
}
