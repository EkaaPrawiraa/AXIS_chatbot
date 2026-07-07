import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
	faLanguage,
	faMicrophoneLines,
	faComments,
	faEnvelopeCircleCheck,
} from "@/lib/assets";
import { ChevronRight } from "lucide-react";
import { ProfileRow } from "@/components/v2/profile/ProfileRow";
import { profileStyles } from "@/lib/styles/profileStyles";
import { CharacterId, TTS_MODELS, VOICE_CHARACTERS, VOICE_CHARACTER_MAP } from "@/lib/profileData";

interface ProfileSettingsListProps {
	userEmail: string;
	language: string;
	voice: string;
	ttsModel: string;
	setVoiceSheetOpen: (val: boolean) => void;
	setTtsSheetOpen: (val: boolean) => void;
	toggleLanguage: () => void;
}

const LANGUAGE_MAP: Record<string, string> = {
	id: "Bahasa Indonesia",
	en: "English",
};

export function ProfileSettingsList({
	userEmail,
	language,
	voice,
	ttsModel,
	setVoiceSheetOpen,
	setTtsSheetOpen,
	toggleLanguage,
}: ProfileSettingsListProps) {
	// Find character name based on voice
	let characterName = "Suara Hangat";
	let characterHelper = "Suara lembut dan menenangkan";
	for (const char of VOICE_CHARACTERS) {
		const mapping = VOICE_CHARACTER_MAP[char.id as CharacterId];
		if (mapping.female === voice || mapping.male === voice) {
			characterName = char.name;
			characterHelper = char.helper;
			break;
		}
	}

	return (
		<div className={profileStyles.settingsListWrapper}>
			<ProfileRow
				Icon={({ className }) => (
					<FontAwesomeIcon icon={faEnvelopeCircleCheck} className={className} />
				)}
				label="Email"
				value={userEmail || "Tidak ada email"}
				helper="Akun terverifikasi"
			/>

			<ProfileRow
				Icon={({ className }) => (
					<FontAwesomeIcon icon={faLanguage} className={className} />
				)}
				label="Bahasa"
				value={LANGUAGE_MAP[language] || "Bahasa Indonesia"}
				helper="Bahasa yang kamu gunakan di AXIS untuk percakapan"
				accessory={
					<ChevronRight className="h-[19px] w-[19px] text-[var(--v2-muted-secondary)]" />
				}
				onClick={toggleLanguage}
			/>

			<ProfileRow
				Icon={({ className }) => (
					<FontAwesomeIcon icon={faMicrophoneLines} className={className} />
				)}
				label="Karakter Suara pilihan"
				value={characterName}
				helper={characterHelper}
				accessory={
					<ChevronRight className="h-[19px] w-[19px] text-[var(--v2-muted-secondary)]" />
				}
				onClick={() => setVoiceSheetOpen(true)}
			/>

			<ProfileRow
				Icon={({ className }) => (
					<FontAwesomeIcon icon={faComments} className={className} />
				)}
				label="Suara Percakapaan"
				value={
					(TTS_MODELS.find((item) => item.id === ttsModel) || TTS_MODELS[0])
						.name
				}
				helper={
					(TTS_MODELS.find((item) => item.id === ttsModel) || TTS_MODELS[0])
						.helper
				}
				accessory={
					<ChevronRight className="h-[19px] w-[19px] text-[var(--v2-muted-secondary)]" />
				}
				onClick={() => setTtsSheetOpen(true)}
			/>
		</div>
	);
}
