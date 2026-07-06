'use client';

import {
  ExternalLink,
  GraduationCap,
  HeartHandshake,
  List,
  Mail,
  MessageCircle,
  Phone,
  Search,
  Shield,
  UsersRound,
} from '@/lib/assets';
import { useMemo, useState } from 'react';
import { V2Shell } from '@/components/v2/V2Shell';
import { cn } from '@/lib/utils';

type HotlineTier = 'Kesehatan Diri' | 'Kesehatan Mental' | 'Lingkungan & Kehidupan';
type HotlineCategory = 'Semua' | HotlineTier;

/** Same 3-tier life-area taxonomy + colors as the Knowledge Graph expanded
 * map (`components/v2/kg/MindMap.tsx`'s GROUPS) — kept identical so the two
 * pages read as one consistent system rather than two different category
 * schemes. */
const TIER_STYLE: Record<HotlineTier, { pill: string; chipBg: string; chipBorder: string }> = {
  'Kesehatan Diri': { pill: '#838c70', chipBg: '#e9ecdb', chipBorder: '#d8ddc2' },
  'Kesehatan Mental': { pill: '#a0a287', chipBg: '#e9ecdb', chipBorder: '#d8ddc2' },
  'Lingkungan & Kehidupan': { pill: '#b3b89d', chipBg: '#e9ecdb', chipBorder: '#d8ddc2' },
};

const FILTERS: HotlineCategory[] = ['Semua', 'Kesehatan Diri', 'Kesehatan Mental', 'Lingkungan & Kehidupan'];

type HotlineResource = {
  id: string;
  name: string;
  description: string;
  badge: string;
  /** Individually-tappable contact lines (tel:/wa/mailto) — restored from
   * v1, which v2's earlier single-`href`-per-card design had lost. */
  contacts: string[];
  category: HotlineTier;
  url: string;
  icon: typeof Phone;
  tone: 'clay' | 'olive' | 'gold' | 'sage';
};

