'use client';

import { AppShell } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { useT } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import { ExternalLink, Mail, MapPin, MessageCircle, Phone, ShieldAlert } from 'lucide-react';

type Hotline = {
  id: string;
  name: string;
  contact: string[];
  methods?: string[];
  availability: string;
  audience: string[];
  supportType?: string[];
  scope: string[];
  url: string;
  address?: string;
};

const HOTLINES: Hotline[] = [
  {
    id: 'healing119',
    name: 'Healing119.id Hotline',
    contact: ['119'],
    methods: ['Call', 'WhatsApp'],
    availability: 'Nasional, Indonesia',
    audience: ['Everyone'],
    supportType: ['Counselors', 'Volunteers'],
    scope: ['Suicide', 'Anxiety', 'Bullying', 'Depression', 'Loneliness', 'Self-harm', 'Stress', 'Supporting others', 'Trauma & PTSD'],
    url: 'https://findahelpline.com/organizations/healing119-id-hotline',
  },
  {
    id: 'lisa',
    name: 'LISA Suicide Prevention Helpline',
    contact: ['ID: +62 811 3855 472', 'EN: +62 811 3815 472'],
    methods: ['WhatsApp'],
    availability: '24 jam, bahasa Indonesia dan English',
    audience: ['Everyone'],
    scope: ['Dukungan kesehatan mental', 'Self-harm', 'Ide atau percobaan bunuh diri', 'Rujukan layanan kesehatan mental'],
    url: 'https://www.intothelightid.org/tentang-bunuh-diri/hotline-bunuh-diri-di-indonesia/',
  },
  {
    id: 'sapa129',
    name: 'SAPA Service 129',
    contact: ['08111 129 129'],
    methods: ['Call', 'WhatsApp'],
    availability: 'Nasional, Indonesia',
    audience: ['Women', 'Children'],
    supportType: ['Counselors'],
    scope: ['Abuse & domestic violence', 'Sexual abuse'],
    url: 'https://findahelpline.com/organizations/sapa-service-129',
  },
  {
    id: 'wcc-jombang',
    name: "Women's Crisis Center Jombang Helpline",
    contact: ['081 235 020 62'],
    methods: ['Call', 'WhatsApp'],
    availability: 'Nasional, Indonesia',
    audience: ['Women', 'Children'],
    supportType: ['Counselors'],
    scope: ['Abuse & domestic violence', 'Sexual abuse', 'Konsultasi hukum', 'Konsultasi psikologi', 'Pendampingan kasus kekerasan berbasis gender'],
    url: 'https://findahelpline.com/organizations/women-s-crisis-center-jombang-helpline',
  },
  {
    id: 'itb-counseling',
    name: 'Bimbingan Konseling Direktorat Kemahasiswaan ITB',
    contact: ['Email: bk@kemahasiswaan.itb.ac.id', 'Phone: (022) 2534275', 'Fax/Phone: (022) 2504814'],
    availability: 'Jam kerja kampus',
    audience: ['ITB students'],
    address: 'Gedung CC Timur, Lantai 2, Jalan Ganesa No. 10, Bandung',
    scope: ['Layanan konseling mahasiswa ITB'],
    url: 'https://kemahasiswaan.itb.ac.id/counseling',
  },
  {
    id: 'yayasan-pulih',
    name: 'Yayasan Pulih',
    contact: ['WhatsApp Admin: +62 811 843 6633', 'Phone: +62 21 7884 2580', 'Email: pulihfoundation@gmail.com'],
    availability: 'Jam kerja, pendaftaran melalui admin WhatsApp',
    audience: ['Everyone'],
    scope: ['Konseling psikologis', 'Pemulihan trauma', 'Bukan layanan darurat 24 jam'],
    url: 'https://www.yayasanpulih.org/our-services/layanan-konseling-psikologi',
  },
  {
    id: 'psc119',
    name: 'Layanan Darurat Medis / PSC 119',
    contact: ['119'],
    availability: '24 jam',
    audience: ['Everyone'],
    scope: ['Keadaan darurat medis', 'Ancaman keselamatan nyawa', 'Cedera aktif', 'Kondisi yang membutuhkan ambulans atau IGD'],
    url: 'https://kemkes.go.id/id/akses-darurat-medis-119-kini-bisa-melalui-satusehat-mobile',
  },
  {
    id: 'findahelpline',
    name: 'Find A Helpline Indonesia',
    contact: ['https://findahelpline.com/countries/id'],
    availability: 'Direktori online',
    audience: ['Everyone'],
    scope: ['Direktori helpline Indonesia', 'Menampilkan layanan berdasarkan topik seperti suicide, anxiety, depression, self-harm, abuse, stress, dan trauma'],
    url: 'https://findahelpline.com/countries/id',
  },
];

