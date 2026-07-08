import React from 'react';
import { Eye, EyeOff, MoveDiagonal, Smartphone } from '@/lib/assets';
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
