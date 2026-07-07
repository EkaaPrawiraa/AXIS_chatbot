import React from "react";
import { Check, Sparkles } from "lucide-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSliders } from "@/lib/assets";
import { profileStyles } from "@/lib/styles/profileStyles";
import { STYLES } from "@/lib/profileData";

interface ResponseStyleSelectorProps {
	responseModel: string;
	chooseStyle: (id: string) => void;
}

export function ResponseStyleSelector({
	responseModel,
	chooseStyle,
}: ResponseStyleSelectorProps) {
	return (
		<section className={profileStyles.sectionHeaderGroup}>
			<p className={profileStyles.sectionTitle}>
				<FontAwesomeIcon
					icon={faSliders}
					className={profileStyles.rowInlineIcon}
				/>
				Gaya respons
			</p>
			<p className={profileStyles.sectionSubtitle}>
				Pilih gaya respons yang paling cocok untukmu.
			</p>
			<div className={profileStyles.responseStyleList}>
				{STYLES.map((style, index) => {
					const active = responseModel === style.id;
					return (
						<React.Fragment key={style.id}>
							{index > 0 && (
								<div className={profileStyles.responseStyleDivider} />
							)}
							<button
								onClick={() => chooseStyle(style.id)}
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
									{style.label}
								</p>
								<p className={profileStyles.responseStyleHelper}>
									{style.helper}
								</p>
							</button>
						</React.Fragment>
					);
				})}
			</div>
		</section>
	);
}
