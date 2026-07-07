'use client';

import { ExternalLink, Mail, MessageCircle, Phone } from '@/lib/assets';
import { hotlineStyles } from '@/lib/styles/hotlineStyles';
import { dashboardStyles } from '@/lib/styles/dashboard';
import {
  TIER_STYLE,
  TONE_CLASS,
  type HotlineResource,
} from '@/lib/hotlinesData';

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

export function HotlineCard({ resource }: { resource: HotlineResource }) {
  const tone = TONE_CLASS[resource.tone];
  const tier = TIER_STYLE[resource.category];

  return (
    <article className={hotlineStyles.cardWrapper}>
      <div className={hotlineStyles.cardTitleRow}>
        <div className="flex flex-col">
          <h2 className={dashboardStyles.itemTitle}>
            {resource.name}
          </h2>
          <p className={dashboardStyles.itemDescription}>{resource.description}</p>
        </div>
        <a
          href={resource.url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Buka info ${resource.name}`}
          className={hotlineStyles.cardActionLink}
        >
          <ExternalLink className="h-[15px] w-[15px]" strokeWidth={2.25} />
        </a>
      </div>
      
      <div className={hotlineStyles.cardBadgeWrapper}>
        <span className={hotlineStyles.cardBadge}>
          {resource.badge}
        </span>
        <span
          className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold"
          style={{ backgroundColor: tier.chipBg, color: tier.pill }}
        >
          {resource.category}
        </span>
      </div>

      {resource.contacts.length ? (
        <div className={hotlineStyles.cardContactList}>
          {resource.contacts.map((contact) => {
            const href = buildContactHref(contact);
            const ContactIcon = contactIcon(contact);
            return (
              <a
                key={contact}
                href={href || undefined}
                target={href.startsWith('http') ? '_blank' : undefined}
                rel="noreferrer"
                className={hotlineStyles.cardContactItem}
              >
                <ContactIcon className={hotlineStyles.cardContactIcon} />
                <span>{contact}</span>
              </a>
            );
          })}
        </div>
      ) : null}
    </article>
  );
}
