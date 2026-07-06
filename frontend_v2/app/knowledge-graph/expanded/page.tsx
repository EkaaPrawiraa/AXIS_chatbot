'use client';

import { useRouter } from 'next/navigation';
import { ArrowLeft, Hand, Loader2, Minus, Plus, ZoomIn } from '@/lib/assets';
import { useEffect, useRef, useState } from 'react';
import { AuthRequired } from '@/components/session';
import { MindMap } from '@/components/v2/kg/MindMap';
import { memoryAPI } from '@/lib/api/memory';
import { useQuery } from '@tanstack/react-query';
import { useSessionStore } from '@/stores';

const ZOOM_MIN = 0.35;
const ZOOM_MAX = 1.6;
const CANVAS_W = 1180;
const CANVAS_H = 560;

export default function ExpandedMapPage() {
  return (
    <AuthRequired>
      <ExpandedMapContent />
    </AuthRequired>
  );
}

/**
 * iOS Safari never implemented the Screen Orientation Lock API, so a web
 * page cannot force a real device rotation there. Instead we simulate
 * landscape by rotating our own fixed-position wrapper 90deg and swapping
 * its box to the device's actual height×width — the classic "CSS
 * orientation lock" trick — so the map reads as landscape immediately,
 * with no physical rotation required on any platform.
 */
function useSimulatedLandscape() {
  const [isPortrait, setIsPortrait] = useState(false);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const mql = window.matchMedia('(orientation: portrait)');
    const update = () => {
      setIsPortrait(mql.matches);
      setSize({ width: window.innerWidth, height: window.innerHeight });
    };
    update();
    mql.addEventListener('change', update);
    window.addEventListener('resize', update);
    return () => {
      mql.removeEventListener('change', update);
      window.removeEventListener('resize', update);
    };
  }, []);

  return { isPortrait, size };
}

