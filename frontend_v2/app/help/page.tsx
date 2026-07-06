"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
	BookOpen,
	ChevronDown,
	Heart,
	MapPinned,
	MessageCircle,
	Mic,
	Search,
	Shield,
	Sparkles,
	UserCog,
  ShieldAlert,
} from '@/lib/assets';
import { AuthRequired } from "@/components/session";
import { V2Shell } from "@/components/v2/V2Shell";
import { animationClasses, motionStyleVars } from "@/lib/animations";

type HelpItem = {
	id: string;
	href?: string;
	linkLabel?: string;
	externalHref?: string;
	externalLinkLabel?: string;
	title: string;
	body: string;
	summary: string;
	helper?: string;
	icon: typeof MessageCircle;
	tone: keyof typeof TONE_CLASS;
};

const HELP_ITEMS: HelpItem[] = [
	{
		id: "chat",
		href: "/chat",
		linkLabel: "Mulai chat",
		title: "Mengobrol dengan AXIS",
		summary:
			"Butuh teman bicara? Pelajari cara memulai obrolan dan mendapatkan dukungan.",
		body: "Ketik apa saja yang ingin kamu ceritakan di kolom chat, lalu kirim. AXIS akan membalas dan mendengarkan tanpa menghakimi. Kamu bisa lanjut percakapan lama lewat daftar sesi, atau mulai percakapan baru kapan saja dari halaman Chat.",
		icon: MessageCircle,
		tone: "olive",
	},
	{
		id: "cbt",
		title: "Latihan berpikir",
		summary:
			"AXIS bisa menawarkan latihan refleksi seperti reframing, grounding, self-compassion, dan thought record.",
		body: "AXIS kadang menawarkan latihan refleksi yang sesuai dengan situasimu. Kamu tidak perlu mengaktifkan apa pun secara manual. AXIS akan mengenali sinyal dari percakapanmu dan menawarkan latihan yang relevan secara otomatis. Kamu bebas menerima atau menolak, dan AXIS tidak akan memaksa.",
		externalHref: "https://share.google/BfCK7xwnx0Bzz28vR",
		externalLinkLabel: "Apa itu CBT?",
		icon: Sparkles,
		tone: "gold",
	},
	{
		id: "phq9",
		// href: '/chat?mood=check',
		linkLabel: "Cek suasana hati",
		title: "Cek suasana hati",
		summary: "Pahami perasaanmu lewat pertanyaan singkat seperti PHQ-9.",
		// helper: 'Apa itu PHQ-9?',
		body: "Sesekali AXIS akan menawarkan 9 pertanyaan singkat tentang suasana hatimu selama dua minggu terakhir, langsung di dalam chat. Cukup pilih jawaban yang tersedia atau ketik dengan bahasamu sendiri. Ini bukan tes wajib. Kamu bebas menolak, dan hasilnya hanya dipakai untuk memahami kondisimu lebih baik.",
		externalHref: "https://share.google/dn4HbtGAEmpKCpeDn",
		externalLinkLabel: "Apa itu PHQ-9?",
		icon: Heart,
		tone: "gold",
	},
	{
		id: "confession-space",
		href: "/confession-space",
		linkLabel: "Buka Confession Space",
		title: "Confession Space",
		summary: "Curhat lewat suara tanpa disimpan jadi memori jangka panjang.",
		body: "Confession Space adalah ruang aman untuk bercerita lewat suara tanpa perlu mengetik. Kamu cukup bicara, lalu AXIS akan mendengarkan dan merespons dengan suara, sementara transkrip percakapan tetap ditampilkan di layar. Sesi ini bersifat sementara, sehingga ceritamu tidak akan disimpan ke memori jangka panjang AXIS.",
		icon: Mic,
		tone: "clay",
	},
	{
		id: "memories",
		href: "/memories",
		linkLabel: "Buka Memori",
		title: "Memori",
		summary: "Simpan cerita, catatan, dan hal penting yang berarti bagimu.",
		body: "AXIS perlahan mengingat hal-hal penting dari percakapanmu, misalnya orang, situasi, atau perasaan yang sering kamu sebut. Di halaman Memori, kamu bisa melihat, mengubah, atau menghapus catatan ini kapan saja. Ada tombol untuk menyembunyikan info sensitif jika kamu ingin layar tidak menampilkan detail pribadi.",
		icon: BookOpen,
		tone: "sage",
	},
	{
		id: "graph",
		href: "/knowledge-graph",
		linkLabel: "Buka Peta Memori",
		title: "Peta Memori",
		summary: "Lihat hubungan antar kenangan dan pola yang bermakna bagimu.",
		body: "Halaman ini menggambarkan bagaimana memori-memorimu saling berhubungan, misalnya bagaimana satu perasaan bisa terhubung dengan kebiasaan tertentu. Fitur ini berguna untuk melihat pola dalam dirimu secara lebih jelas. Tidak wajib dibuka, tapi bisa membantu refleksi.",
		icon: MapPinned,
		tone: "olive",
	},
	{
		id: "safety",
		href: "/hotlines",
		linkLabel: "Lihat daftar hotline",
		title: "Keamanan & Hotline",
		summary:
			"Pelajari cara menjaga keamanan diri dan temukan kontak bantuan darurat.",
		body: "Jika kamu menulis sesuatu yang menunjukkan kamu dalam bahaya, AXIS akan menampilkan peringatan dan mengarahkanmu ke kontak bantuan profesional. AXIS adalah teman bicara, bukan pengganti layanan darurat atau tenaga profesional. Kalau kamu atau orang di sekitarmu dalam bahaya langsung, hubungi layanan darurat atau orang tepercaya sekarang juga.",
		icon: Shield,
		tone: "clay",
	},
	{
		id: "profile",
		href: "/profile",
		linkLabel: "Buka Profil",
		title: "Profil & Pengaturan",
		summary:
			"Kelola akun, preferensi, dan pengaturan aplikasi sesuai kebutuhanmu.",
		body: "Di halaman Profil, kamu bisa mengubah nama tampilan, bahasa, dan suara yang dipakai AXIS saat bicara. Di halaman Pengaturan, kamu bisa mengubah bahasa, cara balasan chat ditampilkan, mengunduh datamu, atau menghapus riwayat dan akun.",
		icon: UserCog,
		tone: "sage",
	},
	{
		id: "batasan",
		// href: '',
		// linkLabel: 'Batasan AXIS',
		title: "Batasan AXIS",
		summary:
			"AXIS adalah pendamping refleksi non-klinis, bukan pengganti bantuan profesional.",
		body: "AXIS dirancang untuk membantu mahasiswa bercerita, merefleksikan pengalaman, dan mengenali suasana hati secara mandiri. AXIS tidak memberikan diagnosis, terapi, atau penanganan darurat. Jika kamu berada dalam kondisi krisis, merasa tidak aman, atau membutuhkan bantuan segera, gunakan halaman Bantuan untuk menghubungi layanan yang lebih tepat.",
		icon: ShieldAlert,
		tone: "rose",
	},
];

