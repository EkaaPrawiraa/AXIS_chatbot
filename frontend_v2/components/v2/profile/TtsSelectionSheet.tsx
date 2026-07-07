import React from "react";
import { Check, X } from "lucide-react";
import { profileStyles } from "@/lib/styles/profileStyles";
import { TTS_MODELS } from "@/lib/profileData";

interface TtsSelectionSheetProps {
	ttsModel: string;
	onChooseTtsModel: (id: string) => void;
	onClose: () => void;
}

export function TtsSelectionSheet({
	ttsModel,
	onChooseTtsModel,
	onClose,
}: TtsSelectionSheetProps) {
	return (
		<div className={profileStyles.sheetBackdrop} onClick={onClose}>
			<div
				className={profileStyles.sheetContainer}
				onClick={(e) => e.stopPropagation()}
			>
				<div className={profileStyles.sheetHeader}>
					<h3 className={profileStyles.sheetTitle}>Suara Percakapan</h3>
					<button
						onClick={onClose}
						aria-label="Tutup"
						className={profileStyles.sheetCloseBtn}
					>
						<X className={profileStyles.sheetCloseIcon} />
					</button>
				</div>
				<div className={profileStyles.sheetOptionsList}>
					{TTS_MODELS.map((model) => {
						const active = ttsModel === model.id;
						return (
							<button
								key={model.id}
								onClick={() => onChooseTtsModel(model.id)}
								className={profileStyles.sheetOptionBtn}
							>
								<div className={profileStyles.sheetOptionTextGroupLeft}>
									<p className={profileStyles.sheetOptionTitle}>
										{model.name}
									</p>
									<p className={profileStyles.sheetOptionHelper}>
										{model.helper}
									</p>
								</div>
								{active ? (
									<Check className={profileStyles.sheetOptionCheck} />
								) : null}
							</button>
						);
					})}
				</div>
			</div>
		</div>
	);
}
