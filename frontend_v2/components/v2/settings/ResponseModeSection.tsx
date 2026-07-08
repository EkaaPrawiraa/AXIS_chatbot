import React from 'react';
import { Check, MessageCircle } from 'lucide-react';
import { usePreferencesStore } from '@/stores/preferences';
import { profileStyles } from '@/lib/styles/profileStyles';

export function ResponseModeSection() {
	const chatResponseMode = usePreferencesStore((state) => state.chatResponseMode);
	const setChatResponseMode = usePreferencesStore((state) => state.setChatResponseMode);

	return (
		<section className={profileStyles.sectionHeaderGroup}>
			<p className={profileStyles.sectionTitle}>
				<MessageCircle className={profileStyles.rowInlineIcon} strokeWidth={2.5} />
				Mode jawaban
			</p>
			<p className={profileStyles.sectionSubtitle}>
				Pilih cara AXIS memberikan jawaban untuk kamu.
			</p>
			<div className={profileStyles.responseStyleList}>
				{(
					[
						{
							id: "normal",
							label: "Jawaban sekaligus",
							helper: "AXIS memberikan jawaban lengkap dalam satu balasan.",
						},
						{
							id: "stream",
							label: "Jawaban bertahap",
							helper: "AXIS memberikan jawaban perlahan hingga selesai.",
						},
					] as const
				).map((option, index) => {
					const active = chatResponseMode === option.id;
					return (
						<React.Fragment key={option.id}>
							{index > 0 && (
								<div className={profileStyles.responseStyleDivider} />
							)}
							<button
								onClick={() => setChatResponseMode(option.id)}
								className={`${profileStyles.responseStyleCard} ${
									active
										? profileStyles.responseStyleCardActive
										: profileStyles.responseStyleCardInactive
								}`}
							>
								{active ? (
									<span className={profileStyles.responseStyleActiveBadge}>
										<Check className={profileStyles.responseStyleActiveIcon} strokeWidth={3} />
									</span>
								) : null}
								<p className={profileStyles.responseStyleTitle}>
									{option.label}
								</p>
								<p className={profileStyles.responseStyleHelper}>
									{option.helper}
								</p>
							</button>
						</React.Fragment>
					);
				})}
			</div>
		</section>
	);
}
