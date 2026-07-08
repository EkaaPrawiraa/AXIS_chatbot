'use client';

import { useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { AuthHero } from '@/components/v2/auth/AuthHero';
import { SegmentedControl } from '@/components/v2/SegmentedControl';
import { AuthForm } from '@/components/v2/auth/AuthForm';
import { SocialLogin } from '@/components/v2/auth/SocialLogin';
import { authStyles } from '@/lib/styles/authStyles';
import { animationClasses, motionStyleVars } from '@/lib/animations';

type AuthMode = 'login' | 'register';

function AuthContent() {
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<AuthMode>('register');
  const next = searchParams.get('next') || '/chat';

  return (
    <main className={authStyles.pageContainer}>
      <section
        className={`${authStyles.contentWrapper} ${animationClasses.pageEnter}`}
        style={motionStyleVars({ durationMs: 360 })}
      >
        <AuthHero />

        <SegmentedControl
          className="mt-4"
          value={mode}
          onChange={(value) => setMode(value)}
          options={[
            { value: 'login', label: 'Masuk' },
            { value: 'register', label: 'Daftar' },
          ]}
        />

        <AuthForm mode={mode} nextPath={next} />

        <SocialLogin nextPath={next} />

        <button
          type="button"
          onClick={() => setMode(mode === 'register' ? 'login' : 'register')}
          className="v2-anim-pressable mt-5 pb-1 text-center text-[14.5px] font-medium text-[var(--v2-ink)]"
        >
          {mode === 'register' ? 'Sudah punya akun? ' : 'Belum punya akun? '}
          <span className="font-bold text-[var(--v2-olive)]">{mode === 'register' ? 'Masuk' : 'Daftar'}</span>
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
