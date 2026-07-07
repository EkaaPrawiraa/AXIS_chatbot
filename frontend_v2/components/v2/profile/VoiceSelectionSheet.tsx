import React, { useState } from "react";
import { Check, Play, X, Loader2 } from "lucide-react";
import { profileStyles } from "@/lib/styles/profileStyles";
import { VOICE_CHARACTERS } from "@/lib/profileData";
import {
	createAudioPlayer,
	dataUrlFromBase64,
	primeAudioElement,
} from "@/lib/audio";
import { voiceAPI } from "@/lib/api/voice";
import { useUIStore } from "@/stores/ui";

interface VoiceSelectionSheetProps {
	gender: string;
	onChooseGender: (id: string) => void;
	voice: string;
	ttsModel: string;
	onChooseVoice: (id: string) => void;
	onClose: () => void;
}

export function VoiceSelectionSheet({
	gender,
	onChooseGender,
	voice,
	ttsModel,
	onChooseVoice,
	onClose,
}: VoiceSelectionSheetProps) {
	const addToast = useUIStore((state) => state.addToast);
	const [isPlaying, setIsPlaying] = useState<string | null>(null);

	const testVoice = async (id: string, characterName: string) => {
		if (isPlaying === id) return;
		try {
			setIsPlaying(id);
			const primed = primeAudioElement();
			const result = await voiceAPI.synthesize({
				text: `Halo, aku AXIS dengan mode ${characterName}. Senang berkenalan denganmu!`,
				voice_id: id,
				tts_model: ttsModel as any,
				language_pref: "id",
			});

			if (!result.audio_output_base64) throw new Error("no audio returned");
			const src = dataUrlFromBase64(result.audio_output_base64, result.audio_output_format);
			const player = createAudioPlayer(src, undefined, primed);
			await player.done;
		} catch (error) {
			console.error(error);
			addToast("Yah, gagal memutar contoh suara.", "error");
		} finally {
			setIsPlaying(null);
		}
	};

	return (
		<div className={profileStyles.sheetBackdrop} onClick={onClose}>
			<div
				className={profileStyles.sheetContainer}
				onClick={(e) => e.stopPropagation()}
			>
				<div className={profileStyles.sheetHeader}>
					<h3 className={profileStyles.sheetTitle}>Karakter Suara</h3>
					<button
						onClick={onClose}
						aria-label="Tutup"
						className={profileStyles.sheetCloseBtn}
					>
						<X className={profileStyles.sheetCloseIcon} />
					</button>
				</div>
				<div className={profileStyles.sheetGenderToggleGroup}>
					{(["wanita", "pria"] as const).map((id) => (
						<button
							key={id}
							onClick={() => onChooseGender(id)}
							className={`${profileStyles.sheetGenderToggleBtn} ${
								gender === id
									? profileStyles.sheetGenderToggleBtnActive
									: profileStyles.sheetGenderToggleBtnInactive
							}`}
						>
							{id}
						</button>
					))}
				</div>
				<div className={profileStyles.sheetOptionsList}>
					{VOICE_CHARACTERS.map((char) => {
						const mapping = {
							hangat: { female: "Sulafat", male: "Achird" },
							tenang: { female: "Aoede", male: "Enceladus" },
							ceria: { female: "Puck", male: "Fenrir" },
							perangkat: { female: "Leda", male: "Charon" },
						}[char.id as "hangat" | "tenang" | "ceria" | "perangkat"];

						// Pick the voice ID based on the currently selected gender
						const voiceId = gender === "pria" ? mapping.male : mapping.female;
						const active = voice === voiceId;

						return (
							<div
								key={char.id}
								onClick={() => onChooseVoice(voiceId)}
								className={profileStyles.sheetOptionBtn}
							>
								<div className={profileStyles.sheetOptionTextGroup}>
									<p className={profileStyles.sheetOptionTitle}>
										{char.name}
									</p>
									<p className={profileStyles.sheetOptionHelper}>
										{char.helper}
									</p>
								</div>
								<div className={profileStyles.sheetOptionAccessory}>
									{active ? (
										<Check className={profileStyles.sheetOptionCheck} />
									) : null}
									<button
										onClick={(e) => {
											e.stopPropagation();
											testVoice(voiceId, char.name);
										}}
										className={profileStyles.sheetOptionTestBtn}
									>
										{isPlaying === voiceId ? (
											<Loader2 className="h-4 w-4 animate-spin" />
										) : (
											<Play className="h-4 w-4 ml-0.5" />
										)}
									</button>
								</div>
							</div>
						);
					})}
				</div>
			</div>
		</div>
	);
}
