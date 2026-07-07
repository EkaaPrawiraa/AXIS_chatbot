/**
 * Centralized styles for the Dashboard page.
 * Use these constants to ensure consistent typography and spacing
 * across all components in the dashboard view.
 */
export const dashboardStyles = {

  
  // Page Layout
  mainContainer: "space-y-3 pb-[124px] pt-0",
  heroContainer: "flex items-center justify-between gap-4 pr-1",
  quickActionList: "flex flex-col gap-1.5",
  devInfoSection: "mt-4 pt-6 border-t border-[var(--v2-line)] flex flex-col gap-4 pb-8",
  infoGrid: "grid gap-4 leading-snug",
  infoRow: "flex flex-col",

  // Hero
  heroHeading: "text-[22px] font-bold tracking-tight text-[var(--v2-ink)]",
  heroSubtext: "text-[14px] leading-relaxed text-[var(--v2-muted-secondary)]",
  primaryButton: "flex h-11 w-11 shrink-0 items-center justify-center rounded-[12px] bg-[var(--v2-olive)] text-white shadow-sm transition-transform hover:opacity-90 active:scale-95",
  primaryIcon: "h-5 w-5",

  // Sections
  sectionHeading: "mb-3 text-[13px] font-bold uppercase tracking-wider text-[var(--v2-muted)]",
  sectionHeadingNoMargin: "text-[13px] font-bold uppercase tracking-wider text-[var(--v2-muted)]",
  sectionSubtext: "mt-0.5 text-[13px] text-[var(--v2-muted-secondary)]",

  // Typography Items
  itemTitle: "text-[15px] font-semibold leading-tight text-[var(--v2-ink)]",
  itemLabel: "text-[13px] text-[var(--v2-muted-secondary)]",
  itemDescription: "mt-0.5 text-[13px] text-[var(--v2-muted-secondary)]",

  // Buttons & Links
  evalButton: "mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--v2-olive)] px-4 py-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 active:scale-[0.98]",
  evalIcon: "h-4 w-4",

  // Quick Action Component
  quickActionCard: "v2-anim-pressable flex items-center justify-between rounded-[14px] p-3 -mx-3 transition-colors hover:bg-[var(--v2-bg-light-2)]/60",
  quickActionContent: "flex items-center gap-3.5",
  quickActionIconWrapper: "flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--v2-olive-soft)] text-[var(--v2-olive-deep)]",
  quickActionTextWrapper: "flex flex-col",
  quickActionChevron: "h-5 w-5 shrink-0 text-[var(--v2-muted-secondary)] opacity-50",

  // Dashboard Card (Unified)
  dashboardCardContainer: "flex flex-col gap-4",
  heroHeaderGroup: "flex flex-col gap-1",

  // Mood Check Component
  moodCheckContainer: "flex flex-col gap-3 py-2",
  moodCheckGrid: "flex items-center justify-between sm:justify-center sm:gap-6",
  moodCheckButtonBase: "v2-anim-pressable flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded-full transition-all duration-300",
  moodCheckButtonSelected: "bg-[var(--v2-olive-soft)] shadow-[0_4px_12px_rgba(123,79,53,0.15)] scale-110",
  moodCheckButtonUnselected: "bg-white border border-[var(--v2-line-border)] hover:bg-[var(--v2-bg-light-2)] shadow-sm",
  moodCheckIcon: "h-[22px] w-[22px] transition-colors duration-300",
  moodCheckScaleLabels: "flex justify-between px-2 pt-1.5 text-[11px] font-medium tracking-wide text-[var(--v2-muted-secondary)] opacity-80",

  // Insight Component
  insightCardContainer: "flex flex-col gap-1.5 pt-1",
  insightCardHeader: "flex items-center gap-1.5",
  insightCardIcon: "h-4 w-4 text-[var(--v2-olive-deep)] shrink-0",
  insightCardTitle: "text-[13px] font-bold uppercase tracking-wider text-[var(--v2-muted)] line-clamp-1",
  insightCardDescription: "line-clamp-2 leading-relaxed",
  // insightCardLink: "mt-1 inline-flex w-fit items-center gap-1.5 text-[13.5px] font-bold text-[var(--v2-olive-deep)] transition-opacity hover:opacity-75",
  insightCardLink:
  "mt-1 self-end pr-0.5 inline-flex w-fit items-center gap-1.5 text-[13.5px] font-bold text-[var(--v2-olive-deep)] transition-opacity hover:opacity-75",
  insightCardLinkIcon: "h-4 w-4",

  // Layout
  divider: "border-[var(--v2-line)] my-1",
};
