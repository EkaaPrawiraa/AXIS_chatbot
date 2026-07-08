import type { MemoryNodeType } from '@/models';


export const NODE_TYPES: Array<{
  type: MemoryNodeType;
  label: string;
  description: string;
}> = [
  {
    type: 'subject',
    label: 'Subjek',
    description: 'Subjek adalah "pihak" yang terkait dalam memorimu. Contoh: sekolah, keluarga, teman, diri sendiri.',
  },
  {
    type: 'experience',
    label: 'Pengalaman',
    description: 'Pengalaman adalah "momen" atau kejadian yang pernah kamu ceritakan ke AXIS.',
  },
  {
    type: 'trigger',
    label: 'Pemicu',
    description: 'Pemicu adalah hal yang biasanya "memantik" emosi, pikiran, atau perilaku tertentu.',
  },
  {
    type: 'thought',
    label: 'Pikiran',
    description: 'Pikiran adalah "pola pikir" yang muncul saat kamu menghadapi situasi tertentu.',
  },
  {
    type: 'behaviour',
    label: 'Perilaku',
    description: 'Perilaku adalah "respons" atau kebiasaan yang pernah kamu ceritakan.',
  },
  {
    type: 'topic',
    label: 'Topik',
    description: 'Topik adalah "tema" besar seperti akademik, relasi, diri, atau rutinitas.',
  },
  {
    type: 'memory',
    label: 'Memori',
    description: 'Memori adalah "ringkasan konteks" yang membantu percakapan berikutnya tetap berkesinambungan.',
  },
  {
    type: 'emotion',
    label: 'Perasaan',
    description: 'Perasaan adalah "emosi" yang pernah kamu rasakan dalam ceritamu.',
  },
];

export const NODE_TYPE_DESCRIPTION: Record<string, string> = Object.fromEntries(
  NODE_TYPES.map((item) => [item.type, item.description])
);
