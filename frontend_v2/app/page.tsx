"use client";

import {
	ExternalLink,
	Map as MapIcon,
} from "lucide-react";
import { V2Shell } from "@/components/v2/V2Shell";
import { MobileAppHeader } from "@/components/v2/MobileAppHeader";
import { QuickActionCard } from "@/components/v2/dashboard/QuickActionCard";
import { DashboardCard } from "@/components/v2/dashboard/DashboardCard";
import { MoodCheckCard } from "@/components/v2/dashboard/MoodCheckCard";
import { animationClasses, motionStyleVars } from "@/lib/animations";
import { dashboardStyles } from "@/lib/styles/dashboard";
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
				className={`${dashboardStyles.mainContainer} ${animationClasses.pageEnter}`}
				style={motionStyleVars({ durationMs: 360 })}
			>
				<div
					className={animationClasses.staggerItem}
					style={motionStyleVars({ delayMs: 40 })}
				>
					<MobileAppHeader />
				</div>

				<DashboardCard
					className={animationClasses.staggerItem}
					style={motionStyleVars({ delayMs: 90 })}
					name={name}
					insight={insight}
				/>

				<hr className={dashboardStyles.divider} />

				<section
					className={animationClasses.staggerItem}
					style={motionStyleVars({ delayMs: 210 })}
				>
					<h2 className={dashboardStyles.sectionHeading}>
						JELAJAHI AXIS
					</h2>
					<div className={dashboardStyles.quickActionList}>
						<QuickActionCard
							className={animationClasses.staggerItem}
							style={motionStyleVars({ delayMs: 260 })}
							href="/confession-space"
							label="Confession Space"
							description="Ceritakan apa saja yang ingin kamu bagi dengan AXIS dengan interaksi suara, percakapan ini tidak akan disimpan."
						/>
						<QuickActionCard
							className={animationClasses.staggerItem}
							style={motionStyleVars({ delayMs: 300 })}
							href="/knowledge-graph"
							label="Peta memori"
							description="Lihat apa yang AXIS pahami tentang dirimu dan bagaimana ingatan tersebut saling terhubung."
						/>
						<QuickActionCard
							className={animationClasses.staggerItem}
							style={motionStyleVars({ delayMs: 340 })}
							href="/help"
							label="Tentang AXIS"
							description="Pelajari lebih lanjut tentang AXIS dan bagaimana ia bekerja."
						/>
						<QuickActionCard
							className={animationClasses.staggerItem}
							style={motionStyleVars({ delayMs: 380 })}
							href="/settings"
							label="Pengaturan"
							description="Sesuaikan pengalaman agar AXIS bisa menemanimu lebih baik."
						/>
					</div>
				</section>

				<hr className={dashboardStyles.divider} />

				<MoodCheckCard
					className={animationClasses.cardEnter}
					style={motionStyleVars({ delayMs: 500 })}
				/>

				<section
					className={`${dashboardStyles.devInfoSection} ${animationClasses.cardEnter}`}
					style={motionStyleVars({ delayMs: 560 })}
				>
					<div>
						<h2 className={dashboardStyles.sectionHeading}>
							Informasi Developer
						</h2>
					</div>

					<dl className={dashboardStyles.infoGrid}>
						<InfoRow label="Pembuat" value="Mohammad Nugraha Eka Prawira" />
						<InfoRow label="NIM" value="13522001" />
						<InfoRow label="Program Studi" value="Teknik Informatika, STEI ITB" />
						<InfoRow label="Pembimbing" value="Dr. Agung Dewandaru, S.T., M.Sc." />
					</dl>

					<a
						href={evaluationFormUrl}
						target="_blank"
						rel="noreferrer"
						className={dashboardStyles.evalButton}
					>
						Isi kuesioner evaluasi
						<ExternalLink className={dashboardStyles.evalIcon} />
					</a>
				</section>
			</main>
		</V2Shell>
	);
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
	return (
		<div className={dashboardStyles.infoRow}>
			<dt className={dashboardStyles.itemTitle}>{label}</dt>
			<dd className={dashboardStyles.itemDescription}>{value}</dd>
		</div>
	);
}

