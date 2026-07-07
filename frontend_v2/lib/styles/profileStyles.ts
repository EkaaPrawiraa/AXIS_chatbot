/**
 * Centralized styles for the Profile page.
 * Replaces hardcoded boxy inline classes with organic flat-list layouts.
 */
export const profileStyles = {
  // Page Layout
  mainContainer: "space-y-3 pb-[124px] pt-0",
  headerContainer: "mb-2",
  pageTitle: "v2-mobile-title",
  pageSubtitle: "mt-1 text-[13px] font-medium leading-[1.4] text-[var(--v2-text-subdued)]",

  // Profile Avatar & Name Section
  avatarSection: "flex items-center gap-4 py-4 border-b border-[var(--v2-line-lighter)]",
  avatarInnerWrapper: "flex min-w-0 flex-1 items-center gap-4",
  avatarWrapper: "relative shrink-0",
  avatarImage: "h-[72px] w-[72px] rounded-full object-cover",
  displayNameLabel: "text-[12.5px] font-bold text-[var(--v2-green-tertiary)]",
  displayNameText: "truncate text-[20px] font-bold leading-tight text-[var(--v2-ink)]",
  displayNameInput: "mt-0.5 w-full rounded-[10px] border border-[var(--v2-c-ddd3bd)] bg-white/70 px-2 py-1 text-[20px] font-bold text-[var(--v2-ink)] outline-none",
  displayNameHelper: "truncate mt-1 text-[11.5px] font-medium leading-snug text-[var(--v2-muted-secondary)]",
  displayNameEditBtn: "v2-anim-pressable flex w-full items-center gap-2.5",
  displayNamePencilIcon: "h-[16px] w-[16px] shrink-0 text-[var(--v2-green-tertiary)]",
  displayNameCheckIcon: "h-[15px] w-[15px] shrink-0 text-[var(--v2-green-primary)]",
  logoutIconButton: "v2-anim-pressable grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[var(--v2-c-f7e5da)] text-[var(--v2-c-a34a28)]",
  logoutIconMini: "h-[18px] w-[18px] pr-0.5",

  // Section Typography (like "Preferensi lanjutan", "Gaya respons")
  sectionHeaderGroup: "pt-2 pb-1",
  sectionTitle: "flex items-center gap-2 text-[15px] font-bold text-[var(--v2-ink)]",
  sectionSubtitle: "mt-0.5 text-[13px] font-medium text-[var(--v2-muted-secondary)]",
  sectionDivider: "border-[var(--v2-line-lighter)] my-3",

  // Profile Row (Flat List Item)
  settingsListWrapper: "mt-4 flex flex-col",
  rowContainer: "flex w-full items-center gap-3.5 py-3 text-left",
  rowPressable: "v2-anim-pressable cursor-pointer",
  rowTextGroup: "min-w-0 flex-1",
  rowLabel: "flex items-center gap-2 text-[12.5px] font-bold text-[var(--v2-green-tertiary)]",
  rowInlineIcon: "h-[14px] w-[14px]",
  rowValue: "block truncate text-[15.5px] font-bold leading-snug text-[var(--v2-ink)]",
  rowHelper: "block text-[12px] font-medium leading-snug text-[var(--v2-muted-secondary)]",
  rowAccessoryWrapper: "shrink-0",

  // Response Style Cards (Organic instead of boxy/bordered)
  responseStyleList: "mt-3 flex items-stretch gap-4",
  responseStyleDivider: "my-2 w-[1px] shrink-0 bg-[var(--v2-line-lighter)]",
  responseStyleCard: "v2-anim-pressable relative flex flex-col flex-1 rounded-[16px] p-3 text-left transition-all duration-200",
  responseStyleCardActive: "bg-[#F3EFE4] border-[1.5px] border-[var(--v2-olive)] shadow-sm",
  responseStyleCardInactive: "bg-[var(--v2-bg-light-3)] border-[1.5px] border-transparent opacity-70",
  responseStyleActiveBadge: "absolute right-2.5 top-2.5 grid h-[22px] w-[22px] place-items-center rounded-full bg-[var(--v2-olive-deep)] text-white",
  responseStyleActiveIcon: "h-[13px] w-[13px]",
  responseStyleIcon: "h-[22px] w-[22px] text-[var(--v2-green-light)]",
  responseStyleTitle: "mt-2 text-[14px] font-bold text-[var(--v2-ink)]",
  responseStyleHelper: "mt-1 text-[11.5px] font-medium leading-[1.4] text-[var(--v2-muted-secondary)]",

  // Info Grid (Account Information)
  accountInfoContainer: "pt-2 space-y-3",
  accountInfoRow: "flex items-center justify-between gap-3",
  accountInfoLabel: "text-[13px] font-medium text-[var(--v2-muted-tertiary)]",
  accountInfoValue: "text-[13px] font-bold text-[var(--v2-ink)]",
  accountInfoValueFlex: "flex items-center gap-2 text-[13px] font-bold text-[var(--v2-ink)]",
  accountInfoIdText: "truncate font-mono uppercase",
  accountInfoCopyBtn: "v2-anim-pressable text-[var(--v2-ink)]",
  accountInfoCopyIconActive: "h-[14px] w-[14px] text-[var(--v2-green-primary)]",
  accountInfoCopyIcon: "h-[14px] w-[14px]",
  accountInfoVerifiedBadge: "grid h-[16px] w-[16px] place-items-center rounded-full bg-[var(--v2-c-5c8a4e)] text-white",
  accountInfoVerifiedIcon: "h-[10px] w-[10px]",

  // Logout Button (Subtle, elegant)
  logoutButton: "v2-anim-pressable mt-8 flex w-full items-center gap-3.5 py-4 text-left border-t border-[var(--v2-line-lighter)]",
  logoutIconWrapper: "grid h-[42px] w-[42px] shrink-0 place-items-center rounded-full bg-[var(--v2-c-f7e5da)] text-[var(--v2-c-a34a28)]",
  logoutTitle: "block text-[15.5px] font-bold text-[var(--v2-c-a34a28)]",
  logoutSubtitle: "block text-[12px] font-medium text-[var(--v2-muted-secondary)]",

  // Saved Banner
  savedBannerPopup: "fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-full bg-[var(--v2-green-primary)] px-6 py-2.5 text-sm font-semibold text-white shadow-lg transition-all duration-300",
  savedBanner: "mb-4 flex items-center justify-between rounded-2xl bg-[var(--v2-olive-soft)]/40 px-4 py-3",
  savedBannerText: "flex items-center gap-2.5 text-[14px] font-bold text-[var(--v2-olive-deep)]",
  
  // Bottom Sheet elements (Reused structure)
  sheetBackdrop: "fixed inset-0 z-[80] bg-black/35",
  sheetContainer: "absolute inset-x-0 bottom-0 mx-auto w-[min(100%,540px)] rounded-t-[26px] bg-[var(--v2-bg-light-9)] p-5 shadow-2xl",
  sheetHeader: "mb-4 flex items-center justify-between",
  sheetTitle: "text-[19px] font-bold text-[var(--v2-ink)]",
  sheetSubtitle: "mt-1 text-[12.5px] font-medium text-[var(--v2-muted-secondary)]",
  sheetCloseBtn: "v2-anim-pressable text-[var(--v2-ink)]",
  sheetCloseIcon: "h-[18px] w-[18px]",
  sheetGenderToggleGroup: "mt-1.5 grid grid-cols-2 gap-2 rounded-[14px] bg-[var(--v2-bg-light-3)] p-1",
  sheetGenderToggleBtn: "v2-anim-pressable rounded-[11px] py-2 text-[13.5px] font-bold capitalize text-center",
  sheetGenderToggleBtnActive: "bg-white text-[var(--v2-ink)] shadow-sm",
  sheetGenderToggleBtnInactive: "text-[var(--v2-muted-secondary)]",
  
  // Sheet Options (Flat list style)
  sheetOptionsList: "mt-4 flex flex-col",
  sheetOptionBtn: "flex w-full items-center justify-between border-b border-[var(--v2-line-lighter)] py-3.5 text-left last:border-0",
  sheetOptionTextGroup: "flex flex-1 flex-col",
  sheetOptionTextGroupLeft: "flex flex-1 flex-col text-left",
  sheetOptionTitle: "block text-[14.5px] font-bold text-[var(--v2-ink)]",
  sheetOptionHelper: "block text-[12px] font-medium text-[var(--v2-muted-secondary)]",
  sheetOptionAccessory: "flex items-center gap-3",
  sheetOptionCheck: "h-[18px] w-[18px] text-[var(--v2-green-primary)]",
  sheetOptionTestBtn: "v2-anim-pressable grid h-9 w-9 place-items-center rounded-full bg-[var(--v2-olive-soft)] text-[var(--v2-olive-deep)]",
};
