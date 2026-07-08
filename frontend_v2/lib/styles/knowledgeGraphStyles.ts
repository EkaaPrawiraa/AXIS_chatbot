export const knowledgeGraphStyles = {
  mainContainer: "space-y-3.5 pb-6",
  
  // Header
  headerContainer: "",
  title: "text-[25px] font-bold leading-tight text-[var(--v2-ink)]",
  description: "mt-1 max-w-[300px] text-[13px] font-medium leading-snug text-[var(--v2-muted)]",
  
  // Map Section
  mapSection: "px-1 pb-4 pt-1",
  loadingContainer: "grid h-[336px] place-items-center text-[var(--v2-muted)]",
  hubContainer: "mt-1.5",
  
  // Sensitive Toggle
  sensitiveToggleBtn: "v2-anim-pressable flex items-center gap-2 rounded-full border border-[var(--v2-c-e0d8c5)] bg-[var(--v2-c-fbf6ec)] px-3.5 py-1.5 text-[12px] font-semibold text-[var(--v2-ink)]",
  sensitiveToggleIcon: "h-[14px] w-[14px]",
  
  // Expand Button
  expandBtn: "v2-anim-pressable mx-auto mt-3 flex h-[44px] w-[min(100%,210px)] items-center justify-center gap-2.5 rounded-full bg-[var(--v2-clay)] text-[15.5px] font-bold text-white shadow-[0_14px_26px_-14px_rgba(var(--v2-rgb-c36c45),0.9)]",
  expandIcon: "h-[16px] w-[16px]",
  
  // Landscape Notice
  noticeContainer: "mt-3 flex items-center justify-center gap-2 text-[12px] font-medium text-[var(--v2-muted-tertiary)]",
  noticeIcon: "h-[15px] w-[15px] -rotate-90",

  // Expanded Map
  expandedMainContainer: "flex h-full w-full flex-col bg-[var(--v2-c-f8f1e7)]",
  expandedHeaderContainer: "pointer-events-none absolute inset-x-0 top-0 z-20 flex items-start justify-between gap-3 p-4",
  expandedHeaderContent: "flex items-start gap-4",
  expandedBackBtn: "v2-anim-pressable pointer-events-auto flex h-[46px] items-center gap-2 rounded-full bg-[var(--v2-bg-light-1)] px-5 text-[15px] font-bold text-[var(--v2-ink)] shadow-[0_10px_22px_-14px_rgba(var(--v2-rgb-464035),0.5)]",
  expandedBackIcon: "h-[17px] w-[17px]",
  expandedTitle: "text-[24px] font-bold leading-tight text-[var(--v2-ink)]",
  expandedDescription: "text-[13px] font-medium text-[var(--v2-muted-tertiary)]",
  
  expandedCanvasContainer: "flex-1 cursor-grab overflow-auto active:cursor-grabbing [scrollbar-width:none]",
  expandedLoadingContainer: "grid h-full place-items-center text-[var(--v2-muted)]",
  expandedMapWrapper: "grid min-h-full min-w-fit place-items-center px-4 py-10",
  
  expandedFooterContainer: "pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-end justify-between gap-3 p-4",
  expandedZoomControls: "pointer-events-auto flex h-[46px] items-center gap-1 rounded-full bg-[var(--v2-bg-light-1)] px-2 shadow-[0_10px_22px_-14px_rgba(var(--v2-rgb-464035),0.5)]",
  expandedZoomBtn: "v2-anim-pressable grid h-9 w-9 place-items-center text-[var(--v2-ink)]",
  expandedZoomIcon: "h-[16px] w-[16px]",
  expandedZoomText: "w-[52px] text-center text-[14px] font-bold text-[var(--v2-ink)]",
  
  expandedHelperContainer: "hidden h-[42px] items-center gap-3 rounded-full bg-[var(--v2-bg-light-1)]/95 px-4 text-[12.5px] font-semibold text-[var(--v2-ink)] shadow-[0_10px_22px_-14px_rgba(var(--v2-rgb-464035),0.5)] min-[560px]:flex",
  expandedHelperItem: "flex items-center gap-1.5",
  expandedHelperIcon: "h-[14px] w-[14px]",
  expandedHelperDot: "text-[var(--v2-c-c9c2b2)]",
  
  expandedMinimapContainer: "hidden rounded-[16px] bg-[var(--v2-bg-light-1)] p-2.5 shadow-[0_10px_22px_-14px_rgba(var(--v2-rgb-464035),0.5)] min-[500px]:block",
  
  expandedPortraitWrapper: "fixed inset-0 z-[60] overflow-hidden bg-[var(--v2-c-f8f1e7)]",
};
