'use client';

import { AppShell } from '@/components/layout';
import { AuthRequired, useRequireAuthRedirect } from '@/components/session';
import { useProfile, useUpdateProfile } from '@/hooks';
import { usePreferencesStore, useSessionStore } from '@/stores';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useState, useEffect } from 'react';
import { LogOut, Play, Save, SlidersHorizontal } from 'lucide-react';
import { useT } from '@/lib/i18n';
import { voiceAPI } from '@/lib/api/voice';
import { authAPI } from '@/lib/api/auth';
import { createAudioPlayer } from '@/lib/audio';
import { VoiceOption } from '@/models';
import { useRouter } from 'next/navigation';

export default function ProfilePage() {
  const t = useT();
  const { isInitialized, isAuthenticated } = useRequireAuthRedirect();
  const userId = useSessionStore((state) => state.userId);
  const setProfile = useSessionStore((state) => state.setProfile);
  const user = useSessionStore((state) => state.user);
  const clearSession = useSessionStore((state) => state.clearSession);
  const appLanguage = usePreferencesStore((state) => state.language);
  const router = useRouter();
  const activeUserId = isAuthenticated ? userId : null;
  const { data: profile, isLoading } = useProfile(activeUserId);
  const updateProfile = useUpdateProfile();
  const [formData, setFormData] = useState({
    name: '',
    language: 'id',
    preferredVoiceId: '',
    preferredTtsModel: 'v2_5_turbo',
    preferredResponseModel: 'gpt-5.4-nano',
  });
  const [voiceOptions, setVoiceOptions] = useState<VoiceOption[]>([]);
  const [isLoadingVoices, setIsLoadingVoices] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  useEffect(() => {
    if (profile) {
      setFormData({
        name: profile.name || '',
        language: profile.language || 'id',
        preferredVoiceId: profile.preferredVoiceId || '',
        preferredTtsModel: profile.preferredTtsModel || 'v2_5_turbo',
        preferredResponseModel: profile.preferredResponseModel || 'gpt-5.4-nano',
      });
    }
  }, [profile]);

  useEffect(() => {
    let active = true;
    setIsLoadingVoices(true);
    voiceAPI
      .listOptions()
      .then((voices) => {
        if (active) setVoiceOptions(voices);
      })
      .catch(() => {
        if (active) setVoiceOptions([]);
      })
      .finally(() => {
        if (active) setIsLoadingVoices(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const formatDate = (value?: string | number) => {
    if (!value) return '-';
    return new Date(value).toLocaleString(appLanguage === 'en' ? 'en-US' : 'id-ID', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  const handleSave = async () => {
    if (userId) {
      const updated = await updateProfile.mutateAsync({
        userId,
        request: {
          name: formData.name,
          language: formData.language,
          preferredLanguage: formData.language,
          preferredVoiceId: formData.preferredVoiceId,
          preferredTtsModel: formData.preferredTtsModel,
          preferredResponseModel: formData.preferredResponseModel,
        },
      });
      setProfile(updated);
      setSavedMessage(t('profileUpdated'));
      setTimeout(() => setSavedMessage(null), 2500);
    }
  };

  const handleLogout = async () => {
    try {
      await authAPI.logout();
    } catch {
      // abaikan kegagalan jaringan; tetap bersihkan sesi lokal
    }
    clearSession();
    router.push('/auth');
  };

  const selectedVoice = voiceOptions.find((voice) => voice.id === formData.preferredVoiceId);

  if (isInitialized && !isAuthenticated) {
    return null;
  }

  if (!userId) {
    return (
      <AppShell>
        <AuthRequired
          title={t('authProfileTitle')}
          description={t('authProfileDescription')}
        />
      </AppShell>
    );
  }

  if (isLoading) {
    return (
      <AppShell>
        <div className="axis-page-narrow">
          <div className="space-y-4">
            <div className="h-8 w-56 animate-pulse rounded bg-muted" />
            <div className="h-28 animate-pulse rounded-xl bg-muted" />
            <div className="h-48 animate-pulse rounded-xl bg-muted" />
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="axis-page-narrow">
        <div className="mb-8 border-b border-border pb-8">
          {/* <div className="axis-eyebrow mb-4">
            <SlidersHorizontal className="size-4 text-primary" />
            {t('companionPreferences')}
          </div> */}
          <h1 className="axis-title mb-2">{t('editProfile')}</h1>
          <p className="axis-description">
            {t('editProfileDescription')}
          </p>
        </div>

        <div className="space-y-5">
          <Card className="p-6">
            <h2 className="mb-5 text-2xl font-semibold tracking-[-0.035em]">{t('editableProfile')}</h2>
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">{t('displayName')}</Label>
                <Input
                  id="name"
                  value={formData.name || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={t('displayNamePlaceholder')}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="language">{t('preferredLanguage')}</Label>
                <select
                  id="language"
                  value={formData.language || 'id'}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                  className="axis-field-select mt-1"
                >
                  <option value="id">{t('indonesian')}</option>
                  <option value="en">{t('english')}</option>
                </select>
              </div>
              <div>
                <Label htmlFor="preferredVoiceId">{t('preferredVoice')}</Label>
                <div className="mt-1 flex gap-2">
                  <select
                    id="preferredVoiceId"
                    value={formData.preferredVoiceId}
                    onChange={(e) => setFormData({ ...formData, preferredVoiceId: e.target.value })}
                    className="axis-field-select min-w-0 flex-1"
                    disabled={isLoadingVoices}
                  >
                    <option value="">{isLoadingVoices ? t('loadingVoices') : t('defaultVoice')}</option>
                    {voiceOptions.map((voice) => (
                      <option key={voice.id} value={voice.id}>
                        {voice.name}
                      </option>
                    ))}
                  </select>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    disabled={!selectedVoice?.previewUrl}
                    onClick={() => {
                      if (selectedVoice?.previewUrl) void createAudioPlayer(selectedVoice.previewUrl).done;
                    }}
                    title={t('playVoiceSample')}
                  >
                    <Play className="h-4 w-4" />
                  </Button>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{t('preferredVoiceHelp')}</p>
              </div>
              <div>
                <Label htmlFor="preferredTtsModel">{t('voiceQuality')}</Label>
                <select
                  id="preferredTtsModel"
                  value={formData.preferredTtsModel}
                  onChange={(e) => setFormData({ ...formData, preferredTtsModel: e.target.value })}
                  className="axis-field-select mt-1"
                >
                  <option value="v2_5_turbo">{t('voiceFast')}</option>
                  <option value="v3">{t('voiceExpressive')}</option>
                  <option value="openai_tts1">{t('openaiTtsFallback')}</option>
                </select>
              </div>
              <div>
                <Label htmlFor="preferredResponseModel">{t('responseModelPreference')}</Label>
                <select
                  id="preferredResponseModel"
                  value={formData.preferredResponseModel}
                  onChange={(e) => setFormData({ ...formData, preferredResponseModel: e.target.value })}
                  className="axis-field-select mt-1"
                >
                  <option value="gpt-5.4-nano">{t('responseFastShort')}</option>
                  <option value="gpt-5.5">{t('responseDeepMeaningful')}</option>
                </select>
                <p className="mt-1 text-xs text-muted-foreground">{t('responseModelPreferenceHelp')}</p>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="mb-5 text-2xl font-semibold tracking-[-0.035em]">{t('accountMetadata')}</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label>{t('userIdLabel')}</Label>
                <Input value={profile?.userId || userId || ''} disabled className="mt-1 font-mono text-xs" />
              </div>
              <div>
                <Label>{t('emailLabel')}</Label>
                <Input value={user?.email || ''} disabled className="mt-1" />
              </div>
              {/* <div>
                <Label>{t('profileDefaults')}</Label>
                <Input
                  value={`${profile?.interactionStyle || 'empathetic'} / ${profile?.reflectionPreference || 'guided'}`}
                  disabled
                  className="mt-1"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  {t('profileDefaultsHelp')}
                </p>
              </div> */}
              <div>
                <Label>{t('createdAt')}</Label>
                <Input value={formatDate(user?.createdAt || profile?.createdAt)} disabled className="mt-1" />
              </div>
              <div>
                <Label>{t('updatedAt')}</Label>
                <Input value={formatDate(user?.updatedAt || profile?.updatedAt)} disabled className="mt-1" />
              </div>
            </div>
          </Card>

          <div className="flex flex-col items-stretch justify-end gap-3 sm:flex-row sm:items-center">
            <Button type="button" variant="outline" onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              {t('logout')}
            </Button>
            {savedMessage && <p className="text-sm text-muted-foreground">{savedMessage}</p>}
            <Button
              onClick={handleSave}
              disabled={updateProfile.isPending}
            >
              <Save className="mr-2 h-4 w-4" />
              {updateProfile.isPending ? t('saving') : t('saveChanges')}
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
