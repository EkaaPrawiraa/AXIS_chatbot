import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Globe, Lock, Mail, UserRound } from '@/lib/assets';
import { authAPI } from '@/lib/api/auth';
import { friendlyErrorMessage } from '@/lib/errorMessages';
import { useSessionStore } from '@/stores';
import { usePreferencesStore } from '@/stores/preferences';
import { TextField } from '@/components/v2/TextField';
import { SelectField } from '@/components/v2/SelectField';
import { V2Button } from '@/components/v2/V2Button';
import { authStyles } from '@/lib/styles/authStyles';
import { animationClasses } from '@/lib/animations';

export function AuthForm({ mode, nextPath }: { mode: 'login' | 'register', nextPath: string }) {
  const router = useRouter();
  const setSession = useSessionStore((state) => state.setSession);
  const setLanguage = usePreferencesStore((state) => state.setLanguage);

  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState<'id' | 'en'>('id');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isRegister = mode === 'register';

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
            safetyTermsAccepted: false,
            safetyTermsVersion: 'v1',
          })
        : await authAPI.login({ email, password });

      setSession(session);
      setLanguage(session.user.preferredLanguage === 'en' ? 'en' : preferredLanguage);
      router.replace(nextPath);
    } catch (err) {
      setError(friendlyErrorMessage(err, 'Belum berhasil masuk. Coba cek email dan password kamu.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className={authStyles.formContainer}>
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
          className={`${authStyles.fieldsWrapper} ${animationClasses.fieldGroupEnter}`}
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
        <div className={`${authStyles.errorAlert} ${animationClasses.softPop}`}>
          {error}
        </div>
      ) : null}

      <V2Button className={authStyles.submitButton} disabled={isSubmitting}>
        {isSubmitting ? 'Sebentar...' : isRegister ? 'Buat akun' : 'Masuk'}
      </V2Button>
    </form>
  );
}