const TONE_CLASS = {
	olive: "bg-[#eef0e4] text-[var(--v2-olive-deep)]",
	gold: "bg-[#f7ead0] text-[#d59f2e]",
	clay: "bg-[#f7e3d8] text-[var(--v2-clay)]",
	sage: "bg-[#ecebe1] text-[var(--v2-olive-deep)]",
  rose: "bg-[#f5e1df] text-[#a85f5d]",
} as const;

export default function HelpPage() {
	const [openId, setOpenId] = useState("chat");
	const [query, setQuery] = useState("");

	const visibleItems = useMemo(() => {
		const normalized = query.trim().toLowerCase();
		if (!normalized) return HELP_ITEMS;
		return HELP_ITEMS.filter((item) =>
			`${item.title} ${item.summary} ${item.body}`
				.toLowerCase()
				.includes(normalized),
		);
	}, [query]);

	return (
		<AuthRequired>
			<V2Shell>
				<main
					className={`space-y-4 pb-[calc(116px+env(safe-area-inset-bottom))] ${animationClasses.pageEnter}`}
					style={motionStyleVars({ durationMs: 340 })}
				>
					<section
						className={animationClasses.staggerItem}
						style={motionStyleVars({ delayMs: 50 })}
					>
						<h1 className="v2-mobile-title mt-1">Bantuan</h1>
						<p className="v2-mobile-description mt-1 w-full text-[#55524a]">
							Temukan bantuan dan pahami fitur AXIS agar kamu nyaman
							menggunakannya.
						</p>
					</section>

					<label
						className={`flex h-[48px] items-center gap-3 rounded-[18px] border border-[var(--v2-line)] bg-[#fffaf3]/88 px-4 shadow-[0_10px_28px_rgb(83_67_46_/_0.04)] ${animationClasses.staggerItem}`}
						style={motionStyleVars({ delayMs: 100 })}
					>
						<Search
							className="h-[19px] w-[19px] shrink-0 text-[var(--v2-muted)]"
							strokeWidth={2.2}
						/>
						<input
							value={query}
							onChange={(event) => setQuery(event.target.value)}
							type="search"
							aria-label="Cari bantuan"
							placeholder="Cari bantuan..."
							className="min-w-0 flex-1 bg-transparent text-[14px] font-medium text-[var(--v2-ink)] outline-none placeholder:text-[var(--v2-placeholder)]"
						/>
					</label>

					<section className="space-y-3 pt-1">
						{visibleItems.map((item, index) => (
							<HelpCard
								key={item.id}
								item={item}
								index={index}
								open={openId === item.id}
								onToggle={() =>
									setOpenId((current) => (current === item.id ? "" : item.id))
								}
							/>
						))}
						{visibleItems.length === 0 ? (
							<div className="rounded-[19px] border border-[var(--v2-line)] bg-[#fffaf3]/74 px-4 py-5 text-center text-[14px] font-medium text-[var(--v2-muted)]">
								Belum ada bantuan yang cocok dengan pencarianmu.
							</div>
						) : null}
					</section>
				</main>
			</V2Shell>
		</AuthRequired>
	);
}