export default function HotlinesPage() {
  const t = useT();
  const emergency = HOTLINES.find((hotline) => hotline.id === 'psc119') || HOTLINES[0];

  return (
    <AppShell>
      <div className="axis-page">
        <section className="flex flex-col gap-5 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              {t('hotlinesEyebrow')}
            </p>
            <h1 className="mt-3 text-4xl font-semibold leading-none tracking-[-0.05em] sm:text-5xl">
              {t('hotlinesTitle')}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">
              {t('hotlinesDescription')}
            </p>
          </div>

          <div className="border-t border-border pt-4 md:border-t-0 md:pt-0">
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              {t('hotlinesDirectoryStatus')}
            </p>
            <p className="mt-1 text-sm font-semibold tracking-[-0.01em]">{t('hotlinesVerified')}</p>
          </div>
        </section>

        <section className="mt-6 rounded-xl border border-destructive/25 bg-destructive/8 p-4 shadow-[var(--axis-shadow-soft)] sm:p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-full border border-destructive/25 bg-background/65 text-destructive">
                <ShieldAlert className="size-4" />
              </div>
              <div>
                <h2 className="text-base font-semibold tracking-[-0.02em]">
                  {t('hotlinesEmergencyTitle')}
                </h2>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {t('hotlinesEmergencyDescription')}
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-2 sm:flex-row">
              <a href={buildContactHref(emergency.contact[0]) || emergency.url} target="_blank" rel="noreferrer">
                <Button className="w-full gap-2 sm:w-auto">
                  <Phone className="size-4" />
                  {emergency.contact[0]}
                </Button>
              </a>
              <a href={emergency.url} target="_blank" rel="noreferrer">
                <Button variant="outline" className="w-full gap-2 bg-card sm:w-auto">
                  {t('openResource')}
                  <ExternalLink className="size-4" />
                </Button>
              </a>
            </div>
          </div>
        </section>

        <section className="mt-6 overflow-hidden rounded-xl border border-border bg-card shadow-[var(--axis-shadow-soft)]">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] border-b border-border bg-muted/20 px-4 py-3 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground sm:px-5">
            <span>{t('hotlinesSupportResource')}</span>
            <span>{t('hotlinesContact')}</span>
          </div>

          <div className="divide-y divide-border">
            {HOTLINES.map((hotline, index) => (
              <article
                key={hotline.id}
                className="grid gap-4 px-4 py-5 transition-[background-color] duration-200 hover:bg-muted/30 sm:px-5 lg:grid-cols-[minmax(0,1fr)_360px]"
              >
                <div className="min-w-0">
                  <div className="flex items-start gap-3">
                    <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background font-mono text-xs font-semibold text-primary">
                      {String(index + 1).padStart(2, '0')}
                    </div>
                    <div className="min-w-0">
                      <h2 className="text-lg font-semibold leading-7 tracking-[-0.02em]">{hotline.name}</h2>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className="axis-chip">{hotline.availability}</span>
                        {hotline.methods?.map((method) => (
                          <span key={method} className="axis-chip">
                            {method}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-4 md:grid-cols-[180px_minmax(0,1fr)]">
                    <div>
                      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                        {t('hotlinesAudience')}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {hotline.audience.map((audience) => (
                          <span key={audience} className="rounded-md border border-border bg-muted/30 px-2 py-1 text-xs text-foreground">
                            {audience}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                        {t('hotlinesScope')}
                      </p>
                      <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">
                        {hotline.scope.join(', ')}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex min-w-0 flex-col gap-3 lg:border-l lg:border-border lg:pl-5">
                  <div className="grid gap-2">
                    {hotline.contact.slice(0, 3).map((contact) => {
                      const href = buildContactHref(contact);
                      const content = (
                        <ContactLine contact={contact} muted={!href} />
                      );

                      return href ? (
                        <a key={contact} href={href} target={href.startsWith('http') ? '_blank' : undefined} rel="noreferrer">
                          {content}
                        </a>
                      ) : (
                        <div key={contact}>{content}</div>
                      );
                    })}
                    {hotline.address && (
                      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/20 px-3 py-2 text-sm text-muted-foreground">
                        <MapPin className="mt-0.5 size-4 shrink-0" />
                        <span className="break-words leading-5">{hotline.address}</span>
                      </div>
                    )}
                  </div>

                  <a href={hotline.url} target="_blank" rel="noreferrer" className="mt-auto">
                    <Button variant="outline" className="w-full gap-2 bg-card">
                      {t('openResource')}
                      <ExternalLink className="size-4" />
                    </Button>
                  </a>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function ContactLine({ contact, muted }: { contact: string; muted?: boolean }) {
  const Icon = getContactIcon(contact);

  return (
    <div
      className={cn(
        'flex items-start gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm transition-[background-color,border-color,transform] duration-200',
        muted ? 'text-muted-foreground' : 'hover:-translate-y-0.5 hover:border-ring/35 hover:bg-muted/35'
      )}
    >
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <span className="break-words font-medium leading-5">{contact}</span>
    </div>
  );
}

function getContactIcon(contact: string) {
  const normalized = contact.toLowerCase();
  if (normalized.includes('email')) return Mail;
  if (normalized.includes('whatsapp')) return MessageCircle;
  if (normalized.startsWith('http')) return ExternalLink;
  return Phone;
}

function buildContactHref(contact: string) {
  const trimmed = contact.trim();
  const normalized = trimmed.toLowerCase();
  if (normalized.startsWith('http')) return trimmed;

  const emailMatch = trimmed.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  if (emailMatch) return `mailto:${emailMatch[0]}`;

  const phone = trimmed.replace(/[^\d+]/g, '');
  if (!phone) return '';
  return `tel:${phone}`;
}