const RESOURCES: HotlineResource[] = [
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

const TONE_CLASS = {
  clay: { bubble: 'bg-[#f7ddd0] text-[var(--v2-clay)]' },
  olive: { bubble: 'bg-[#ecece1] text-[var(--v2-olive-deep)]' },
  gold: { bubble: 'bg-[#f9ecd2] text-[#d99f2c]' },
  sage: { bubble: 'bg-[#eeeede] text-[var(--v2-olive-deep)]' },
} as const;

function buildContactHref(contact: string): string {
  const trimmed = contact.trim();
  const normalized = trimmed.toLowerCase();
  if (normalized.startsWith('http')) return trimmed;
  const emailMatch = trimmed.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  if (emailMatch) return `mailto:${emailMatch[0]}`;
  const phone = trimmed.replace(/[^\d+]/g, '');
  return phone ? `tel:${phone}` : '';
}

function contactIcon(contact: string) {
  const normalized = contact.toLowerCase();
  if (normalized.includes('email')) return Mail;
  if (normalized.includes('whatsapp')) return MessageCircle;
  return Phone;
}

export default function HotlinesPage() {
  const [query, setQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<HotlineCategory>('Semua');

  const filteredResources = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return RESOURCES.filter((resource) => {
      const matchesFilter = activeFilter === 'Semua' || resource.category === activeFilter;
      const haystack = `${resource.name} ${resource.description}`.toLowerCase();
      const matchesQuery = !normalized || haystack.includes(normalized);
      return matchesFilter && matchesQuery;
    });
  }, [activeFilter, query]);

  return (
    <V2Shell>
      <main className="space-y-4 pb-4">
        <section className="space-y-1.5 pt-2">
          <h1 className="text-[25px] font-bold leading-[1.1] tracking-[-0.04em] text-[var(--v2-ink)]">
            Hotline & Bantuan Darurat
          </h1>
          <p className="text-[14px] font-medium leading-relaxed text-[#34312d]">
            Kamu tidak sendiri. Bantuan selalu ada untukmu.
          </p>
        </section>

        <EmergencyHero />

        <label className="flex h-[50px] items-center gap-3 rounded-[16px] border border-[#e8dcc8] bg-[#fffaf3]/78 px-4 shadow-[0_10px_26px_rgb(83_67_46_/_0.035)]">
          <Search className="h-[20px] w-[20px] shrink-0 text-[var(--v2-olive-deep)]" strokeWidth={2.35} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            type="search"
            aria-label="Cari layanan hotline"
            placeholder="Cari layanan atau situasi..."
            className="min-w-0 flex-1 bg-transparent text-[13.5px] font-medium text-[var(--v2-ink)] outline-none placeholder:text-[#8d897f]"
          />
        </label>

        <section className="-mx-1 flex items-center gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <button
            type="button"
            onClick={() => setActiveFilter('Semua')}
            className={cn(
              'h-[34px] shrink-0 rounded-full border px-4 text-[12px] font-semibold transition-colors',
              activeFilter === 'Semua'
                ? 'border-[var(--v2-olive)] bg-[var(--v2-olive)] text-white shadow-[0_8px_18px_rgb(93_105_73_/_0.18)]'
                : 'border-[#e8ddca] bg-[#fffaf3]/70 text-[var(--v2-ink)]'
            )}
          >
            Semua
          </button>
          {FILTERS.slice(1).map((filter, index) => {
            const tier = TIER_STYLE[filter as HotlineTier];
            const active = activeFilter === filter;
            return (
              <button
                key={filter}
                type="button"
                onClick={() => setActiveFilter(filter)}
                // Extra gap ahead of the first tier chip (vs. the 8px between
                // "Semua" and everything else) so the tier chips visually
                // read as one distinct group, matching the KG page's same
                // taxonomy. All chips stay on one row -- horizontal scroll
                // (not wrap) when they overflow the viewport width.
                className={cn(
                  'h-[34px] shrink-0 rounded-full border px-4 text-[12px] font-semibold transition-colors',
                  index === 0 && 'ml-1'
                )}
                style={
                  active
                    ? { backgroundColor: tier.pill, borderColor: tier.pill, color: '#fffaf3' }
                    : { backgroundColor: tier.chipBg, borderColor: tier.chipBorder, color: 'var(--v2-ink)' }
                }
              >
                {filter}
              </button>
            );
          })}
        </section>

        <section id="daftar-hotline" className="space-y-3">
          {filteredResources.map((resource) => (
            <HotlineCard key={resource.id} resource={resource} />
          ))}
          {filteredResources.length === 0 ? (
            <div className="rounded-[19px] border border-dashed border-[var(--v2-line)] px-5 py-8 text-center">
              <p className="text-[15px] font-bold text-[var(--v2-ink)]">Belum ada layanan yang cocok.</p>
              <p className="mt-1 text-[13px] font-medium text-[var(--v2-muted)]">
                Coba kata kunci lain atau pilih kategori Semua.
              </p>
            </div>
          ) : null}
        </section>

        <section className="flex items-center gap-3 rounded-[18px] border border-[#eadfcb] bg-[#fffaf3]/76 px-4 py-3">
          <span className="relative h-10 w-10 shrink-0 text-[var(--v2-olive-deep)]" aria-hidden="true">
            <span className="absolute bottom-0 left-2 h-7 w-2 rounded-full bg-[var(--v2-olive)] rotate-[-26deg]" />
            <span className="absolute bottom-1 left-5 h-8 w-2 rounded-full bg-[#8f9c72] rotate-[24deg]" />
            <span className="absolute bottom-0 left-4 h-10 w-[2px] rounded-full bg-[#657154]" />
          </span>
          <p className="text-[12.5px] font-medium leading-[1.45] text-[#34312d]">
            Semua layanan di atas aman, rahasia, dan gratis. AXIS peduli dan mendukungmu.
          </p>
        </section>
      </main>
    </V2Shell>
  );
}