function HelpCard({
	item,
	index,
	open,
	onToggle,
}: {
	item: HelpItem;
	index: number;
	open: boolean;
	onToggle: () => void;
}) {
	const Icon = item.icon;

	return (
		<article
			className={`overflow-hidden rounded-[19px] border border-[var(--v2-line)] bg-[#fffaf3]/74 shadow-[0_12px_30px_rgb(83_67_46_/_0.055)] ${animationClasses.cardEnter}`}
			style={motionStyleVars({ delayMs: 145 + index * 38 })}
		>
			<button
				type="button"
				onClick={onToggle}
				aria-expanded={open}
				aria-controls={`help-detail-${item.id}`}
				className="flex min-h-[92px] w-full items-center gap-3.5 px-4 py-3.5 text-left"
			>
				<div
					className={`grid h-[54px] w-[54px] shrink-0 place-items-center rounded-full ${TONE_CLASS[item.tone]}`}
				>
					<Icon className="h-[27px] w-[27px]" strokeWidth={2.15} />
				</div>
				<div className="min-w-0 flex-1">
					<h2 className="text-[17px] font-bold leading-tight text-[var(--v2-ink)]">
						{item.title}
					</h2>
					<p className="mt-1 text-[13px] font-medium leading-[1.4] text-[#5f5b52]">
						{item.summary}{" "}
						{item.helper ? (
							<span className="font-bold text-[var(--v2-olive-link)] underline underline-offset-4">
								{item.helper}
							</span>
						) : null}
					</p>
				</div>
				<ChevronDown
					className={`h-[20px] w-[20px] shrink-0 text-[var(--v2-ink)] transition-transform duration-200 ${
						open ? "rotate-180" : ""
					}`}
					strokeWidth={2.2}
				/>
			</button>

			{open ? (
				<div
					id={`help-detail-${item.id}`}
					className={`border-t border-[var(--v2-line)] px-4 pb-4 pt-3 ${animationClasses.softPop}`}
				>
					{item.id === "cbt" ? (
						<ThinkingPracticeDetail item={item} />
					) : (
						<DefaultHelpDetail item={item} />
					)}
				</div>
			) : null}
		</article>
	);
}

function DefaultHelpDetail({ item }: { item: HelpItem }) {
	return (
		<>
			<p className="whitespace-pre-line text-[13px] font-medium leading-[1.6] text-[#514d46]">
				{item.body}
			</p>
			<HelpDetailActions item={item} />
		</>
	);
}

function ThinkingPracticeDetail({ item }: { item: HelpItem }) {
	const examples = [
		{
			label: "Reframing",
			before: "Aku selalu gagal",
			after: "Aku sedang belajar dan berkembang",
		},
		{
			label: "Grounding",
			before: "Aku panik",
			after: "Aku tarik napas, fokus pada 5 hal di sekitarku",
		},
		{
			label: "Self-compassion",
			before: "Aku payah",
			after: "Aku berharga dan sedang berusaha",
		},
		{
			label: "Thought record",
			description: "catat pikiran otomatis, emosi, dan bukti pendukung",
		},
	];

	return (
		<div className="space-y-4">
			<p className="text-[13px] font-medium leading-[1.62] text-[#514d46]">
				{item.body}
			</p>

			<div className="space-y-3">
				<p className="text-[13.5px] font-bold leading-tight text-[var(--v2-ink)]">
					Contoh latihan yang mungkin ditawarkan:
				</p>
				<ul className="space-y-3">
					{examples.map((example) => (
						<li
							key={example.label}
							className="flex gap-3 text-[13px] font-medium leading-[1.55] text-[#514d46]"
						>
							<span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-[#d59f2e]" />
							<span>
								<span className="font-bold text-[var(--v2-ink)]">
									{example.label}:{" "}
								</span>
								{example.description ? (
									example.description
								) : (
									<>
										&quot;{example.before}&quot;{" "}
										<span aria-hidden="true">-&gt;</span> &quot;{example.after}
										&quot;
									</>
								)}
							</span>
						</li>
					))}
				</ul>
			</div>

			<HelpDetailActions item={item} />
		</div>
	);
}

function HelpDetailActions({ item }: { item: HelpItem }) {
	return (
		<div className="mt-4 flex flex-wrap items-center gap-3">
			{item.href && item.linkLabel ? (
				<Link
					href={item.href}
					className="v2-anim-pressable inline-flex min-h-9 items-center rounded-full bg-[var(--v2-olive-soft)] px-4 text-[12.5px] font-bold text-[var(--v2-olive-deep)]"
				>
					{item.linkLabel}
				</Link>
			) : null}
			{item.externalHref && item.externalLinkLabel ? (
				<a
					href={item.externalHref}
					target="_blank"
					rel="noreferrer"
					className="v2-anim-pressable inline-flex min-h-9 items-center gap-2 rounded-full px-1 text-[13px] font-bold text-[var(--v2-olive-link)] underline underline-offset-4"
				>
					<BookOpen className="h-4 w-4" strokeWidth={2.1} />
					{item.externalLinkLabel}
				</a>
			) : null}
		</div>
	);
}
