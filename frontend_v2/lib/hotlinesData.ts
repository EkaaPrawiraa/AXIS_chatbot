import {
  GraduationCap,
  HeartHandshake,
  List,
  Phone,
  Shield,
  UsersRound,
} from '@/lib/assets';

export type HotlineTier = 'Kesehatan Diri' | 'Kesehatan Mental' | 'Lingkungan & Kehidupan';
export type HotlineCategory = 'Semua' | HotlineTier;

export const TIER_STYLE: Record<HotlineTier, { pill: string; chipBg: string; chipBorder: string }> = {
  'Kesehatan Diri': { pill: 'var(--v2-olive-deep)', chipBg: 'var(--v2-c-e9ecdb)', chipBorder: 'var(--v2-c-d8ddc2)' },
  'Kesehatan Mental': { pill: 'var(--v2-olive)', chipBg: 'var(--v2-c-e9ecdb)', chipBorder: 'var(--v2-c-d8ddc2)' },
  'Lingkungan & Kehidupan': { pill: 'var(--v2-clay)', chipBg: 'var(--v2-c-e9ecdb)', chipBorder: 'var(--v2-c-d8ddc2)' },
};

export const FILTERS: HotlineCategory[] = ['Semua', 'Kesehatan Diri', 'Kesehatan Mental', 'Lingkungan & Kehidupan'];

export type HotlineResource = {
  id: string;
  name: string;
  description: string;
  badge: string;
  contacts: string[];
  category: HotlineTier;
  url: string;
  icon: typeof Phone;
  tone: 'clay' | 'olive' | 'gold' | 'sage';
};

export const RESOURCES: HotlineResource[] = [
  {
    id: 'psc119',
    name: 'PSC 119 Darurat Medis',
    description: 'Bantuan darurat medis dan ambulans.',
    badge: 'Telepon · 24 jam',
    contacts: ['119'],
    category: 'Kesehatan Diri',
    url: 'https://kemkes.go.id/id/akses-darurat-medis-119-kini-bisa-melalui-satusehat-mobile',
    icon: Phone,
    tone: 'clay',
  },
  {
    id: 'healing119',
    name: 'Healing119.id Hotline',
    description: 'Dukungan emosi lewat call atau WhatsApp.',
    badge: 'Call / WhatsApp · Nasional',
    contacts: ['119'],
    category: 'Kesehatan Mental',
    url: 'https://findahelpline.com/organizations/healing119-id-hotline',
    icon: HeartHandshake,
    tone: 'olive',
  },
  {
    id: 'lisa',
    name: 'LISA Suicide Prevention Helpline',
    description: 'Dukungan krisis dan rujukan kesehatan mental.',
    badge: 'WhatsApp · 24 jam',
    contacts: ['ID: +62 811 3855 472', 'EN: +62 811 3815 472'],
    category: 'Kesehatan Mental',
    url: 'https://www.intothelightid.org/tentang-bunuh-diri/hotline-bunuh-diri-di-indonesia/',
    icon: Shield,
    tone: 'clay',
  },
  {
    id: 'sapa129',
    name: 'SAPA Service 129',
    description: 'Layanan bantuan untuk perempuan dan anak dalam situasi tidak aman.',
    badge: 'Call / WhatsApp · Nasional',
    contacts: ['08111 129 129'],
    category: 'Lingkungan & Kehidupan',
    url: 'https://findahelpline.com/organizations/sapa-service-129',
    icon: UsersRound,
    tone: 'gold',
  },
  {
    id: 'wcc-jombang',
    name: 'WCC Jombang Helpline',
    description: 'Dukungan kasus kekerasan berbasis gender, hukum, dan psikologi.',
    badge: 'Call / WhatsApp · Nasional',
    contacts: ['081 235 020 62'],
    category: 'Lingkungan & Kehidupan',
    url: 'https://findahelpline.com/organizations/women-s-crisis-center-jombang-helpline',
    icon: HeartHandshake,
    tone: 'sage',
  },
  {
    id: 'itb-counseling',
    name: 'Bimbingan Konseling ITB',
    description: 'Layanan konseling mahasiswa ITB.',
    badge: 'Kampus · Jam kerja',
    contacts: ['Email: bk@kemahasiswaan.itb.ac.id', 'Phone: (022) 2534275'],
    category: 'Kesehatan Mental',
    url: 'https://kemahasiswaan.itb.ac.id/counseling',
    icon: GraduationCap,
    tone: 'gold',
  },
  {
    id: 'yayasan-pulih',
    name: 'Yayasan Pulih',
    description: 'Konseling psikologis dan pemulihan trauma.',
    badge: 'WhatsApp admin · Jam kerja',
    contacts: ['WhatsApp Admin: +62 811 843 6633', 'Phone: +62 21 7884 2580', 'Email: pulihfoundation@gmail.com'],
    category: 'Kesehatan Mental',
    url: 'https://www.yayasanpulih.org/our-services/layanan-konseling-psikologi',
    icon: HeartHandshake,
    tone: 'olive',
  },
  {
    id: 'findahelpline',
    name: 'Find A Helpline Indonesia',
    description: 'Direktori online layanan bantuan.',
    badge: 'Direktori online',
    contacts: [],
    category: 'Lingkungan & Kehidupan',
    url: 'https://findahelpline.com/countries/id',
    icon: List,
    tone: 'sage',
  },
  {
    id: 'trusted-person',
    name: 'Teman Terpercaya',
    description: 'Hubungi orang dekat yang kamu percaya untuk menemani sementara.',
    badge: 'Dukungan pribadi',
    contacts: [],
    category: 'Lingkungan & Kehidupan',
    url: '/chat',
    icon: UsersRound,
    tone: 'sage',
  },
];

export const TONE_CLASS = {
  clay: { bubble: 'bg-[var(--v2-c-f7ddd0)] text-[var(--v2-clay)]' },
  olive: { bubble: 'bg-[var(--v2-c-ecece1)] text-[var(--v2-olive-deep)]' },
  gold: { bubble: 'bg-[var(--v2-c-f9ecd2)] text-[var(--v2-c-d99f2c)]' },
  sage: { bubble: 'bg-[var(--v2-c-eeeede)] text-[var(--v2-olive-deep)]' },
} as const;
