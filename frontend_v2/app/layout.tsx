import type { Metadata, Viewport } from "next";
import "./globals.css";
import { DesktopWarningBanner } from "@/components/v2/DesktopWarningBanner";
import { Providers } from "@/providers";
import { SITE_URL } from "@/lib/config/site";

export const metadata: Metadata = {
	metadataBase: new URL(SITE_URL),
	title: {
		default: "AXIS | Chatbot Pendamping Mahasiswa Indonesia",
		template: "%s | AXIS",
	},
	description:
		"AXIS adalah chatbot pendamping mahasiswa Indonesia untuk curhat, refleksi emosi, voice interaction, dan memori jangka panjang berbasis knowledge graph.",
	keywords: [
		"AXIS chatbot",
		"chatbot pendamping mahasiswa",
		"chatbot empatik",
		"companionship chatbot",
		"chatbot mahasiswa Indonesia",
		"tugas akhir chatbot ITB",
		"knowledge graph",
		"chatbot curhat mahasiswa",
		"chatbot empatik Indonesia",
	],
	alternates: {
		canonical: "/",
	},
	robots: {
		index: true,
		follow: true,
		googleBot: {
			index: true,
			follow: true,
		},
	},
	openGraph: {
		title: "AXIS | Chatbot Pendamping Mahasiswa Indonesia",
		description:
			"Chatbot pendamping mahasiswa Indonesia untuk curhat, refleksi emosi, voice interaction, dan memori jangka panjang.",
		url: "https://axis-chatbot.my.id",
		siteName: "AXIS",
		type: "website",
	},
};

export const viewport: Viewport = {
	width: "device-width",
	initialScale: 1,
	maximumScale: 1,
};

export default function RootLayout({
	children,
}: Readonly<{ children: React.ReactNode }>) {
	return (
		<html lang="id" suppressHydrationWarning>
			<body>
				<Providers>
					<DesktopWarningBanner />
					{children}
				</Providers>
			</body>
		</html>
	);
}
