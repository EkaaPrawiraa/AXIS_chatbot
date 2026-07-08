import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api/auth';
import { friendlyErrorMessage } from '@/lib/errorMessages';
import { useSessionStore } from '@/stores';
import { usePreferencesStore } from '@/stores/preferences';
import { GoogleSignInButton } from '@/components/v2/GoogleSignInButton';
import { authStyles } from '@/lib/styles/authStyles';
import { animationClasses } from '@/lib/animations';

export function SocialLogin({ nextPath }: { nextPath: string }) {
  const router = useRouter();
  const setSession = useSessionStore((state) => state.setSession);
  const setLanguage = usePreferencesStore((state) => state.setLanguage);

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleGoogleCredential = async (idToken: string) => {
    setError(null);
    setIsSubmitting(true);
    try {
      const session = await authAPI.googleLogin(idToken);
      setSession(session);
      setLanguage(session.user.preferredLanguage === 'en' ? 'en' : 'id');
      router.replace(nextPath);
    } catch (err) {
      setError(friendlyErrorMessage(err, 'Masuk dengan Google belum berhasil. Coba lagi ya.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className={authStyles.dividerWrapper}>
        <span className={authStyles.dividerLine} />
        atau
        <span className={authStyles.dividerLine} />
      </div>

      <div className="mt-5 flex flex-col items-center gap-3">
        {error ? (
          <div className={`${authStyles.errorAlert} ${animationClasses.softPop} w-full`}>
            {error}
          </div>
        ) : null}
        <GoogleSignInButton onCredential={handleGoogleCredential} disabled={isSubmitting} />
      </div>
    </>
  );
}
