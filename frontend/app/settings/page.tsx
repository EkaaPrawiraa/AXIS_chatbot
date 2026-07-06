'use client';

import { AppShell } from '@/components/layout';
import { useRequireAuthRedirect } from '@/components/session';
import { Button } from '@/components/ui/button';
import { useT } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import { usePreferencesStore, type AppLanguage } from '@/stores';
import { Database, Languages, MessageSquareText, Moon, Shield, Sparkles, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import type { ChatResponseMode } from '@/models';

type ThemeOption = {
  value: 'light' | 'dark' | 'system';
  label: string;
  icon?: typeof Sun;
};

export default function SettingsPage() {
  const t = useT();
  const { isInitialized, isAuthenticated } = useRequireAuthRedirect();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const language = usePreferencesStore((state) => state.language);
  const chatResponseMode = usePreferencesStore((state) => state.chatResponseMode);

  useEffect(() => setMounted(true), []);
  const setLanguage = usePreferencesStore((state) => state.setLanguage);
  const setChatResponseMode = usePreferencesStore((state) => state.setChatResponseMode);

  const themeOptions: ThemeOption[] = [
    { value: 'light', label: t('light'), icon: Sun },
    { value: 'dark', label: t('dark'), icon: Moon },
    { value: 'system', label: t('system') },
  ];

  if (isInitialized && !isAuthenticated) {
    return null;
  }

  return (
    <AppShell>
      <div className="axis-page">
        <section className="flex flex-col gap-5 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              {t('settingsEyebrow')}
            </p>
            <h1 className="mt-3 text-4xl font-semibold leading-none tracking-[-0.05em] sm:text-5xl">
              {t('settingsTitle')}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">
              {t('settingsDescription')}
            </p>
          </div>

          <div className="flex items-center gap-6 border-t border-border pt-4 md:border-t-0 md:pt-0">
            <CompactStat label={t('theme')} value={mounted ? getThemeLabel(theme, t) : '...'} />
            <CompactStat label={t('appLanguage')} value={language === 'en' ? t('english') : t('indonesian')} />
          </div>
        </section>

        <section className="mt-6 overflow-hidden rounded-xl border border-border bg-card shadow-[var(--axis-shadow-soft)]">
          <SectionHeader
            icon={Sun}
            title={t('appearance')}
            description={t('appearanceDescription')}
          />

          <div className="divide-y divide-border">
            <SettingRow
              icon={Moon}
              title={t('theme')}
              description={t('themeDescription')}
            >
              <div className="grid w-full gap-2 sm:w-auto sm:grid-cols-3">
                {themeOptions.map((option) => {
                  const Icon = option.icon;
                  const isActive = mounted && theme === option.value;

                  return (
                    <Button
                      key={option.value}
                      variant={isActive ? 'default' : 'outline'}
                      onClick={() => setTheme(option.value)}
                      className={cn('justify-start gap-2 sm:justify-center', !isActive && 'bg-card')}
                    >
                      {Icon && <Icon className="size-4" />}
                      {option.label}
                    </Button>
                  );
                })}
              </div>
            </SettingRow>

            <SettingRow
              icon={Languages}
              title={t('appLanguage')}
              description={t('appLanguageDescription')}
            >
              <select
                value={language}
                onChange={(event) => setLanguage(event.target.value as AppLanguage)}
                className="axis-field-select w-full sm:w-64"
              >
                <option value="id">{t('indonesian')}</option>
                <option value="en">{t('english')}</option>
              </select>
            </SettingRow>

            <SettingRow
              icon={MessageSquareText}
              title={t('chatResponseMode')}
              description={t('chatResponseModeDescription')}
            >
              <div className="grid w-full gap-2 sm:w-auto sm:grid-cols-2">
                {([
                  ['normal', t('responseModeNormal'), t('responseModeNormalDescription'), MessageSquareText],
                  ['stream', t('responseModeStream'), t('responseModeStreamDescription'), Sparkles],
                ] as const).map(([value, label, description, Icon]) => {
                  const isActive = chatResponseMode === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setChatResponseMode(value as ChatResponseMode)}
                      className={cn(
                        'rounded-xl border px-3 py-3 text-left transition-[border-color,background-color,box-shadow]',
                        isActive
                          ? 'border-ring/50 bg-primary text-primary-foreground shadow-[var(--axis-shadow-soft)]'
                          : 'border-border bg-card hover:border-ring/35'
                      )}
                    >
                      <span className="flex items-center gap-2 text-sm font-semibold">
                        <Icon className="size-4" />
                        {label}
                      </span>
                      <span className={cn('mt-1 block text-xs leading-5', isActive ? 'text-primary-foreground/75' : 'text-muted-foreground')}>
                        {description}
                      </span>
                    </button>
                  );
                })}
              </div>
            </SettingRow>
          </div>
        </section>

        <section className="mt-5 overflow-hidden rounded-xl border border-border bg-card shadow-[var(--axis-shadow-soft)]">
          <SectionHeader
            icon={Shield}
            title={t('privacyData')}
            description={t('privacyDescription')}
          />

          <div className="divide-y divide-border">
            <SettingRow
              icon={Database}
              title={t('dataHandledByApp')}
              description={t('dataHandledByAppDescription')}
            >
              <p className="max-w-xs text-sm leading-6 text-muted-foreground lg:text-right">
                {t('dataResetLocation')}
              </p>
            </SettingRow>
          </div>
        </section>

        <section className="mt-5 rounded-xl border border-border bg-muted/20 px-4 py-4 sm:px-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                {t('about')}
              </p>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{t('aboutDescription')}</p>
            </div>
            <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
              {t('appVersion')}
            </p>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function CompactStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tracking-[-0.03em]">{value}</p>
    </div>
  );
}

function SectionHeader({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof Sun;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-3 border-b border-border bg-muted/20 px-4 py-4 sm:px-5">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background text-primary">
        <Icon className="size-4" />
      </div>
      <div>
        <h2 className="text-lg font-semibold tracking-[-0.025em]">{title}</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

function SettingRow({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: typeof Sun;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-4 px-4 py-5 sm:px-5 lg:grid-cols-[minmax(0,1fr)_minmax(220px,auto)] lg:items-center">
      <div className="flex gap-3">
        <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-muted/30 text-muted-foreground">
          <Icon className="size-4" />
        </div>
        <div>
          <h3 className="text-sm font-semibold tracking-[-0.01em]">{title}</h3>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="flex justify-start lg:justify-end">{children}</div>
    </div>
  );
}

function getThemeLabel(theme: string | undefined, t: ReturnType<typeof useT>) {
  if (theme === 'light') return t('light');
  if (theme === 'dark') return t('dark');
  return t('system');
}
