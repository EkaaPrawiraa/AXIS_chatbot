import React, { useState } from "react";
import Avatar from "boring-avatars";
import { Check, Pencil } from "lucide-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRightFromBracket } from "@/lib/assets";
import { profileStyles } from "@/lib/styles/profileStyles";

interface ProfileAvatarProps {
	user: any;
	profile: any;
	initialName: string;
	onSave: (newName: string) => void;
	savedField: string | null;
	logout: () => void;
}

export function ProfileAvatar({
	user,
	profile,
	initialName,
	onSave,
	savedField,
	logout,
}: ProfileAvatarProps) {
	const [isEditingName, setIsEditingName] = useState(false);
	const [name, setName] = useState(initialName);

	const commitName = () => {
		setIsEditingName(false);
		if (name !== initialName) {
			onSave(name);
		}
	};

	// Reset local state if external initialName changes (e.g. from server)
	React.useEffect(() => {
		setName(initialName);
	}, [initialName]);

	return (
		<section className={profileStyles.avatarSection}>
			<div className={profileStyles.avatarInnerWrapper}>
				<div className={profileStyles.avatarWrapper}>
					<Avatar
						size={72}
						name={user?.id ?? profile?.userId ?? "AXIS User"}
						variant="beam"
						colors={["#F2EFE8", "#D8DDC2", "#84A971", "#E7DFCC", "#F2D8C8"]}
					/>
				</div>
				<div className={profileStyles.rowTextGroup}>
					<p className={profileStyles.displayNameLabel}>Nama tampilan</p>
					{isEditingName ? (
						<input
							autoFocus
							value={name}
							onChange={(event) => setName(event.target.value)}
							onBlur={commitName}
							onKeyDown={(event) => event.key === "Enter" && commitName()}
							className={profileStyles.displayNameInput}
						/>
					) : (
						<button
							onClick={() => setIsEditingName(true)}
							className={profileStyles.displayNameEditBtn}
						>
							<span className={profileStyles.displayNameText}>
								{name || "Tanpa nama"}
							</span>
							<Pencil className={profileStyles.displayNamePencilIcon} />
							{savedField === "name" ? (
								<Check className={profileStyles.displayNameCheckIcon} />
							) : null}
						</button>
					)}
					<p className={profileStyles.displayNameHelper}>
						Ini adalah nama yang akan ditampilkan di AXIS.
					</p>
				</div>
			</div>

			<button
				onClick={logout}
				aria-label="Keluar dari akun"
				className={profileStyles.logoutIconButton}
			>
				<FontAwesomeIcon
					icon={faRightFromBracket}
					className={profileStyles.logoutIconMini}
				/>
			</button>
		</section>
	);
}
