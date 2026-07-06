"use client";

import { CONCEPT_ICONS, ExternalLink, GraduationCap } from "@/lib/assets";
import { V2Shell } from "@/components/v2/V2Shell";
import { MobileAppHeader } from "@/components/v2/MobileAppHeader";
import { HeroCard } from "@/components/v2/HeroCard";
import { QuickActionCard } from "@/components/v2/QuickActionCard";
import { InsightCard } from "@/components/v2/InsightCard";
import { MoodCheckCard } from "@/components/v2/MoodCheckCard";
import { animationClasses, motionStyleVars } from "@/lib/animations";
import { useSessionStore } from "@/stores";
import { evaluationFormUrl } from "@/lib/evaluationForm";
import { useMemoryNodes, useMemoryRelations } from "@/hooks";
import { deriveLatestTopicInsight } from "@/lib/dashboardInsight";
import { useMemo } from "react";

export default function HomePage() {
	const user = useSessionStore((state) => state.user);
	const userId = useSessionStore((state) => state.userId);
	const name = user?.displayName || "teman";

	const { data: topicsData } = useMemoryNodes(userId, "topic");
	const { data: relationsData } = useMemoryRelations(userId);
	// Fetched only to check `sensitivity_level` on nodes connected to topics —
	// see dashboardInsight.ts for why the topic-safety filtering needs this.
	const { data: experiencesData } = useMemoryNodes(userId, "experience");
	const { data: emotionsData } = useMemoryNodes(userId, "emotion");
	const { data: thoughtsData } = useMemoryNodes(userId, "thought");

	const connectedNodesById = useMemo(() => {
		const map = new Map();
		for (const node of [
			...(experiencesData?.nodes || []),
			...(emotionsData?.nodes || []),
			...(thoughtsData?.nodes || []),
		]) {
			map.set(node.id, node);
		}
		return map;
	}, [experiencesData, emotionsData, thoughtsData]);

	const insight = deriveLatestTopicInsight(
		topicsData?.nodes || [],
		relationsData?.relations || [],
		connectedNodesById,
	);

	return (
		<V2Shell showTopbar={false}>
			<main
				className={`space-y-3 pb-[124px] pt-0 ${animationClasses.pageEnter}`}
				style={motionStyleVars({ durationMs: 360 })}
			>
				<div
					className={animationClasses.staggerItem}
					style={motionStyleVars({ delayMs: 40 })}
				>
					<MobileAppHeader />
				</div>

				<section
					className={animationClasses.staggerItem}
					style={motionStyleVars({ delayMs: 90 })}
				>
					<h1 className="v2-mobile-title">
						Hai, {name} <span aria-hidden></span>
					</h1>
					<p className="v2-mobile-description mt-1 text-[#55524a]">
						Senang kamu di sini.
						<br />
						{/* Kamu nggak harus sendiri hari ini. */}
					</p>
				</section>

				<HeroCard
					className={animationClasses.heroEnter}
					style={motionStyleVars({ delayMs: 140 })}
					title="Lanjut cerita"
					body="Aku di sini, siap dengerin kapan pun kamu mau."
					ctaLabel="Lanjut cerita"
					href="/chat"
				/>

				<section
					className={animationClasses.staggerItem}
					style={motionStyleVars({ delayMs: 210 })}
				>
					<h2 className="v2-section-heading">Aksi cepat</h2>
					<div className="mt-1.5 grid grid-cols-4 gap-2.5">
						<QuickActionCard
							className={animationClasses.staggerItem}
							style={motionStyleVars({ delayMs: 300 })}
							href="/confession-space"
							label="Curhat"
							icon={
								<CONCEPT_ICONS.confession
									className="h-[22px] w-[22px] text-[var(--v2-clay)]"
									strokeWidth={2.2}
									fill="var(--v2-clay)"
								/>
							}
						/>
						<QuickActionCard
							className={animationClasses.staggerItem}
							style={motionStyleVars({ delayMs: 340 })}
							href="/knowledge-graph"
							label="Peta Memori"
							icon={
								<CONCEPT_ICONS.knowledgeGraph
									className="h-[22px] w-[22px] text-[#fdf8f0]"
									strokeWidth={2}
									fill="var(--v2-olive)"
								/>
							}
						/>
						<QuickActionCard
							className={animationClasses.staggerItem}
							style={motionStyleVars({ delayMs: 380 })}
							href="/help"
							label="Bantuan"
							icon={
								<CONCEPT_ICONS.bantuan
									className="h-[22px] w-[22px] text-[#c21807]"
									strokeWidth={2.2}
								/>
							}
						/>

						<QuickActionCard
							className={animationClasses.staggerItem}
							style={motionStyleVars({ delayMs: 260 })}
							href="/settings"
							label="Pengaturan"
							icon={
								<CONCEPT_ICONS.pengaturan
									className="h-[22px] w-[22px] text-[var(--v2-olive-deep)]"
									strokeWidth={2}
								/>
							}
						/>
					</div>
				</section>

				{insight ? (
					<InsightCard
						className={animationClasses.cardEnter}
						style={motionStyleVars({ delayMs: 430 })}
						title={insight.title}
						body={insight.body}
						linkLabel="Lanjut dari sini"
						href="/chat"
					/>
				) : null}

				<MoodCheckCard
					className={animationClasses.cardEnter}
					style={motionStyleVars({ delayMs: 500 })}
				/>

				<section
					className={`relative rounded-[24px] border border-[var(--v2-line)] bg-[#fffaf3]/76 p-4 shadow-[0_14px_34px_rgb(83_67_46_/_0.06)] ${animationClasses.cardEnter}`}
					style={motionStyleVars({ delayMs: 560 })}
				>
					<div className="flex items-start gap-3 pr-5">
						<div className="grid h-[48px] w-[48px] shrink-0 place-items-center rounded-full bg-[var(--v2-olive-soft)] text-[var(--v2-olive-deep)]">
							<GraduationCap className="h-[24px] w-[24px]" strokeWidth={2.1} />
						</div>
						<div className="min-w-0">
							<p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--v2-olive-deep)]">
								Tentang proyek
							</p>
							<h2 className="mt-1 text-[17.5px] font-bold leading-[1.25] text-[var(--v2-ink)]">
								AXIS dikembangkan sebagai tugas akhir.
							</h2>
							{/* <dl className="mt-3 grid gap-2.5 text-[12.5px] leading-snug">
                <InfoRow label="Pembuat" value="Mohammad Nugraha Eka Prawira" />
                <InfoRow label="NIM" value="13522001" />
                <InfoRow label="Program Studi" value="Teknik Informatika, STEI ITB" />
                <InfoRow label="Pembimbing" value="Dr. Agung Dewandaru, S.T., M.Sc." />
              </dl> */}

							<dl className="mt-3 grid gap-2.5 text-[12.5px] leading-snug">
								<InfoRow
									label="Pembuat"
									value={
										<span className="inline-flex flex-wrap items-center gap-1.5">
											<a
												href="https://www.linkedin.com/in/mohammad-nugraha-eka-prawira-8440b9149"
												target="_blank"
												rel="noopener noreferrer"
												className="underline underline-offset-2 hover:opacity-80"
											>
												Mohammad Nugraha Eka Prawira
											</a>

											<span className="font-semibold text-[var(--v2-muted)]">
												·
											</span>

											<a
												href="mailto:emailkamu@gmail.com"
												className="underline underline-offset-2 hover:opacity-80"
											>
												Gmail
											</a>
										</span>
									}
								/>

								<InfoRow label="NIM" value="13522001" />
								<InfoRow
									label="Program Studi"
									value="Teknik Informatika, STEI ITB"
								/>
								<InfoRow
									label="Pembimbing"
									value="Dr. Agung Dewandaru, S.T., M.Sc."
								/>
							</dl>
							<a
								href={evaluationFormUrl}
								target="_blank"
								rel="noreferrer"
								className="v2-anim-pressable mt-4 inline-flex min-h-9 items-center gap-2 rounded-full bg-[var(--v2-olive-soft)] px-3.5 text-[12.5px] font-bold text-[var(--v2-olive-deep)]"
							>
								Isi kuesioner evaluasi
								<ExternalLink className="h-3.5 w-3.5" strokeWidth={2.3} />
							</a>
						</div>
					</div>
				</section>
			</main>
		</V2Shell>
	);
}

// function InfoRow({ label, value }: { label: string; value: string }) {
//   return (
//     <div>
//       <dt className="font-semibold text-[var(--v2-muted)]">{label}</dt>
//       <dd className="mt-0.5 font-bold text-[var(--v2-ink)]">{value}</dd>
//     </div>
//   );
// }
function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
	return (
		<div>
			<dt className="font-semibold text-[var(--v2-muted)]">{label}</dt>
			<dd className="mt-0.5 font-bold text-[var(--v2-ink)]">{value}</dd>
		</div>
	);
}
