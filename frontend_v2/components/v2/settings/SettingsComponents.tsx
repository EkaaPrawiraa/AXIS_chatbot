import { ComponentType } from "react";
import { Check, ChevronRight } from "lucide-react";
import { settingsStyles } from "@/lib/styles/settingsStyles";

export function SectionHeading({
	Icon,
	title,
	subtitle,
}: {
	Icon?: ComponentType<{ className?: string; strokeWidth?: number }>;
	title: string;
	subtitle: string;
}) {
	return (
		<div className={settingsStyles.sectionHeadingGroup}>
			<h2 className={settingsStyles.sectionTitle}>
				{Icon && <Icon className={settingsStyles.sectionHeadingIcon} strokeWidth={2.5} />}
				{title}
			</h2>
			<p className={settingsStyles.sectionSubtitle}>{subtitle}</p>
		</div>
	);
}

export function RadioMark({ active }: { active: boolean }) {
	return active ? (
		<span className={settingsStyles.radioActiveCircle}>
			<Check className={settingsStyles.radioActiveIcon} strokeWidth={3.2} />
		</span>
	) : (
		<span className={settingsStyles.radioInactiveCircle} aria-hidden />
	);
}

export function ActionRow({
	Icon,
	title,
	helper,
	danger = false,
	onClick,
}: {
	Icon?: ComponentType<{ className?: string }>;
	title: string;
	helper: string;
	danger?: boolean;
	onClick: () => void;
}) {
	return (
		<button
			onClick={onClick}
			className={danger ? settingsStyles.listItemDanger : settingsStyles.listItem}
		>
			<div className="flex items-center gap-3 min-w-0 flex-1">
				{Icon && (
					<Icon
						className={danger ? settingsStyles.listItemIconDanger : settingsStyles.listItemIcon}
					/>
				)}
				<div className={settingsStyles.listItemContent}>
					<span className={danger ? settingsStyles.listItemTitleDanger : settingsStyles.listItemTitle}>
						{title}
					</span>
					<span className={settingsStyles.listItemSubtitle}>{helper}</span>
				</div>
			</div>
			<ChevronRight
				className={danger ? settingsStyles.listItemAccessoryDanger : settingsStyles.listItemAccessory}
			/>
		</button>
	);
}
