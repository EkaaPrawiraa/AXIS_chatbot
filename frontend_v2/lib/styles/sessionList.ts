export const sessionListStyles = {
  // Page & Header
  pageContainer: "min-h-[100dvh] pb-[86px] pt-0",
  headerGroup: "mt-5 flex items-center justify-between gap-4",
  pageTitle: "text-[22px] font-bold tracking-tight text-[var(--v2-ink)]",
  pageSubtext: "text-[14px] leading-relaxed text-[var(--v2-muted-secondary)]",
  newChatButton: "flex h-11 w-11 shrink-0 items-center justify-center rounded-[12px] bg-[var(--v2-olive)] text-white shadow-sm transition-transform hover:opacity-90 active:scale-95",
  newChatIcon: "h-5 w-5",

  // Search Bar (Redesigned to be boxless/flat)
  searchBarContainer: "mt-5 flex h-[48px] items-center gap-3 rounded-2xl bg-[var(--v2-olive-soft)]/50 px-4 transition-colors focus-within:bg-[var(--v2-olive-soft)]",
  searchIcon: "h-[19px] w-[19px] shrink-0 text-[var(--v2-olive-deep)]/60",
  searchInput: "min-w-0 flex-1 bg-transparent text-[14px] font-medium text-[var(--v2-ink)] outline-none placeholder:text-[var(--v2-olive-deep)]/50",

  // Session Group
  groupContainer: "mt-6 space-y-6",
  groupHeader: "mb-0.5 flex items-center justify-between gap-3 px-1",
  groupTitleContainer: "flex items-center gap-2",
  groupTitle: "text-[13px] font-bold uppercase tracking-wider text-[var(--v2-muted)]",
  groupCountBadge: "rounded-full bg-[var(--v2-olive-soft)] px-2.5 py-0.5 text-[11.5px] font-bold text-[var(--v2-olive-deep)]",
  groupActionButton: "v2-anim-pressable grid h-8 w-8 place-items-center rounded-full text-[var(--v2-olive-deep)] hover:bg-[var(--v2-bg-light-2)]",

  // Unified List Item (Boxless, Elegant)
  itemBase: "v2-anim-pressable flex w-full items-start gap-3 border-b border-[var(--v2-line-border)]/60 py-3.5 text-left last:border-b-0 hover:bg-[var(--v2-bg-light-2)]/50 transition-colors",
  itemContent: "min-w-0 flex-1 px-1",
  itemHeader: "flex items-start justify-between gap-3",
  itemTitle: "line-clamp-1 text-[15px] font-semibold leading-tight text-[var(--v2-ink)]",
  itemTime: "shrink-0 text-[12px] font-semibold text-[var(--v2-muted)] mt-0.5",
  itemBody: "mt-1.5 flex items-start justify-between gap-3",
  itemPreview: "line-clamp-2 text-[13px] text-[var(--v2-muted-secondary)] mt-0.5",
  badgeBase: "shrink-0 rounded-full bg-[var(--v2-olive-soft)] font-bold text-[var(--v2-olive-deep)] px-2.5 py-0.5 text-[10.5px]",

  // Empty State
  emptyStateContainer: "mt-8 px-6 py-10 text-center",
  emptyStateTitle: "text-[18.5px] font-bold text-[var(--v2-ink)]",
  emptyStateDescription: "mx-auto mt-3 max-w-[260px] text-[13.5px] font-medium leading-relaxed text-[var(--v2-muted)]",
  emptyStateButton: "v2-button v2-button-secondary mt-7 min-h-[46px] px-6 text-[14px] shadow-sm",
};
