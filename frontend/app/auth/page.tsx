'use client';

import { FormEvent, Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { authAPI } from '@/lib/api/auth';
import { useSessionStore } from '@/stores';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { HeartHandshake, Loader2, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { useT } from '@/lib/i18n';
import { usePreferencesStore } from '@/stores';

export default function AuthPage() {
  return (
    <Suspense fallback={<AuthShell />}>
      <AuthPageContent />
    </Suspense>
  );
}

function AuthPageContent() {
  const t = useT();
  const router = useRouter();
  const searchParams = useSearchParams();
  const setSession = useSessionStore((state) => state.setSession);
  const appLanguage = usePreferencesStore((state) => state.language);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState(appLanguage);
  const [safetyTermsAccepted, setSafetyTermsAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const session =
        mode === 'login'
          ? await authAPI.login({ email, password })
          : await authAPI.register({
              email,
              password,
              displayName,
              preferredLanguage,
              safetyTermsAccepted,
              safetyTermsVersion: 'companion-safety-v1',
            });
      setSession(session);
      const next = searchParams.get('next');
      router.push(next?.startsWith('/') ? next : '/chat');
    } catch (err: any) {
      setError(err?.response?.data?.message || t('couldNotAuth'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-[100dvh] bg-background px-4 py-8 sm:px-6">
      <div className="mx-auto grid min-h-[calc(100dvh-4rem)] max-w-6xl items-center gap-10 lg:grid-cols-[1fr_440px]">
        <section className="order-1 max-w-3xl">
          <Link href="/" className="mb-12 inline-flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            <span className="flex size-8 items-center justify-center rounded-md bg-muted text-primary">
              <HeartHandshake className="h-4 w-4" />
            </span>
            {t('appName')}
          </Link>
          <h1 className="max-w-3xl text-balance text-5xl font-semibold leading-[0.96] tracking-[-0.06em] md:text-7xl">{t('authHero')}</h1>
          <p className="mt-5 max-w-[62ch] text-lg leading-8 text-muted-foreground">
            {t('authDescription')}
          </p>
          <div className="mt-10 grid max-w-2xl gap-3 sm:grid-cols-2">
            <div className="axis-section p-5">
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{t('authVoiceFirst')}</p>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">{t('authVoiceFirstDescription')}</p>
            </div>
            <div className="axis-section p-5">
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{t('authPrivateMemory')}</p>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">{t('authPrivateMemoryDescription')}</p>
            </div>
          </div>
        </section>

        <Card className="order-2 p-6">
          <Tabs value={mode} onValueChange={(value) => setMode(value as 'login' | 'register')}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login">{t('login')}</TabsTrigger>
              <TabsTrigger value="register">{t('register')}</TabsTrigger>
            </TabsList>

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <TabsContent value="login" className="m-0 space-y-4" forceMount hidden={mode !== 'login'}>
                <div>
                  <h2 className="text-2xl font-semibold tracking-[-0.035em]">{t('welcomeBack')}</h2>
                  <p className="text-sm leading-6 text-muted-foreground">{t('continueConversation')}</p>
                </div>
              </TabsContent>

              <TabsContent value="register" className="m-0 space-y-4" forceMount hidden={mode !== 'register'}>
                <div>
                  <h2 className="text-2xl font-semibold tracking-[-0.035em]">{t('createAccount')}</h2>
                  <p className="text-sm leading-6 text-muted-foreground">{t('createAccountDescription')}</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="displayName">{t('name')}</Label>
                  <div className="relative">
                    <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="displayName"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                      placeholder={t('yourName')}
                      className="pl-9"
                      required={mode === 'register'}
                    />
                  </div>
                </div>
              </TabsContent>

              <div className="space-y-2">
                <Label htmlFor="email">{t('email')}</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder={t('emailPlaceholder')}
                    className="pl-9"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">{t('password')}</Label>
                <div className="relative">
                  <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder={t('minPassword')}
                    className="pl-9"
                    minLength={5}
                    required
                  />
                </div>
              </div>

              {mode === 'register' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="preferredLanguage">{t('preferredLanguage')}</Label>
                    <select
                      id="preferredLanguage"
                      value={preferredLanguage}
                      onChange={(event) => setPreferredLanguage(event.target.value as 'id' | 'en')}
                      className="axis-field-select"
                    >
                      <option value="id">{t('indonesian')}</option>
                      <option value="en">{t('english')}</option>
                    </select>
                  </div>
                  <label className="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-3 text-sm leading-6">
                    <input
                      type="checkbox"
                      checked={safetyTermsAccepted}
                      onChange={(event) => setSafetyTermsAccepted(event.target.checked)}
                      className="mt-1"
                      required={mode === 'register'}
                    />
                    <span className="text-muted-foreground">{t('safetyRegisterAgreement')}</span>
                  </label>
                </>
              )}

              {error && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {mode === 'login' ? t('login') : t('createAccount')}
              </Button>
            </form>
          </Tabs>
        </Card>
      </div>
    </main>
  );
}

function AuthShell() {
  return (
    <main className="min-h-[100dvh] bg-background px-4 py-8 sm:px-6">
      <div className="mx-auto grid min-h-[calc(100dvh-4rem)] max-w-6xl items-center gap-10 lg:grid-cols-[1fr_440px]">
        <section className="order-1 max-w-3xl">
          <div className="mb-12 h-12 w-36 animate-pulse rounded-lg bg-muted" />
          <div className="h-24 max-w-2xl animate-pulse rounded-xl bg-muted" />
          <div className="mt-5 h-16 max-w-xl animate-pulse rounded-xl bg-muted/70" />
        </section>
        <Card className="order-2 p-6">
          <div className="h-10 animate-pulse rounded-lg bg-muted" />
          <div className="mt-6 space-y-4">
            <div className="h-16 animate-pulse rounded-xl bg-muted/70" />
            <div className="h-12 animate-pulse rounded-xl bg-muted/70" />
            <div className="h-12 animate-pulse rounded-xl bg-muted/70" />
          </div>
        </Card>
      </div>
    </main>
  );
}
