"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthRequired } from "@/components/session";
import { V2Shell } from "@/components/v2/V2Shell";
import { profileAPI } from "@/lib/api/profile";
import { friendlyErrorMessage } from "@/lib/errorMessages";
import { useSessionStore } from "@/stores";
import { useUIStore } from "@/stores/ui";
import { profileStyles } from "@/lib/styles/profileStyles";
import { ProfileAvatar } from "@/components/v2/profile/ProfileAvatar";
import { ProfileSettingsList } from "@/components/v2/profile/ProfileSettingsList";
import { ResponseStyleSelector } from "@/components/v2/profile/ResponseStyleSelector";
import { AccountInfo } from "@/components/v2/profile/AccountInfo";
import { VoiceSelectionSheet } from "@/components/v2/profile/VoiceSelectionSheet";
import { TtsSelectionSheet } from "@/components/v2/profile/TtsSelectionSheet";

export default function ProfilePage() {
	return (
		<AuthRequired>
			<ProfileContent />
		</AuthRequired>
	);
}

function ProfileContent() {
	const router = useRouter();
	const userId = useSessionStore((state) => state.userId);
	const user = useSessionStore((state) => state.user);
	const profile = useSessionStore((state) => state.profile);
	const setProfile = useSessionStore((state) => state.setProfile);
	const clearSession = useSessionStore((state) => state.clearSession);
	const addToast = useUIStore((state) => state.addToast);

	const [language, setLanguage] = useState(
		(profile?.language || user?.preferredLanguage || "id") === "en"
			? "en"
			: "id",
	);
	const [voice, setVoice] = useState(
		profile?.preferredVoiceId || user?.preferredVoiceId || "alloy",
	);
	const [responseModel, setResponseModel] = useState(
		profile?.preferredResponseModel ||
			user?.preferredResponseModel ||
			"gpt-5.4-nano",
	);
	const [voiceSheetOpen, setVoiceSheetOpen] = useState(false);
	const [ttsSheetOpen, setTtsSheetOpen] = useState(false);
	const [ttsModel, setTtsModel] = useState(
		profile?.preferredTtsModel || user?.preferredTtsModel || "v2_5_turbo",
	);
	const [gender, setGender] = useState(
		(profile?.gender || user?.gender || "pria") === "wanita"
			? "wanita"
			: "pria",
	);
	const [savedField, setSavedField] = useState<string | null>(null);
	const [showSavedBanner, setShowSavedBanner] = useState(false);

	const persist = async (
		patch: Partial<{
			name: string;
			language: string;
			voice: string;
			responseModel: string;
			ttsModel: string;
			gender: string;
		}>,
		field: string,
	) => {
		if (!userId) return;
		try {
			const next = await profileAPI.updateProfile(userId, {
				name: patch.name,
				language: patch.language ?? language,
				preferredLanguage: patch.language ?? language,
				preferredVoiceId: patch.voice ?? voice,
				preferredResponseModel: patch.responseModel ?? responseModel,
				preferredTtsModel: patch.ttsModel ?? ttsModel,
				gender: patch.gender ?? gender,
			});
			setProfile(next);
			setSavedField(field);
			setShowSavedBanner(true);
			window.setTimeout(
				() => setSavedField((current) => (current === field ? null : current)),
				2200,
			);
		} catch (error) {
			setSavedField(null);
			addToast(
				friendlyErrorMessage(error, "Gagal menyimpan perubahan, coba lagi ya."),
				"error",
			);
		}
	};

	const chooseStyle = (id: string) => {
		setResponseModel(id);
		persist({ responseModel: id }, "responseModel");
	};

	const chooseVoice = (id: string) => {
		setVoice(id);
		persist({ voice: id }, "voice");
		setVoiceSheetOpen(false);
	};

	const chooseTtsModel = (id: string) => {
		setTtsModel(id);
		persist({ ttsModel: id }, "ttsModel");
		setTtsSheetOpen(false);
	};

	const toggleLanguage = () => {
		const nextLang = language === "id" ? "en" : "id";
		setLanguage(nextLang);
		persist({ language: nextLang }, "language");
	};

	const copyUserId = () => {
		if (!userId) return;
		navigator.clipboard.writeText(userId);
		setSavedField("userid");
		window.setTimeout(
			() => setSavedField((current) => (current === "userid" ? null : current)),
			2000,
		);
		addToast("User ID berhasil disalin!", "success");
	};

	const logout = () => {
		clearSession();
		router.replace("/");
	};

	return (
		<V2Shell>
			{/* Saved Banner Popup */}
			<div
				className={`${profileStyles.savedBannerPopup} ${
					showSavedBanner
						? "translate-y-0 opacity-100"
						: "-translate-y-full opacity-0 pointer-events-none"
				}`}
				onTransitionEnd={() => {
					if (!savedField) setShowSavedBanner(false);
				}}
			>
				Perubahan tersimpan
			</div>

			<main className={profileStyles.mainContainer}>
				<div className={profileStyles.headerContainer}>
					<h1 className={profileStyles.pageTitle}>Profil</h1>
					<p className={profileStyles.pageSubtitle}>
						Sesuaikan identitas dan bagaimana AXIS berinteraksi denganmu.
					</p>
				</div>

				<ProfileAvatar
					user={user}
					profile={profile}
					initialName={profile?.name || user?.displayName || ""}
					onSave={(newName) => persist({ name: newName }, "name")}
					savedField={savedField}
					logout={logout}
				/>

				<ProfileSettingsList
					userEmail={user?.email || ""}
					language={language}
					voice={voice}
					ttsModel={ttsModel}
					setVoiceSheetOpen={setVoiceSheetOpen}
					setTtsSheetOpen={setTtsSheetOpen}
					toggleLanguage={toggleLanguage}
				/>

				<hr className={profileStyles.sectionDivider} />

				<ResponseStyleSelector
					responseModel={responseModel}
					chooseStyle={chooseStyle}
				/>

				<hr className={profileStyles.sectionDivider} />

				<AccountInfo
					userId={userId || undefined}
					user={user}
					copyUserId={copyUserId}
					savedField={savedField}
				/>

				{voiceSheetOpen && (
					<VoiceSelectionSheet
						gender={gender}
						onChooseGender={(g) => {
							setGender(g);
							persist({ gender: g }, "gender");
						}}
						voice={voice}
						ttsModel={ttsModel}
						onChooseVoice={chooseVoice}
						onClose={() => setVoiceSheetOpen(false)}
					/>
				)}

				{ttsSheetOpen && (
					<TtsSelectionSheet
						ttsModel={ttsModel}
						onChooseTtsModel={chooseTtsModel}
						onClose={() => setTtsSheetOpen(false)}
					/>
				)}
			</main>
		</V2Shell>
	);
}
