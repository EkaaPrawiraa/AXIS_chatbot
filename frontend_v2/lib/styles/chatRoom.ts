export const chatRoomStyles = {
  // Hotline Warning Card - Emergency & Caring Theme (Soft Red/Pink)
  hotlineCardBase: "w-full max-w-[92%] rounded-[20px] border border-[#F8D7DA] bg-[#FFF5F6] p-4 shadow-[0_4px_16px_rgba(220,20,60,0.04)]",
  hotlineRow: "flex items-start gap-4",
  hotlineIconWrapper: "relative grid h-[42px] w-[42px] shrink-0 place-items-center rounded-full bg-[#FFE5E8]",
  hotlineMainTitle: "text-[15px] font-bold leading-tight text-[var(--v2-ink)] tracking-tight",
  hotlineMainSubtitle: "mt-1 text-[13px] font-bold leading-snug text-[#DC143C]", // Crimson accent
  hotlineMainDesc: "mt-1.5 text-[13px] font-medium leading-[1.55] text-[var(--v2-muted)]",
  hotlineDivider: "mt-4 border-t border-[#F8D7DA] pt-4",
  hotlineSubTitleRow: "flex flex-wrap items-center justify-between gap-2",
  hotlineSubTitle: "text-[14px] font-bold leading-tight text-[var(--v2-ink)]",
  hotlineSubBadge: "inline-flex shrink-0 items-center gap-1.5 rounded-full bg-[#FFE5E8] px-2.5 py-1 text-[10.5px] font-bold text-[#DC143C]",
  hotlineSubDesc: "mt-1 text-[13px] font-medium leading-[1.5] text-[var(--v2-muted-secondary)]",
  hotlineButtonGroup: "mt-4 flex flex-col gap-2.5 sm:flex-row",
  hotlineSecondaryBtn: "v2-anim-pressable inline-flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-xl border border-[#F8D7DA] bg-white px-4 text-[13.5px] font-bold text-[var(--v2-ink)] shadow-sm",
  hotlinePrimaryBtn: "v2-anim-pressable inline-flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-xl bg-[#DC143C] px-4 text-[13.5px] font-bold text-white shadow-[0_8px_16px_rgba(220,20,60,0.18)] hover:opacity-90 active:scale-95 transition-all",

  // PHQ-9 Card
  phqCardBase: "w-full overflow-hidden rounded-[20px] border border-[var(--v2-line)] bg-white shadow-[0_4px_16px_rgba(var(--v2-rgb-53432e),0.03)]",
  phqHeader: "bg-[var(--v2-olive-soft)] px-4 py-3.5",
  phqHeaderTitle: "text-[15px] font-bold leading-tight text-[var(--v2-ink)] tracking-tight",
  phqHeaderSubtitle: "mt-1 text-[13px] font-medium leading-snug text-[var(--v2-olive-deep)]",
  phqBody: "px-4 pb-4 pt-4",
  phqStepText: "text-[13px] font-bold text-[var(--v2-olive)]",
  phqProgressContainer: "mt-1.5 h-[6px] overflow-hidden rounded-full bg-[var(--v2-line)]",
  phqProgressBar: "h-full rounded-full bg-[var(--v2-olive)] transition-[width]",
  phqQuestion: "mt-4 text-[15px] font-bold leading-[1.45] text-[var(--v2-ink)] tracking-tight",
  phqOptionsContainer: "mt-4 space-y-2",
  phqOptionBtn: "v2-anim-pressable flex min-h-[40px] w-full items-center gap-2.5 rounded-xl border border-[var(--v2-line-border)] bg-white px-3 text-left shadow-sm disabled:opacity-45",
  phqOptionText: "text-[13.5px] font-bold text-[var(--v2-ink)]",
  phqInfoBtn: "v2-anim-pressable mt-3.5 flex items-center gap-1.5 text-[13px] font-bold text-[var(--v2-muted-secondary)] disabled:opacity-45",

  // --- New Centralized Styles ---

  // Page structure
  pageContainer: "fixed inset-0 z-10 flex h-[100dvh] flex-col",
  chatRail: "min-h-0 flex-1 space-y-3 overflow-y-auto px-1 pb-4",
  
  // Date Divider
  dateDividerContainer: "my-6 flex items-center justify-center gap-4",
  dateDividerLine: "h-[1px] flex-1 bg-gradient-to-r from-transparent to-[var(--v2-line-border)]",
  dateDividerLineReverse: "h-[1px] flex-1 bg-gradient-to-l from-transparent to-[var(--v2-line-border)]",
  dateDividerText: "text-[11px] font-bold tracking-widest text-[var(--v2-muted)] uppercase",

  // Assistant Bubble
  assistantBubbleWrapper: "w-fit max-w-[84%] space-y-1.5",
  assistantBubbleBody: "rounded-[12px] bg-[var(--v2-c-efeae0)] px-3.5 py-2.5 text-[14px] font-medium leading-[1.5] text-[var(--v2-ink)] [&_p]:whitespace-pre-wrap",
  assistantPhqChipsWrapper: "mt-3 space-y-2 rounded-[12px] bg-[var(--v2-olive-soft)] p-2.5",
  assistantPhqChipsGrid: "grid gap-1.5",
  assistantPhqChipBtn: "v2-anim-pressable rounded-[10px] border border-[var(--v2-line)] bg-white/80 px-3 py-2 text-left text-[13px] font-semibold disabled:opacity-45",
  assistantActionRow: "flex items-center gap-2.5 pl-1",
  assistantTimestampAction: "shrink-0 text-[11px] font-medium text-[var(--v2-c-8d8880)]",
  assistantTimestamp: "pl-1 text-[11px] font-medium text-[var(--v2-c-8d8880)]",
  
  // User Bubble
  userBubbleWrapper: "ml-auto w-fit max-w-[80%] rounded-[12px] bg-[var(--v2-c-7b8467)] px-3.5 py-2 text-[14px] font-medium leading-[1.5] text-white",
  userBubbleText: "whitespace-pre-wrap",
  userTimestamp: "mt-0.5 flex items-center justify-end gap-1 text-[10.5px] font-medium text-white/85",

  // Message Actions
  actionContainer: "mt-1.5 flex flex-wrap items-center gap-1.5",
  actionBtn: "v2-anim-pressable flex h-7 items-center gap-1.5 rounded-full bg-white px-3 shadow-sm border border-[var(--v2-line-border)] text-[11px] font-bold text-[var(--v2-muted-secondary)]",

  // Typing Dots
  typingContainer: "flex items-center gap-1 py-0.5",
  typingDot: "h-[6px] w-[6px] rounded-full bg-[var(--v2-muted)]",

  // Chat Composer
  composerWrapper: "sticky bottom-0 z-20 mt-auto bg-gradient-to-t from-[var(--v2-bg)] via-[var(--v2-bg)] to-transparent pb-5 pt-8",
  composerInputContainer: "relative mx-[22px] flex items-end gap-2 rounded-[24px] border border-[var(--v2-line-border)] bg-white p-1.5 pl-4 shadow-sm focus-within:border-[var(--v2-olive)] focus-within:ring-2 focus-within:ring-[var(--v2-olive-soft)] transition-all",
  composerTextarea: "max-h-[140px] min-h-[38px] w-full resize-none bg-transparent py-2.5 text-[15px] font-medium text-[var(--v2-ink)] placeholder-[var(--v2-muted)] outline-none scrollbar-hide",
  composerSendBtn: "grid h-[38px] w-[38px] shrink-0 place-items-center rounded-full bg-[var(--v2-olive)] text-white shadow-sm disabled:opacity-40",

  // Chat Header
  headerWrapper: "sticky top-0 z-20 -mx-[22px] flex items-center gap-2 bg-[rgba(var(--v2-rgb-faf4eb),0.92)] px-[22px] pb-2.5 pt-1.5 backdrop-blur-lg",
  headerBackBtn: "v2-anim-pressable grid h-9 w-8 place-items-center text-[var(--v2-ink)]",
  headerActionsWrapper: "relative ml-auto flex items-center gap-1",
  headerIconBtn: "v2-anim-pressable grid h-[38px] w-[38px] place-items-center rounded-full bg-white text-[var(--v2-ink)] shadow-[0_2px_8px_rgba(0,0,0,0.03)]",
  headerDropdown: "absolute right-0 top-full mt-2 w-48 overflow-hidden rounded-[16px] border border-[var(--v2-line-border)] bg-[rgba(255,255,255,0.95)] p-1 shadow-lg backdrop-blur-lg origin-top-right",
  headerDropdownItem: "flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-[14px] font-bold text-[var(--v2-ink)] hover:bg-[var(--v2-bg-light-1)] transition-colors",
  headerDropdownItemDanger: "flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-[14px] font-bold text-[#d84f45] hover:bg-[#fff5f5] transition-colors",
};
