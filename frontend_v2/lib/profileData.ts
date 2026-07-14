import { Leaf, Sprout } from "@/lib/assets";

export type CharacterId = "hangat" | "tenang" | "ceria" | "perangkat";

export const TTS_MODELS: Array<{ id: string; name: string; helper: string }> = [
	{
		id: "gemini-3.1-flash-tts",
		name: "AXIS Cepat",
		helper: "Respons suara paling gesit",
	},
	{
		id: "gemini-2.5-pro-tts",
		name: "AXIS Natural",
		helper: "Suara lebih alami dan nyaman didengar",
	},
	{
		id: "gemini-3.5-flash-tts",
		name: "AXIS Klasik",
		helper: "Mesin suara alternatif",
	},
];

export const VOICE_CHARACTERS: Array<{
	id: CharacterId;
	name: string;
	helper: string;
}> = [
	{
		id: "hangat",
		name: "Suara Hangat",
		helper: "Suara lembut dan menenangkan",
	},
	{ id: "tenang", name: "Suara Tenang", helper: "Suara kalem dan stabil" },
	{ id: "ceria", name: "Suara Ceria", helper: "Suara ringan dan bersemangat" },
	{
		id: "perangkat",
		name: "Suara Perangkat",
		helper: "Suara asisten yang netral",
	},
];

export const VOICE_CHARACTER_MAP: Record<
	CharacterId,
	{ female: string; male: string }
> = {
	hangat: { female: "Sulafat", male: "Achird" },
	tenang: { female: "Aoede", male: "Enceladus" },
	ceria: { female: "Puck", male: "Fenrir" },
	perangkat: { female: "Leda", male: "Charon" },
};

export const STYLES: Array<{
	id: string;
	label: string;
	helper: string;
	Icon: typeof Leaf;
}> = [
	{
		id: "gpt-5.4-nano",
		label: "Ringkas",
		helper: "Jawaban singkat, padat, dan respon lebih cepat",
		Icon: Leaf,
	},
	{
		id: "gpt-5.5",
		label: "Reflektif",
		helper: "Jawaban mendalam, penuh empati dan respon lebih lambat",
		Icon: Sprout,
	},
];
