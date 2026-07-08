'use client';

import { useState } from 'react';
import { SafetyConsentSheet } from '@/components/v2/safety/SafetyConsentSheet';
import { profileAPI } from '@/lib/api/profile';
import { friendlyErrorMessage } from '@/lib/errorMessages';
import { useSessionStore } from '@/stores';
import { useUIStore } from '@/stores/ui';

export const SAFETY_TERMS_VERSION = 'companion-safety-v1';
const DISMISS_KEY = 'axis-safety-consent-dismissed';


export function SafetyConsentGate() {
  const userId = useSessionStore((state) => state.userId);
  const profile = useSessionStore((state) => state.profile);
  const setProfile = useSessionStore((state) => state.setProfile);
  const addToast = useUIStore((state) => state.addToast);

  const [isSaving, setIsSaving] = useState(false);
  const [dismissed, setDismissed] = useState(
    () => typeof window !== 'undefined' && sessionStorage.getItem(DISMISS_KEY) === '1'
  );

  const needsConsent = Boolean(userId && profile && !profile.safetyTermsAccepted);
  if (!needsConsent || dismissed) return null;

  const accept = async () => {
    if (!userId || !profile || isSaving) return;
    setIsSaving(true);
    try {
      const updated = await profileAPI.updateProfile(userId, {
        name: profile.name,
        language: profile.language,
        preferredLanguage: profile.language,
        preferredVoiceId: profile.preferredVoiceId,
        preferredTtsModel: profile.preferredTtsModel,
        safetyTermsAccepted: true,
        safetyTermsVersion: SAFETY_TERMS_VERSION,
      });
      setProfile(updated);
    } catch (error) {
      addToast(friendlyErrorMessage(error, 'Gagal menyimpan persetujuan, coba lagi ya.'), 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const later = () => {
    sessionStorage.setItem(DISMISS_KEY, '1');
    setDismissed(true);
  };

  return <SafetyConsentSheet isBusy={isSaving} onAccept={() => void accept()} onLater={later} />;
}
