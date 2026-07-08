'use client';

import { useRouter } from 'next/navigation';
import { Loader2 } from '@/lib/assets';
import { useEffect, useRef, useState } from 'react';
import { AuthRequired } from '@/components/session';
import { MindMap } from '@/components/v2/kg/MindMap';
import { ExpandedGraphHeader, ExpandedGraphFooter } from '@/components/v2/kg/KnowledgeGraphUI';
import { knowledgeGraphStyles } from '@/lib/styles/knowledgeGraphStyles';
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

  const viewportWidth = isPortrait ? size.height : size.width;
  const viewportHeight = isPortrait ? size.width : size.height;

  // "100%" = the whole map fits the screenn
  useEffect(() => {
    if (!viewportWidth || !viewportHeight) return;
    const fit = Math.min(1, (viewportWidth - 40) / CANVAS_W, (viewportHeight - 120) / CANVAS_H);
    const clamped = Math.max(ZOOM_MIN, fit);
    setFitZoom(clamped);
    setZoom(clamped);
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
    <main className={knowledgeGraphStyles.expandedMainContainer}>
      <ExpandedGraphHeader onBack={() => router.push('/knowledge-graph')} />

      <div
        ref={scrollRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        className={knowledgeGraphStyles.expandedCanvasContainer}
      >
        {topicsQuery.isLoading ? (
          <div className={knowledgeGraphStyles.expandedLoadingContainer}>
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : (
          <div className={knowledgeGraphStyles.expandedMapWrapper}>
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

      <ExpandedGraphFooter zoom={zoom} fitZoom={fitZoom} onZoom={adjustZoom} />
    </main>
  );

  if (isPortrait && size.width && size.height) {
    return (
      <div className={knowledgeGraphStyles.expandedPortraitWrapper}>
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

  return <div className={knowledgeGraphStyles.expandedPortraitWrapper}>{content}</div>;
}
