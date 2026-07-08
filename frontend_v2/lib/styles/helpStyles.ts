export const helpStyles = {
  // Layout
  pageContainer: "space-y-4 pb-[calc(116px+env(safe-area-inset-bottom))]",
  headerSection: "mt-1",
  pageTitle: "v2-mobile-title",
  pageDescription: "v2-mobile-description mt-1 w-full text-[var(--v2-gray-dark-1)]",

  // Flat List Container
  listWrapper: "mt-6 flex flex-col",
  
  // List Item (Header/Row)
  itemContainer: "flex flex-col py-1 transition-colors",
  itemHeaderBtn: "v2-anim-pressable flex w-full items-center gap-3.5 py-3.5 text-left hover:bg-[var(--v2-bg-light-2)]/50 rounded-xl px-1",
  
  // Icon styling
  iconWrapper: "flex h-9 w-9 shrink-0 items-center justify-center",
  iconElement: "h-[22px] w-[22px]",
  
  // Text group
  textGroup: "min-w-0 flex-1",
  titleText: "text-[15.5px] font-bold leading-tight text-[var(--v2-ink)]",
  summaryText: "mt-1 text-[13px] font-medium leading-[1.4] text-[var(--v2-muted-secondary)]",
  helperLink: "font-bold text-[var(--v2-olive-link)] underline underline-offset-4",
  
  // Chevron
  chevron: "h-[20px] w-[20px] shrink-0 text-[var(--v2-muted-secondary)] transition-transform duration-200",
  
  // Detail content
  detailContainer: "overflow-hidden px-2 pb-5 pt-1", // Aligned with the header button
  detailBodyText: "whitespace-pre-line text-[13px] font-medium leading-[1.6] text-[var(--v2-gray-dark-2)]",
  
  // Action buttons
  actionsWrapper: "mt-4 flex flex-wrap items-center gap-3",
  primaryLinkBtn: "v2-anim-pressable inline-flex min-h-9 items-center rounded-full bg-[var(--v2-olive-soft)] px-4 text-[12.5px] font-bold text-[var(--v2-olive-deep)]",
  externalLinkBtn: "v2-anim-pressable inline-flex min-h-9 items-center gap-1.5 rounded-full px-1 text-[13px] font-bold text-[var(--v2-olive-link)] underline underline-offset-4",
  externalLinkIcon: "h-4 w-4",
  
  // CBT Examples List
  examplesListWrapper: "mt-4 space-y-3",
  examplesListTitle: "text-[13.5px] font-bold leading-tight text-[var(--v2-ink)]",
  examplesListGroup: "space-y-3",
  exampleItem: "flex gap-3 text-[13px] font-medium leading-[1.55] text-[var(--v2-gray-dark-2)]",
  exampleBullet: "mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--v2-c-d59f2e)]",
  exampleLabel: "font-bold text-[var(--v2-ink)]",
  // Layout
  divider: "border-[var(--v2-line)] my-1",
};
