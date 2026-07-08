"use client";

import { useState } from "react";
import {
	BookOpen,
	Heart,
	KnowledgeGraphSvgIcon,
	MessageCircle,
	Mic,
	Shield,
	Sparkles,
	UserCog,
	ShieldAlert,
} from '@/lib/assets';
import { AuthRequired } from "@/components/session";
import { V2Shell } from "@/components/v2/V2Shell";
import { animationClasses, motionStyleVars } from "@/lib/animations";
import { MobileAppHeader } from "@/components/v2/MobileAppHeader";
import { HelpItemData, HelpItemRow } from "@/components/v2/help/HelpItemRow";
import { helpStyles } from "@/lib/styles/helpStyles";

const HELP_ITEMS: HelpItemData[] = [
	{
		id: "chat",
		href: "/chat",
		linkLabel: "Mulai chat",
		title: "Chat dengan AXIS",
		summary: "Ceritakan apa yang sedang kamu pikirkan atau rasakan.",
		body: "Buka halaman Chat, lalu tulis apa saja yang ingin kamu ceritakan. Kamu juga bisa menekan tombol mic untuk mengubah suara menjadi teks. Jika ingin mendengar balasan AXIS, tekan tombol suara pada pesan AXIS.",
		icon: MessageCircle,
		tone: "olive",
	},
	{
		id: "cbt",
		title: "Latihan Refleksi CBT",
		summary: "AXIS bisa membantu kamu melihat pikiran dan perasaan dengan lebih jernih.",
		body: "Saat percakapanmu cocok, AXIS dapat menawarkan latihan seperti reframing, grounding, self compassion, atau thought record. Kamu tidak perlu mengaktifkannya sendiri. Cukup lanjutkan chat seperti biasa, lalu terima latihan jika terasa membantu. Kamu juga bebas menolak.",
		externalHref: "https://share.google/BfCK7xwnx0Bzz28vR",
		externalLinkLabel: "Apa itu CBT?",
		icon: Sparkles,
		tone: "gold",
	},
	{
		id: "phq9",
		linkLabel: "Cek suasana hati",
		title: "Cek Suasana Hati",
		summary: "Jawab beberapa pertanyaan singkat untuk memahami kondisimu belakangan ini.",
		body: "AXIS dapat menawarkan pertanyaan PHQ 9 di dalam chat untuk membantumu mengecek suasana hati selama dua minggu terakhir. Kamu juga bisa memintanya dengan menulis, “mau tes mood”. Jawab dengan pilihan yang tersedia atau dengan bahasamu sendiri. Ini bukan tes wajib, jadi kamu bebas melewatinya.",
		externalHref: "https://share.google/dn4HbtGAEmpKCpeDn",
		externalLinkLabel: "Apa itu PHQ 9?",
		icon: Heart,
		tone: "gold",
	},
	{
		id: "confession-space",
		href: "/confession-space",
		linkLabel: "Buka Confession Space",
		title: "Confession Space",
		summary: "Ruang curhat lewat suara yang tidak disimpan ke memori jangka panjang.",
		body: "Di Confession Space, kamu bisa bercerita langsung lewat suara tanpa mengetik. AXIS akan mendengarkan dan membalas dengan suara, sementara teks percakapan tetap muncul di layar. Sesi ini bersifat sementara, jadi ceritamu tidak masuk ke memori jangka panjang AXIS.",
		icon: Mic,
		tone: "clay",
	},
	{
		id: "memories",
		href: "/memories",
		linkLabel: "Buka Memori",
		title: "Memori",
		summary: "Lihat hal penting yang AXIS ingat dari percakapanmu.",
		body: "AXIS dapat mengingat hal penting yang sering muncul dalam ceritamu, seperti orang, situasi, kebiasaan, atau perasaan tertentu. Di halaman Memori, kamu bisa melihat, mengubah, atau menghapus catatan tersebut kapan saja. Kamu juga bisa menyembunyikan info sensitif agar detail pribadi tidak langsung terlihat di layar.",
		icon: BookOpen,
		tone: "sage",
	},
	{
		id: "graph",
		href: "/knowledge-graph",
		linkLabel: "Buka Peta Memori",
		title: "Peta Memori",
		summary: "Lihat hubungan antar memori dalam bentuk peta sederhana.",
		body: "Peta Memori menampilkan bagaimana beberapa hal dalam ceritamu saling terhubung. Misalnya, perasaan tertentu bisa berkaitan dengan kebiasaan, tempat, atau orang yang sering kamu sebut. Fitur ini tidak wajib digunakan, tetapi bisa membantu kamu melihat pola diri dengan lebih jelas.",
		icon: KnowledgeGraphSvgIcon,
		tone: "olive",
	},
	{
		id: "safety",
		href: "/hotlines",
		linkLabel: "Lihat daftar hotline",
		title: "Keamanan dan Hotline",
		summary: "Temukan bantuan yang lebih tepat saat kamu merasa tidak aman.",
		body: "Jika percakapan menunjukkan tanda bahaya, AXIS akan menampilkan arahan untuk mencari bantuan yang lebih aman dan tepat. AXIS bukan layanan darurat dan bukan pengganti tenaga profesional. Jika kamu atau orang di sekitarmu berada dalam bahaya langsung, segera hubungi layanan darurat atau orang tepercaya.",
		icon: Shield,
		tone: "clay",
	},
	{
		id: "profile",
		href: "/profile",
		linkLabel: "Buka Profil",
		title: "Profil dan Pengaturan",
		summary: "Atur akun dan pengalaman menggunakan AXIS.",
		body: "Di halaman Profil, kamu bisa mengubah nama tampilan, bahasa, dan suara AXIS. Di halaman Pengaturan, kamu bisa menyesuaikan tampilan balasan chat, mengunduh data, menghapus riwayat, atau menghapus akun.",
		icon: UserCog,
		tone: "sage",
	},
	{
		id: "batasan",
		title: "Batasan AXIS",
		summary: "AXIS membantu refleksi, tetapi bukan layanan klinis atau darurat.",
		body: "AXIS dibuat untuk membantu kamu bercerita, memahami perasaan, dan melakukan refleksi mandiri. AXIS tidak memberikan diagnosis, terapi, atau penanganan darurat. Jika kamu sedang dalam kondisi krisis, merasa tidak aman, atau butuh bantuan segera, gunakan halaman Bantuan untuk menghubungi layanan yang lebih tepat.",
		icon: ShieldAlert,
		tone: "rose",
	},
];