function ExpandedMapContent() {
  const router = useRouter();
  const userId = useSessionStore((state) => state.userId);
  const user = useSessionStore((state) => state.user);
  const [zoom, setZoom] = useState(1);
  const [fitZoom, setFitZoom] = useState(1);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const { isPortrait, size } = useSimulatedLandscape();

  // The "viewport" the map lays out against is swapped (height×width) when
  // we're simulating landscape from a portrait device.
  const viewportWidth = isPortrait ? size.height : size.width;
  const viewportHeight = isPortrait ? size.width : size.height;

  // "100%" = the whole map fits the screen, like the mock.
  useEffect(() => {
    if (!viewportWidth || !viewportHeight) return;
    const fit = Math.min(1, (viewportWidth - 40) / CANVAS_W, (viewportHeight - 120) / CANVAS_H);
    const clamped = Math.max(ZOOM_MIN, fit);
    setFitZoom(clamped);
    setZoom(clamped);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewportWidth, viewportHeight]);

  const topicsQuery = useQuery({
    queryKey: ['mindmap-topics', userId],
    queryFn: () => memoryAPI.getMemoryNodes(userId!, 'topic'),
    enabled: !!userId,
    staleTime: 60_000,
  });

  const adjustZoom = (direction: number) =>
    setZoom((value) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, value + direction * 0.1 * fitZoom)));

  const onPointerDown = (event: React.PointerEvent) => {
    const scroller = scrollRef.current;
    if (!scroller) return;
    dragRef.current = { x: event.clientX, y: event.clientY, left: scroller.scrollLeft, top: scroller.scrollTop };
  };
  const onPointerMove = (event: React.PointerEvent) => {
    const scroller = scrollRef.current;
    const drag = dragRef.current;
    if (!scroller || !drag) return;
    scroller.scrollLeft = drag.left - (event.clientX - drag.x);
    scroller.scrollTop = drag.top - (event.clientY - drag.y);
  };
  const onPointerUp = () => {
    dragRef.current = null;
  };

  const content = (
    <main className="flex h-full w-full flex-col bg-[#f8f1e7]">
      <header className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-start justify-between gap-3 p-4">
        <div className="flex items-start gap-4">
          <button
            onClick={() => router.push('/knowledge-graph')}
            className="v2-anim-pressable pointer-events-auto flex h-[46px] items-center gap-2 rounded-full bg-[#fbf7ee] px-5 text-[15px] font-bold text-[var(--v2-ink)] shadow-[0_10px_22px_-14px_rgba(70,64,53,0.5)]"
          >
            <ArrowLeft className="h-[17px] w-[17px]" /> Kembali
          </button>
          <div>
            <h1 className="text-[24px] font-bold leading-tight text-[var(--v2-ink)]">Peta Memori 🌿</h1>
            <p className="text-[13px] font-medium text-[#6f6a5e]">Gambaran hal-hal penting dalam hidupmu.</p>
          </div>
        </div>
      </header>

      <div
        ref={scrollRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        className="flex-1 cursor-grab overflow-auto active:cursor-grabbing [scrollbar-width:none]"
      >
        {topicsQuery.isLoading ? (
          <div className="grid h-full place-items-center text-[var(--v2-muted)]">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : (
          <div className="grid min-h-full min-w-fit place-items-center px-4 py-10">
            <div style={{ width: CANVAS_W * zoom, height: CANVAS_H * zoom }}>
              <div style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}>
                <MindMap
                  topics={topicsQuery.data?.nodes || []}
                  userName={user?.displayName || 'Kamu'}
                  onSelectTopic={() => router.push('/memories?type=topic')}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <footer className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-end justify-between gap-3 p-4">
        <div className="pointer-events-auto flex h-[46px] items-center gap-1 rounded-full bg-[#fbf7ee] px-2 shadow-[0_10px_22px_-14px_rgba(70,64,53,0.5)]">
          <button onClick={() => adjustZoom(-1)} aria-label="Perkecil" className="v2-anim-pressable grid h-9 w-9 place-items-center text-[var(--v2-ink)]">
            <Minus className="h-[16px] w-[16px]" />
          </button>
          <span className="w-[52px] text-center text-[14px] font-bold text-[var(--v2-ink)]">
            {Math.round((zoom / fitZoom) * 100)}%
          </span>
          <button onClick={() => adjustZoom(1)} aria-label="Perbesar" className="v2-anim-pressable grid h-9 w-9 place-items-center text-[var(--v2-ink)]">
            <Plus className="h-[16px] w-[16px]" />
          </button>
        </div>

        <div className="hidden h-[42px] items-center gap-3 rounded-full bg-[#fbf7ee]/95 px-4 text-[12.5px] font-semibold text-[var(--v2-ink)] shadow-[0_10px_22px_-14px_rgba(70,64,53,0.5)] min-[560px]:flex">
          <span className="flex items-center gap-1.5">
            <Hand className="h-[14px] w-[14px]" /> Geser untuk berpindah
          </span>
          <span className="text-[#c9c2b2]">•</span>
          <span className="flex items-center gap-1.5">
            <ZoomIn className="h-[14px] w-[14px]" /> Cubit untuk zoom
          </span>
        </div>

        <div className="hidden rounded-[16px] bg-[#fbf7ee] p-2.5 shadow-[0_10px_22px_-14px_rgba(70,64,53,0.5)] min-[500px]:block">
          <svg width="84" height="52" viewBox="0 0 84 52" aria-hidden>
            <rect x="26" y="6" width="34" height="22" rx="5" fill="none" stroke="#a9a291" strokeWidth="1.6" />
            <circle cx="42" cy="30" r="5" fill="#8b9370" />
            <circle cx="32" cy="12" r="3" fill="#9aa77e" />
            <circle cx="54" cy="12" r="3" fill="#9aa77e" />
            <circle cx="24" cy="44" r="3.4" fill="#c26b4b" />
            <circle cx="60" cy="44" r="3.4" fill="#d9a13d" />
            <line x1="42" y1="30" x2="24" y2="44" stroke="#cbbc9e" strokeWidth="1.3" />
            <line x1="42" y1="30" x2="60" y2="44" stroke="#cbbc9e" strokeWidth="1.3" />
            <line x1="42" y1="30" x2="32" y2="12" stroke="#cbbc9e" strokeWidth="1.3" />
            <line x1="42" y1="30" x2="54" y2="12" stroke="#cbbc9e" strokeWidth="1.3" />
          </svg>
        </div>
      </footer>
    </main>
  );

  if (isPortrait && size.width && size.height) {
    // Rotate a box sized to the device's actual height×width 90deg so it
    // exactly fills the portrait screen while presenting as landscape.
    return (
      <div className="fixed inset-0 z-[60] overflow-hidden bg-[#f8f1e7]">
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: size.height,
            height: size.width,
            transformOrigin: 'top left',
            transform: 'rotate(90deg) translateY(-100%)',
          }}
        >
          {content}
        </div>
      </div>
    );
  }

  return <div className="fixed inset-0 z-[60] overflow-hidden bg-[#f8f1e7]">{content}</div>;
}
