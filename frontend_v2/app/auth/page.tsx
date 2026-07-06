'use client';

import { Eye, EyeOff, Globe, Lock, Mail, UserRound } from '@/lib/assets';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import { authAPI } from '@/lib/api/auth';
import { animationClasses, motionStyleVars } from '@/lib/animations';
import { friendlyErrorMessage } from '@/lib/errorMessages';
import { useSessionStore } from '@/stores';
import { usePreferencesStore } from '@/stores/preferences';
import { AuthHero } from '@/components/v2/AuthHero';
import { GoogleSignInButton } from '@/components/v2/GoogleSignInButton';
import { SegmentedControl } from '@/components/v2/SegmentedControl';
import { SelectField } from '@/components/v2/SelectField';
import { TextField } from '@/components/v2/TextField';
import { V2Button } from '@/components/v2/V2Button';

type AuthMode = 'login' | 'register';

function AuthContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setSession = useSessionStore((state) => state.setSession);
  const setLanguage = usePreferencesStore((state) => state.setLanguage);
  const [mode, setMode] = useState<AuthMode>('register');
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState<'id' | 'en'>('id');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isRegister = mode === 'register';
  const next = searchParams.get('next') || '/chat';

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const session = isRegister
        ? await authAPI.register({
            email,
            password,
            displayName,
            preferredLanguage,
            // Real consent is captured post-registration by SafetyConsentGate,
            // which blocks the app until the user explicitly accepts.
            safetyTermsAccepted: false,
            safetyTermsVersion: 'v1',
          })
        : await authAPI.login({ email, password });

      setSession(session);
      setLanguage(session.user.preferredLanguage === 'en' ? 'en' : preferredLanguage);
      router.replace(next);
    } catch (err) {
      setError(friendlyErrorMessage(err, 'Belum berhasil masuk. Coba cek email dan password kamu.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleCredential = async (idToken: string) => {
    setError(null);
    setIsSubmitting(true);
    try {
      const session = await authAPI.googleLogin(idToken);
      setSession(session);
      setLanguage(session.user.preferredLanguage === 'en' ? 'en' : preferredLanguage);
      router.replace(next);
    } catch (err) {
      setError(friendlyErrorMessage(err, 'Masuk dengan Google belum berhasil. Coba lagi ya.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="v2-screen overflow-x-hidden">
      <section
        className={`mx-auto flex min-h-dvh w-full max-w-[420px] flex-col px-7 pb-4 pt-3 ${animationClasses.pageEnter}`}
        style={motionStyleVars({ durationMs: 360 })}
      >
        <AuthHero />

        <SegmentedControl
          className="mt-2.5"
          value={mode}
          onChange={(value) => setMode(value)}
          options={[
            { value: 'login', label: 'Masuk' },
            { value: 'register', label: 'Daftar' },
          ]}
        />

        <form onSubmit={submit} className="mt-5 space-y-3.5">
          <TextField
            label="Email"
            icon={<Mail className="h-[22px] w-[22px]" strokeWidth={2} />}
            placeholder="nama@email.com"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
          />

          <TextField
            label="Password"
            icon={<Lock className="h-[22px] w-[22px]" strokeWidth={2} />}
            placeholder={isRegister ? 'Buat password Anda' : 'Password kamu'}
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={isRegister ? 8 : undefined}
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            helper={isRegister ? 'Minimal 8 karakter dengan huruf dan angka.' : undefined}
            trailing={
              <button
                type="button"
                aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'}
                onClick={() => setShowPassword((value) => !value)}
                className="v2-anim-pressable absolute right-5 top-1/2 -translate-y-1/2 text-[var(--v2-olive)]"
              >
                {showPassword ? <EyeOff className="h-[22px] w-[22px]" /> : <Eye className="h-[22px] w-[22px]" />}
              </button>
            }
          />

          {isRegister ? (
            <div
              key="register-fields"
              className={`space-y-3.5 ${animationClasses.fieldGroupEnter}`}
            >
              <TextField
                label="Nama tampilan"
                icon={<UserRound className="h-[22px] w-[22px]" strokeWidth={2} />}
                placeholder="Nama yang akan ditampilkan"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                required
                autoComplete="name"
              />

              <SelectField
                label="Bahasa"
                icon={<Globe className="h-[22px] w-[22px]" strokeWidth={2} />}
                value={preferredLanguage}
                onChange={(event) => setPreferredLanguage(event.target.value as 'id' | 'en')}
              >
                <option value="id">Bahasa Indonesia</option>
                <option value="en">English</option>
              </SelectField>
            </div>
          ) : null}

          {error ? (
            <div className={`rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700 ${animationClasses.softPop}`}>
              {error}
            </div>
          ) : null}

          <V2Button className="h-[42px] min-h-[42px] w-full text-[16px]" disabled={isSubmitting}>
            {isSubmitting ? 'Sebentar...' : isRegister ? 'Buat akun' : 'Masuk'}
          </V2Button>
        </form>

        <div className="mt-4 flex items-center gap-3 text-[12px] font-medium text-[var(--v2-muted)]">
          <span className="h-px flex-1 bg-[var(--v2-line)]" />
          atau
          <span className="h-px flex-1 bg-[var(--v2-line)]" />
        </div>

        <div className="mt-3.5 flex justify-center">
          <GoogleSignInButton onCredential={handleGoogleCredential} disabled={isSubmitting} />
        </div>

        <button
          type="button"
          onClick={() => setMode(isRegister ? 'login' : 'register')}
          className="v2-anim-pressable mt-3 pb-1 text-center text-[14px] font-semibold text-[var(--v2-ink)]"
        >
          {isRegister ? 'Sudah punya akun? ' : 'Belum punya akun? '}
          <span className="font-bold text-[var(--v2-olive-link)]">{isRegister ? 'Masuk' : 'Daftar'}</span>
        </button>
      </section>
    </main>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={<main className="v2-screen v2-center">Memuat...</main>}>
      <AuthContent />
    </Suspense>
  );
}