export default function HelpPage() {
	const [openId, setOpenId] = useState("chat");

	return (
		<AuthRequired>
			<V2Shell showTopbar={false}>
				<main
					className={`${helpStyles.pageContainer} ${animationClasses.pageEnter}`}
					style={motionStyleVars({ durationMs: 340 })}
				>
					<div
						className={animationClasses.staggerItem}
						style={motionStyleVars({ delayMs: 40 })}
					>
						<MobileAppHeader />
					</div>
					<section
						className={`${helpStyles.headerSection} ${animationClasses.staggerItem}`}
						style={motionStyleVars({ delayMs: 50 })}
					>
						<h1 className={helpStyles.pageTitle}>Bantuan</h1>
						<p className={helpStyles.pageDescription}>
							Temukan bantuan dan pahami fitur AXIS agar kamu nyaman
							menggunakannya.
						</p>
					</section>

					<section className={helpStyles.listWrapper}>
						{HELP_ITEMS.map((item, index) => (
							<div
								key={item.id}
								className={animationClasses.staggerItem}
								style={motionStyleVars({ delayMs: 140 + index * 30 })}
							>
								<HelpItemRow
									item={item}
									open={openId === item.id}
									onToggle={() =>
										setOpenId((current) => (current === item.id ? "" : item.id))
									}
								/>
								{index < HELP_ITEMS.length - 1 && (
									<hr className={helpStyles.divider} />
								)}
							</div>
						))}
					</section>
				</main>
			</V2Shell>
		</AuthRequired>
	);
}
