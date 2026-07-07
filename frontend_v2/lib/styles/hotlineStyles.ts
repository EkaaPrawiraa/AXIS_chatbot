export const hotlineStyles = {
  // Page Layout
  pageWrapper: "space-y-4 pb-8",
  headerContainer: "mb-4",
  pageHeaderWrapper: "space-y-0.5",
  pageTitle: "v2-mobile-title",
  pageSubtitle: "mt-1 text-[13px] font-medium leading-[1.4] text-[var(--v2-text-subdued)]",

  // Filter Chips
  filterScrollWrapper: "-mx-1 flex gap-2.5 overflow-x-auto px-1 pb-2 hide-scrollbar",
  filterChipBase: "h-[32px] shrink-0 whitespace-nowrap rounded-full px-4 text-[12.5px] font-extrabold transition-colors v2-anim-pressable",
  filterChipActive: "bg-[var(--v2-olive-soft)] text-[var(--v2-olive-deep)]",
  filterChipInactive: "bg-transparent text-[var(--v2-muted)] hover:text-[var(--v2-ink)]",

  // Support Note (Footer note)
  supportNoteWrapper: "flex items-center gap-3 rounded-2xl bg-[var(--v2-olive-soft)]/40 px-4 py-3",
  supportNoteText: "text-[12.5px] font-medium leading-[1.45] text-[var(--v2-olive-deep)]",


  // Hotline Card
  cardWrapper: "flex flex-col gap-1.5 border-b border-[var(--v2-line-lighter)] py-4 last:border-0",
  cardTitleRow: "flex items-start justify-between gap-3",
  cardTitle: "text-[15px] font-semibold leading-tight text-[var(--v2-ink)]",
  cardDesc: "text-[13px] text-[var(--v2-muted-secondary)]",
  cardActionLink: "v2-anim-pressable shrink-0 text-[var(--v2-olive-deep)]",
  cardBadgeWrapper: "mt-1 flex flex-wrap items-center gap-1.5",
  cardBadge: "inline-flex rounded-full bg-[var(--v2-olive-soft)]/40 px-2 py-0.5 text-[10px] font-bold text-[var(--v2-olive-deep)]",
  cardContactList: "mt-3.5 flex flex-wrap gap-x-4 gap-y-2",
  cardContactItem: "v2-anim-pressable flex items-center gap-1.5 text-[13px] font-bold text-[var(--v2-olive-link)] underline decoration-[var(--v2-olive-soft)] decoration-2 underline-offset-4 transition-colors hover:text-[var(--v2-olive-deep)]",
  cardContactIcon: "h-[12px] w-[12px] shrink-0 text-[var(--v2-olive-deep)]",
};
