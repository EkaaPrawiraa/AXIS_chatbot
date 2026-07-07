import { Check, Copy, ShieldCheck } from "lucide-react";
import { profileStyles } from "@/lib/styles/profileStyles";

const formatDate = (dateStr: string) => {
	if (!dateStr) return "-";
	return new Intl.DateTimeFormat("id-ID", {
		dateStyle: "medium",
		timeStyle: "short",
	}).format(new Date(dateStr));
};

interface AccountInfoProps {
	userId: string | undefined;
	user: any;
	copyUserId: () => void;
	savedField: string | null;
}

export function AccountInfo({
	userId,
	user,
	copyUserId,
	savedField,
}: AccountInfoProps) {
	return (
		<section className={profileStyles.sectionHeaderGroup}>
			<p className={profileStyles.sectionTitle}>
				<ShieldCheck className="h-[19px] w-[19px] text-[var(--v2-green-accent)]" />{" "}
				Informasi akun
			</p>
			<dl className={profileStyles.accountInfoContainer}>
				<div className={profileStyles.accountInfoRow}>
					<dt className={profileStyles.accountInfoLabel}>User ID</dt>
					<dd className={profileStyles.accountInfoValueFlex}>
						<span className={profileStyles.accountInfoIdText}>
							{(userId || "-").slice(0, 18)}…
						</span>
						<button
							onClick={copyUserId}
							aria-label="Salin User ID"
							className={profileStyles.accountInfoCopyBtn}
						>
							{savedField === "userid" ? (
								<Check className={profileStyles.accountInfoCopyIconActive} />
							) : (
								<Copy className={profileStyles.accountInfoCopyIcon} />
							)}
						</button>
					</dd>
				</div>
				<div className={profileStyles.accountInfoRow}>
					<dt className={profileStyles.accountInfoLabel}>Dibuat pada</dt>
					<dd className={profileStyles.accountInfoValue}>
						{formatDate(user?.createdAt)}
					</dd>
				</div>
				<div className={profileStyles.accountInfoRow}>
					<dt className={profileStyles.accountInfoLabel}>Diperbarui</dt>
					<dd className={profileStyles.accountInfoValue}>
						{formatDate(user?.updatedAt)}
					</dd>
				</div>
				<div className={profileStyles.accountInfoRow}>
					<dt className={profileStyles.accountInfoLabel}>Akun terverifikasi</dt>
					<dd className={profileStyles.accountInfoValueFlex}>
						<span className={profileStyles.accountInfoVerifiedBadge}>
							<Check className={profileStyles.accountInfoVerifiedIcon} strokeWidth={3.4} />
						</span>
						{user?.safetyTermsAccepted ? "Terverifikasi" : "Belum"}
					</dd>
				</div>
			</dl>
		</section>
	);
}