function EmergencyHero() {
  return (
    <section className="relative overflow-hidden rounded-[23px] border border-[#efc8b6] bg-[#fae4d7] px-3.5 pb-3.5 pt-4 shadow-[0_16px_30px_rgb(154_93_64_/_0.08)]">
      {/* <img
        src="/illustrations/hotline-hero-person.svg"
        alt=""
        className="pointer-events-none absolute -right-7 top-1 h-[178px] w-[178px] object-contain opacity-95"
        aria-hidden="true"
      /> */}

      <div className="relative z-10 flex gap-2.5 pr-[70px]">
        <div className="grid h-[66px] w-[66px] shrink-0 place-items-center rounded-full bg-[#fff4ec] shadow-[inset_0_0_0_1px_rgb(238_202_183_/_0.75)]">
          <div className="grid h-[41px] w-[41px] place-items-center rounded-[15px] bg-[var(--v2-clay)] text-white shadow-[0_12px_20px_rgb(192_92_55_/_0.2)]">
            <Shield className="h-6 w-6 fill-current" strokeWidth={1.9} />
          </div>
        </div>
        <div className="min-w-0 pt-0.5">
          <h2 className="text-[14.5px] font-bold leading-[1.35] tracking-[-0.02em] text-[var(--v2-ink)]">
            Jika kamu merasa tidak aman atau butuh bantuan sekarang, hubungi segera.
          </h2>
          <p className="mt-1.5 text-[12px] font-medium leading-relaxed text-[#4d453d]">
            Keselamatanmu adalah prioritas.
          </p>
        </div>
      </div>

      <div className="relative z-10 mt-4 grid grid-cols-2 gap-2">
        <a
          href="tel:119"
          className="v2-anim-pressable inline-flex h-[42px] items-center justify-center gap-2 rounded-full bg-[var(--v2-clay)] px-3 text-[11.5px] font-bold text-white shadow-[0_10px_20px_rgb(192_92_55_/_0.18)]"
        >
          <Phone className="h-[15px] w-[15px] fill-current" strokeWidth={2.1} />
          Hubungi sekarang
        </a>
        <a
          href="#daftar-hotline"
          className="v2-anim-pressable inline-flex h-[42px] items-center justify-center gap-2 rounded-full border border-[var(--v2-clay)] bg-[#fff8f1] px-3 text-[11.5px] font-bold text-[var(--v2-clay)] shadow-[0_8px_16px_rgb(154_93_64_/_0.06)]"
        >
          <List className="h-[15px] w-[15px]" strokeWidth={2.4} />
          Lihat semua hotline
        </a>
      </div>
    </section>
  );
}

function HotlineCard({ resource }: { resource: HotlineResource }) {
  const Icon = resource.icon;
  const tone = TONE_CLASS[resource.tone];
  const tier = TIER_STYLE[resource.category];

  return (
    <article className="overflow-hidden rounded-[18px] border border-[#eadfcb] bg-[#fffaf3]/74 shadow-[0_10px_24px_rgb(83_67_46_/_0.035)]">
      <div className="flex gap-3 p-3">
        <div className={cn('grid h-[54px] w-[54px] shrink-0 place-items-center rounded-full', tone.bubble)}>
          <Icon className="h-[27px] w-[27px]" strokeWidth={2.25} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h2 className="text-[13.5px] font-bold leading-tight text-[var(--v2-ink)]">{resource.name}</h2>
            <a
              href={resource.url}
              target="_blank"
              rel="noreferrer"
              aria-label={`Buka info ${resource.name}`}
              className="v2-anim-pressable shrink-0 text-[var(--v2-olive-deep)]"
            >
              <ExternalLink className="h-[15px] w-[15px]" strokeWidth={2.25} />
            </a>
          </div>
          <p className="mt-0.5 text-[11.5px] font-medium leading-[1.34] text-[#4c4a45]">{resource.description}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span className="inline-flex rounded-full bg-[#fbecdf] px-2 py-0.5 text-[9.5px] font-bold text-[var(--v2-clay)]">
              {resource.badge}
            </span>
            <span
              className="inline-flex rounded-full px-2 py-0.5 text-[9.5px] font-bold"
              style={{ backgroundColor: tier.chipBg, color: tier.pill }}
            >
              {resource.category}
            </span>
          </div>
        </div>
      </div>

      {resource.contacts.length ? (
        <div className="grid gap-1.5 border-t border-[#eadfcb] px-3 py-2.5">
          {resource.contacts.map((contact) => {
            const href = buildContactHref(contact);
            const ContactIcon = contactIcon(contact);
            return (
              <a
                key={contact}
                href={href || undefined}
                target={href.startsWith('http') ? '_blank' : undefined}
                rel="noreferrer"
                className="v2-anim-pressable flex items-center gap-2 rounded-[12px] border border-[#eadfcb] bg-white/70 px-3 py-2 text-[11.5px] font-semibold text-[var(--v2-ink)]"
              >
                <ContactIcon className="h-[13px] w-[13px] shrink-0 text-[var(--v2-olive-deep)]" />
                <span className="min-w-0 truncate">{contact}</span>
              </a>
            );
          })}
        </div>
      ) : null}
    </article>
  );
}
