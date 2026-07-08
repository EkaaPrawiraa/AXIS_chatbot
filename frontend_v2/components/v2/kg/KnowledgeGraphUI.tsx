import React from 'react';
import { Eye, EyeOff, MoveDiagonal, Smartphone, ArrowLeft, Minus, Plus, Hand, ZoomIn } from '@/lib/assets';
import { knowledgeGraphStyles } from '@/lib/styles/knowledgeGraphStyles';

export function KnowledgeGraphHeader() {
  return (
    <div className={knowledgeGraphStyles.headerContainer}>
      <h1 className={knowledgeGraphStyles.title}>Peta Memori</h1>
      <p className={knowledgeGraphStyles.description}>
        Ini adalah gambaran hubungan antara memori, pikiran, dan dirimu.
      </p>
    </div>
  );
}

export function SensitiveToggle({ hidden, onToggle }: { hidden: boolean; onToggle: () => void }) {
  return (
    <button onClick={onToggle} className={knowledgeGraphStyles.sensitiveToggleBtn}>
      {hidden ? <EyeOff className={knowledgeGraphStyles.sensitiveToggleIcon} /> : <Eye className={knowledgeGraphStyles.sensitiveToggleIcon} />}
      {hidden ? 'Sembunyikan yang sensitif' : 'Tampilkan yang sensitif'}
    </button>
  );
}

export function ExpandMapButton({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} className={knowledgeGraphStyles.expandBtn}>
      Perbesar peta <img src="/noun-rotate-phone.svg" alt="" className={knowledgeGraphStyles.expandIcon} style={{ filter: 'brightness(0) invert(1)' }} aria-hidden="true" />
    </button>
  );
}

export function LandscapeNotice() {
  return (
    <p className={knowledgeGraphStyles.noticeContainer}>
      <Smartphone className={knowledgeGraphStyles.noticeIcon} />
      Lebih nyaman dilihat saat HP dimiringkan.
    </p>
  );
}

export function ExpandedGraphHeader({ onBack }: { onBack: () => void }) {
  return (
    <header className={knowledgeGraphStyles.expandedHeaderContainer}>
      <div className={knowledgeGraphStyles.expandedHeaderContent}>
        <button onClick={onBack} className={knowledgeGraphStyles.expandedBackBtn}>
          <ArrowLeft className={knowledgeGraphStyles.expandedBackIcon} /> Kembali
        </button>
        <div>
          <h1 className={knowledgeGraphStyles.expandedTitle}>Peta Memori </h1>
          <p className={knowledgeGraphStyles.expandedDescription}>Gambaran hal-hal penting dalam hidupmu.</p>
        </div>
      </div>
    </header>
  );
}

export function ExpandedGraphFooter({ zoom, fitZoom, onZoom }: { zoom: number; fitZoom: number; onZoom: (dir: number) => void }) {
  return (
    <footer className={knowledgeGraphStyles.expandedFooterContainer}>
      <div className={knowledgeGraphStyles.expandedZoomControls}>
        <button onClick={() => onZoom(-1)} aria-label="Perkecil" className={knowledgeGraphStyles.expandedZoomBtn}>
          <Minus className={knowledgeGraphStyles.expandedZoomIcon} />
        </button>
        <span className={knowledgeGraphStyles.expandedZoomText}>
          {Math.round((zoom / fitZoom) * 100)}%
        </span>
        <button onClick={() => onZoom(1)} aria-label="Perbesar" className={knowledgeGraphStyles.expandedZoomBtn}>
          <Plus className={knowledgeGraphStyles.expandedZoomIcon} />
        </button>
      </div>

      <div className={knowledgeGraphStyles.expandedHelperContainer}>
        <span className={knowledgeGraphStyles.expandedHelperItem}>
          <Hand className={knowledgeGraphStyles.expandedHelperIcon} /> Geser untuk berpindah
        </span>
        <span className={knowledgeGraphStyles.expandedHelperDot}>•</span>
        <span className={knowledgeGraphStyles.expandedHelperItem}>
          <ZoomIn className={knowledgeGraphStyles.expandedHelperIcon} /> Cubit untuk zoom
        </span>
      </div>

      <div className={knowledgeGraphStyles.expandedMinimapContainer}>
        <svg width="84" height="52" viewBox="0 0 84 52" aria-hidden="true">
          <rect x="26" y="6" width="34" height="22" rx="5" fill="none" stroke="var(--v2-c-a9a291)" strokeWidth="1.6" />
          <circle cx="42" cy="30" r="5" fill="var(--v2-c-8b9370)" />
          <circle cx="32" cy="12" r="3" fill="var(--v2-c-9aa77e)" />
          <circle cx="54" cy="12" r="3" fill="var(--v2-c-9aa77e)" />
          <circle cx="24" cy="44" r="3.4" fill="var(--v2-c-c26b4b)" />
          <circle cx="60" cy="44" r="3.4" fill="var(--v2-c-d9a13d)" />
          <line x1="42" y1="30" x2="24" y2="44" stroke="var(--v2-c-cbbc9e)" strokeWidth="1.3" />
          <line x1="42" y1="30" x2="60" y2="44" stroke="var(--v2-c-cbbc9e)" strokeWidth="1.3" />
          <line x1="42" y1="30" x2="32" y2="12" stroke="var(--v2-c-cbbc9e)" strokeWidth="1.3" />
          <line x1="42" y1="30" x2="54" y2="12" stroke="var(--v2-c-cbbc9e)" strokeWidth="1.3" />
        </svg>
      </div>
    </footer>
  );
}
