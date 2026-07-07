import { MessageCircle } from '@/lib/assets';
import { SectionHeading, RadioMark } from './SettingsComponents';
import { settingsStyles } from '@/lib/styles/settingsStyles';
import { usePreferencesStore } from '@/stores/preferences';

export function ResponseModeSection() {
	const chatResponseMode = usePreferencesStore((state) => state.chatResponseMode);
	const setChatResponseMode = usePreferencesStore((state) => state.setChatResponseMode);

	return (
		<div className={settingsStyles.sectionContainer}>
			<SectionHeading
				Icon={MessageCircle}
				title="Mode jawaban"
				subtitle="Pilih cara AXIS memberikan jawaban untuk kamu."
			/>
			<div className={settingsStyles.listWrapper}>
				{(
					[
						{
							id: "normal",
							label: "Jawaban muncul sekaligus",
							helper: "AXIS memberikan jawaban lengkap dalam satu balasan.",
						},
						{
							id: "stream",
							label: "Jawaban muncul bertahap",
							helper: "AXIS memberikan jawaban perlahan hingga selesai.",
						},
					] as const
				).map((option) => (
					<button
						key={option.id}
						onClick={() => setChatResponseMode(option.id)}
						className={settingsStyles.listItem}
					>
						<div className="flex items-center gap-3 min-w-0 flex-1">
							<div className={settingsStyles.listItemContent}>
								<span className={settingsStyles.listItemTitle}>
									{option.label}
								</span>
								<span className={settingsStyles.listItemSubtitle}>
									{option.helper}
								</span>
							</div>
						</div>
						<RadioMark active={chatResponseMode === option.id} />
					</button>
				))}
			</div>
		</div>
	);
}
