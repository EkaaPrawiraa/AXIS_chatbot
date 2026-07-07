export const memoryStyles = {
  // Layout & Wrappers
  pageWrapper: "space-y-4 pb-8",
  headerContainer: "mb-3",
  pageHeaderWrapper: "flex items-start justify-between gap-4",
  pageTitle: "v2-mobile-title",
  pageDescription: "mt-1 text-[13px] font-medium leading-[1.4] text-[var(--v2-text-subdued)]",
  
  // Filter Chips (Pill Filter)
  filterScrollWrapper: "-mx-1 flex gap-2.5 overflow-x-auto px-1 pb-2 hide-scrollbar",
  filterChip: "h-[32px] shrink-0 whitespace-nowrap rounded-full px-4 text-[12.5px] font-extrabold transition-colors v2-anim-pressable",
  filterChipActive: "bg-[var(--v2-olive-soft)] text-[var(--v2-olive-deep)]",
  filterChipInactive: "bg-transparent text-[var(--v2-muted)] hover:text-[var(--v2-ink)]",

  // Search & Controls
  controlsContainer: "flex items-center gap-2.5",
  searchWrapper: "flex h-[44px] flex-1 items-center gap-3 rounded-2xl bg-[var(--v2-olive-soft)]/50 px-3.5 transition-colors focus-within:bg-[var(--v2-olive-soft)]",
  searchIcon: "h-[18px] w-[18px] shrink-0 text-[var(--v2-olive-deep)]/60",
  searchInput: "min-w-0 flex-1 bg-transparent text-[13.5px] font-medium text-[var(--v2-ink)] outline-none placeholder:text-[var(--v2-olive-deep)]/50",
  infoButton: "grid h-[44px] w-[44px] shrink-0 place-items-center rounded-2xl transition-all v2-anim-pressable",
  infoButtonActive: "bg-[var(--v2-olive)] text-white shadow-[0_4px_12px_rgba(var(--v2-rgb-c36c45),0.2)]",
  infoButtonInactive: "bg-[var(--v2-bg-light-1)] text-[var(--v2-muted)] hover:text-[var(--v2-ink)] hover:bg-[var(--v2-line-lighter)]",
  sensitiveToggleBtn: "flex h-[44px] shrink-0 items-center gap-1.5 rounded-2xl bg-[var(--v2-bg-light-1)] px-3.5 text-[12px] font-bold text-[var(--v2-muted-secondary)] transition-colors hover:text-[var(--v2-ink)] hover:bg-[var(--v2-line-lighter)] v2-anim-pressable",

  // Info Guide Banner
  guideBanner: "flex flex-col gap-1.5 overflow-hidden rounded-[20px] bg-[var(--v2-bg-light-1)] p-4",
  guideHeader: "flex items-center gap-2",
  guideIconWrapper: "grid h-[24px] w-[24px] shrink-0 place-items-center rounded-full bg-[var(--v2-olive-soft)] text-[var(--v2-olive-deep)]",
  guideTitle: "text-[13.5px] font-extrabold text-[var(--v2-olive-deep)]",
  guideDescription: "text-[12.5px] font-medium leading-[1.55] text-[var(--v2-text-subdued)]",
  
  // Sensitive Hidden Banner
  sensitiveHiddenBanner: "flex items-center gap-3.5 border-b border-[var(--v2-line-lighter)] pb-4 pt-2",
  sensitiveHiddenIconWrapper: "grid h-[40px] w-[40px] shrink-0 place-items-center rounded-full bg-[var(--v2-olive-soft)]/50",
  sensitiveHiddenIcon: "h-[18px] w-[18px] text-[var(--v2-olive-deep)]",
  sensitiveHiddenTextWrapper: "min-w-0 flex-1",
  sensitiveHiddenTitle: "text-[13.5px] font-bold text-[var(--v2-ink)]",
  sensitiveHiddenDescription: "text-[11.5px] font-medium leading-[1.4] text-[var(--v2-muted-tertiary)]",
  sensitiveHiddenRevealBtn: "v2-anim-pressable shrink-0 rounded-full px-3 py-1.5 text-[12px] font-bold text-[var(--v2-olive-link)] hover:bg-[var(--v2-olive-soft)] transition-colors",

  // Sensitive Revealed Banner
  sensitiveRevealedBanner: "flex flex-col gap-3 border-b border-[var(--v2-line-lighter)] pb-4 pt-2",
  sensitiveRevealedHeader: "flex items-center gap-2 text-[13px] font-bold text-[var(--v2-ink)]",
  sensitiveRevealedItem: "flex items-center gap-3 py-2",
  sensitiveRevealedIconWrapper: "grid h-[46px] w-[46px] shrink-0 place-items-center rounded-[14px] bg-[var(--v2-c-b9ac97)]/60 backdrop-blur",
  sensitiveRevealedLinesWrapper: "min-w-0 flex-1 space-y-2",
  sensitiveRevealedLine1: "block h-[8px] w-[75%] rounded-full bg-[var(--v2-line-lighter)]",
  sensitiveRevealedLine2: "block h-[8px] w-[45%] rounded-full bg-[var(--v2-line-light)]",
  sensitiveFooter: "mt-3 flex items-center justify-center gap-1.5 text-[11.5px] font-medium text-[var(--v2-muted-tertiary)]",

  // Empty State
  emptyStateWrapper: "flex flex-col items-center justify-center pt-10 pb-16 text-center",
  emptyStateIconWrapper: "grid h-[56px] w-[56px] shrink-0 place-items-center rounded-full bg-[var(--v2-bg-light-1)] text-[var(--v2-olive-deep)] mb-4",
  emptyStateTitle: "mt-4 text-[16px] font-extrabold text-[var(--v2-ink)]",
  emptyStateDescription: "mx-auto mt-1.5 max-w-[280px] text-[13px] font-medium leading-[1.5] text-[var(--v2-text-subdued)]",
  emptyStateButton: "v2-anim-pressable mx-auto mt-5 flex items-center justify-center gap-1.5 text-[14px] font-extrabold text-[var(--v2-olive-link)] hover:text-[var(--v2-olive-deep)] transition-colors",
  emptyStateIcon: "h-[16px] w-[16px]",

  // List Wrapper
  listWrapper: "flex flex-col mt-2",
  resetButton: "mx-auto flex items-center gap-1.5 pt-1 text-[12px] font-semibold text-[var(--v2-muted)]",
  contentSection: "mt-5 pb-6",
  loadingWrapper: "flex items-center justify-center py-10 text-[var(--v2-olive-soft)]",

  // Sensitive Revealed Override
  sensitiveRevealedList: "space-y-1",
  sensitiveRevealedBtn: "rounded-full bg-[var(--v2-olive-soft)] px-3 py-1.5 text-[11px] font-bold text-[var(--v2-olive-deep)] transition-colors hover:bg-[var(--v2-c-b9ac97)]",

  // Memory Card (List Item)
  cardWrapper: "group flex gap-4 border-b border-[var(--v2-line-lighter)] py-4 last:border-b-0",
  cardContentWrapper: "min-w-0 flex-1",
  cardHeader: "flex items-start justify-between gap-3",
  cardTitle: "truncate text-[15px] font-extrabold leading-tight text-[var(--v2-ink)]",
  cardTitleLocked: "flex items-center gap-1.5",
  cardTime: "mt-0.5 text-[12px] font-semibold text-[var(--v2-muted)]",
  cardPreview: "mt-1.5 line-clamp-3 text-[14px] font-medium leading-[1.5] text-[var(--v2-text-subdued)]",
  cardControls: "flex shrink-0 items-center gap-2",
  cardMenuBtn: "v2-anim-pressable -mr-1.5 p-1.5 text-[var(--v2-muted)] hover:text-[var(--v2-ink)]",
  cardBadgeWrapper: "flex justify-end",
  cardBadge: "rounded-full bg-[var(--v2-c-e9ead9)] px-2.5 py-[2px] text-[10.5px] font-semibold text-[var(--v2-green-accent)]",
};
