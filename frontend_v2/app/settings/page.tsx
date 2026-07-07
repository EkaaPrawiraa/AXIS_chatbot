"use client";

import { useState } from "react";
import { AuthRequired } from "@/components/session";
import { V2Shell } from "@/components/v2/V2Shell";
import { settingsStyles } from "@/lib/styles/settingsStyles";
import { useSessionStore } from "@/stores";
import { ResponseModeSection } from "@/components/v2/settings/ResponseModeSection";
import { PrivacyDataSection } from "@/components/v2/settings/PrivacyDataSection";
import { DangerZoneSection } from "@/components/v2/settings/DangerZoneSection";

export default function SettingsPage() {
	return (
		<AuthRequired>
			<SettingsContent />
		</AuthRequired>
	);
}

function SettingsContent() {
	const userId = useSessionStore((state) => state.userId);
	const clearSession = useSessionStore((state) => state.clearSession);

	const [notice, setNotice] = useState<string | null>(null);

	const say = (message: string) => {
		setNotice(message);
		window.setTimeout(
			() => setNotice((current) => (current === message ? null : current)),
			2600,
		);
	};

	return (
		<V2Shell>
			<main className={settingsStyles.mainContainer}>
				<div className={settingsStyles.pageHeaderWrapper}>
					<h1 className={settingsStyles.pageTitle}>
						Pengaturan
					</h1>
					<p className={settingsStyles.pageSubtitle}>
						Atur pengalaman AXIS sesuai kebutuhanmu.
					</p>
				</div>

				{notice ? (
					<p className={settingsStyles.notice}>
						{notice}
					</p>
				) : null}

				<ResponseModeSection />

				<hr className="my-7 border-t border-[var(--v2-line-lighter)]" />

				<PrivacyDataSection userId={userId} say={say} />

				<hr className="my-7 border-t border-[var(--v2-line-lighter)]" />

				<DangerZoneSection userId={userId} say={say} clearSession={clearSession} />
			</main>
		</V2Shell>
	);
}
