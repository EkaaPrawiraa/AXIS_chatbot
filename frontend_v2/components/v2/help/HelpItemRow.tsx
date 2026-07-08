import Link from "next/link";
import { BookOpen, ChevronDown } from "lucide-react";
import { animationClasses } from "@/lib/animations";
import { helpStyles } from "@/lib/styles/helpStyles";

// Note: Using text colors instead of full backgrounds for a cleaner look.
const TONE_CLASS = {
	olive: "text-[var(--v2-olive-deep)]",
	gold: "text-[var(--v2-c-d59f2e)]",
	clay: "text-[var(--v2-clay)]",
	sage: "text-[var(--v2-olive-deep)]",
	rose: "text-[var(--v2-c-a85f5d)]",
} as const;

export type HelpItemData = {
	id: string;
	href?: string;
	linkLabel?: string;
	externalHref?: string;
	externalLinkLabel?: string;
	title: string;
	body: string;
	summary: string;
	helper?: string;
	icon: React.ComponentType<{ className?: string, strokeWidth?: number }>;
	tone: keyof typeof TONE_CLASS;
};

interface HelpItemRowProps {
	item: HelpItemData;
	open: boolean;
	onToggle: () => void;
}

export function HelpItemRow({ item, open, onToggle }: HelpItemRowProps) {
	const Icon = item.icon;

	return (
		<div className={helpStyles.itemContainer}>
			<button
				type="button"
				onClick={onToggle}
				aria-expanded={open}
				aria-controls={`help-detail-${item.id}`}
				className={helpStyles.itemHeaderBtn}
			>

				<div className={helpStyles.textGroup}>
					<h2 className={helpStyles.titleText}>{item.title}</h2>
					<p className={helpStyles.summaryText}>
						{item.summary}{" "}
						{item.helper ? (
							<span className={helpStyles.helperLink}>
								{item.helper}
							</span>
						) : null}
					</p>
				</div>
				<ChevronDown
					className={`${helpStyles.chevron} ${open ? "rotate-180" : ""}`}
					strokeWidth={2.2}
				/>
			</button>

			{open && (
				<div
					id={`help-detail-${item.id}`}
					className={`${helpStyles.detailContainer} ${animationClasses.softPop}`}
				>
					{item.id === "cbt" ? (
						<ThinkingPracticeDetail item={item} />
					) : (
						<DefaultHelpDetail item={item} />
					)}
				</div>
			)}
		</div>
	);
}

function DefaultHelpDetail({ item }: { item: HelpItemData }) {
	return (
		<>
			<p className={helpStyles.detailBodyText}>
				{item.body}
			</p>
			<HelpDetailActions item={item} />
		</>
	);
}

function ThinkingPracticeDetail({ item }: { item: HelpItemData }) {
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
		<div>
			<p className={helpStyles.detailBodyText}>
				{item.body}
			</p>

			<div className={helpStyles.examplesListWrapper}>
				<p className={helpStyles.examplesListTitle}>
					Contoh latihan yang mungkin ditawarkan:
				</p>
				<ul className={helpStyles.examplesListGroup}>
					{examples.map((example) => (
						<li key={example.label} className={helpStyles.exampleItem}>
							<span className={helpStyles.exampleBullet} />
							<span>
								<span className={helpStyles.exampleLabel}>
									{example.label}:{" "}
								</span>
								{example.description ? (
									example.description
								) : (
									<>
										&quot;{example.before}&quot;{" "}
										<span aria-hidden="true">-&gt;</span> &quot;{example.after}&quot;
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

function HelpDetailActions({ item }: { item: HelpItemData }) {
	if (!item.href && !item.externalHref) return null;

	return (
		<div className={helpStyles.actionsWrapper}>
			{item.href && item.linkLabel ? (
				<Link href={item.href} className={helpStyles.primaryLinkBtn}>
					{item.linkLabel}
				</Link>
			) : null}
			{item.externalHref && item.externalLinkLabel ? (
				<a
					href={item.externalHref}
					target="_blank"
					rel="noreferrer"
					className={helpStyles.externalLinkBtn}
				>
					<BookOpen className={helpStyles.externalLinkIcon} strokeWidth={2.1} />
					{item.externalLinkLabel}
				</a>
			) : null}
		</div>
	);
}
