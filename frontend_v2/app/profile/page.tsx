'use client';

import Image from 'next/image';
import {
  Check,
  ChevronRight,
  Copy,
  Globe,
  Leaf,
  Loader2,
  LogOut,
  Mail,
  Mic,
  Pencil,
  Play,
  Settings,
  ShieldCheck,
  Sprout,
  Volume2,
  X,
} from '@/lib/assets';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AuthRequired } from '@/components/session';
import { MobileAppHeader } from '@/components/v2/MobileAppHeader';
import { V2Shell } from '@/components/v2/V2Shell';
import { ProfileRow } from '@/components/v2/profile/ProfileRow';
import { authAPI } from '@/lib/api/auth';
import { avatarSrcForUser } from '@/lib/avatar';
import { profileAPI } from '@/lib/api/profile';
import { voiceAPI } from '@/lib/api/voice';
import { animationClasses } from '@/lib/animations';
import { createAudioPlayer, dataUrlFromBase64, primeAudioElement } from '@/lib/audio';
import { friendlyErrorMessage } from '@/lib/errorMessages';
import { useSessionStore } from '@/stores';
import { useUIStore } from '@/stores/ui';

// "Suara Percakapan" (TTS_MODELS) and "Karakter Suara pilihan"
// (VOICE_CHARACTERS) are deliberately two INDEPENDENT axes: Gemini's API
// lets you pair any of its ~30 prebuilt voice names with any of its 3 TTS
// models, so which tier is used (latency/quality) and which voice
// character is used are orthogonal choices, not one derived from the
// other.
type CharacterId = 'hangat' | 'tenang' | 'ceria' | 'perangkat';

const TTS_MODELS: Array<{ id: string; name: string; helper: string }> = [
  { id: 'gemini-3.1-flash-tts', name: 'AXIS Cepat', helper: 'Respons suara paling gesit' },
  { id: 'gemini-2.5-pro-tts', name: 'AXIS Natural', helper: 'Suara lebih alami dan nyaman didengar' },
  { id: 'gemini-2.5-flash-tts', name: 'AXIS Klasik', helper: 'Mesin suara alternatif' },
];

const VOICE_CHARACTERS: Array<{ id: CharacterId; name: string; helper: string }> = [
  { id: 'hangat', name: 'Suara Hangat', helper: 'Suara lembut dan menenangkan' },
  { id: 'tenang', name: 'Suara Tenang', helper: 'Suara kalem dan stabil' },
  { id: 'ceria', name: 'Suara Ceria', helper: 'Suara ringan dan bersemangat' },
  { id: 'perangkat', name: 'Suara Perangkat', helper: 'Suara asisten yang netral' },
];

// Real Gemini prebuilt voice name per character x gender. voice_id is
// sent to the backend as-is, which uses it as the literal Gemini voice
// name once it doesn't match any catalog persona id (see
// VoiceCatalog.get()'s "unknown voice_id" fallback path in agentic).
// Puck/Fenrir/Aoede/Enceladus/Leda/Charon are listening-tested pairs
// (Google AI Studio); Sulafat/Achird for "Hangat" are picked from
// Gemini's own official character descriptors ("Warm"/"Friendly") since
// Google doesn't publish voice gender and these two haven't been
// listening-verified yet — worth confirming by ear and swapping if
// either sounds off.
const VOICE_CHARACTER_MAP: Record<CharacterId, { female: string; male: string }> = {
  hangat: { female: 'Sulafat', male: 'Achird' },
  tenang: { female: 'Aoede', male: 'Enceladus' },
  ceria: { female: 'Puck', male: 'Fenrir' },
  perangkat: { female: 'Leda', male: 'Charon' },
};

const STYLES: Array<{ id: string; label: string; helper: string; Icon: typeof Leaf }> = [
  { id: 'gpt-5.4-nano', label: 'Ringkas', helper: 'Jawaban singkat, padat, dan langsung ke inti.', Icon: Leaf },
  { id: 'gpt-5.5', label: 'Lebih reflektif', helper: 'Jawaban mendalam, penuh empati dan pertanyaan reflektif.', Icon: Sprout },
];

export default function ProfilePage() {
  return (
    <AuthRequired>
      <ProfileContent />
    </AuthRequired>
  );
}

function ProfileContent() {
  const router = useRouter();
  const userId = useSessionStore((state) => state.userId);
  const user = useSessionStore((state) => state.user);
  const profile = useSessionStore((state) => state.profile);
  const setProfile = useSessionStore((state) => state.setProfile);
  const clearSession = useSessionStore((state) => state.clearSession);
  const addToast = useUIStore((state) => state.addToast);

  const [name, setName] = useState(profile?.name || user?.displayName || '');
  const [isEditingName, setIsEditingName] = useState(false);
  const [language, setLanguage] = useState((profile?.language || user?.preferredLanguage || 'id') === 'en' ? 'en' : 'id');
  const [voice, setVoice] = useState(profile?.preferredVoiceId || user?.preferredVoiceId || 'alloy');
  const [responseModel, setResponseModel] = useState(profile?.preferredResponseModel || user?.preferredResponseModel || 'gpt-5.4-nano');
  const [voiceSheetOpen, setVoiceSheetOpen] = useState(false);
  const [ttsSheetOpen, setTtsSheetOpen] = useState(false);
  const [ttsModel, setTtsModel] = useState(profile?.preferredTtsModel || user?.preferredTtsModel || 'v2_5_turbo');
  const [gender, setGender] = useState((profile?.gender || user?.gender || 'pria') === 'wanita' ? 'wanita' : 'pria');
  const [savedField, setSavedField] = useState<string | null>(null);
  const [showSavedBanner, setShowSavedBanner] = useState(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);

  const persist = async (
    patch: Partial<{ name: string; language: string; voice: string; responseModel: string; ttsModel: string; gender: string }>,
    field: string
  ) => {
    if (!userId) return;
    try {
      const next = await profileAPI.updateProfile(userId, {
        name: patch.name ?? name,
        language: patch.language ?? language,
        preferredLanguage: patch.language ?? language,
        preferredVoiceId: patch.voice ?? voice,
        preferredResponseModel: patch.responseModel ?? responseModel,
        preferredTtsModel: patch.ttsModel ?? ttsModel,
        gender: patch.gender ?? gender,
      });
      setProfile(next);
      setSavedField(field);
      setShowSavedBanner(true);
      window.setTimeout(() => setSavedField((current) => (current === field ? null : current)), 2200);
    } catch (error) {
      setSavedField(null);
      addToast(friendlyErrorMessage(error, 'Gagal menyimpan perubahan, coba lagi ya.'), 'error');
    }
  };

  // Only picks the tier/model (latency vs quality) -- independent of
  // which voice character is speaking; see VOICE_CHARACTER_MAP above.
  const chooseTts = (id: string) => {
    setTtsModel(id);
    setTtsSheetOpen(false);
    void persist({ ttsModel: id }, 'tts');
  };

  const copyUserId = async () => {
    if (!userId) return;
    await navigator.clipboard.writeText(userId).catch(() => undefined);
    setSavedField('userid');
    window.setTimeout(() => setSavedField((current) => (current === 'userid' ? null : current)), 1500);
  };

  const formatDate = (value?: string | number) => {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '-';
    return `${date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}, ${date
      .toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
      .replace(':', '.')}`;
  };

  const commitName = () => {
    setIsEditingName(false);
    if (name.trim()) void persist({ name: name.trim() }, 'name');
  };

  const toggleLanguage = () => {
    const next = language === 'id' ? 'en' : 'id';
    setLanguage(next);
    void persist({ language: next }, 'language');
  };

  // Resolves character + the shared gender preference to a real Gemini
  // voice name and saves it as voice_id (see VOICE_CHARACTER_MAP above).
  const chooseVoiceCharacter = (id: CharacterId) => {
    const resolved = VOICE_CHARACTER_MAP[id][gender === 'wanita' ? 'female' : 'male'];
    setVoice(resolved);
    setVoiceSheetOpen(false);
    void persist({ voice: resolved }, 'voice');
  };

  // Changing gender from inside the voice sheet keeps whichever character
  // is currently active and re-resolves it to that gender's voice name.
  const chooseVoiceGender = (id: 'pria' | 'wanita') => {
    setGender(id);
    const character = activeCharacter || 'hangat';
    const resolved = VOICE_CHARACTER_MAP[character][id === 'wanita' ? 'female' : 'male'];
    setVoice(resolved);
    void persist({ gender: id, voice: resolved }, 'voice');
  };

  const chooseStyle = (id: string) => {
    setResponseModel(id);
    void persist({ responseModel: id }, 'style');
  };

  const chooseGenderPreference = (id: 'pria' | 'wanita') => {
    setGender(id);
    void persist({ gender: id }, 'gender');
  };

  // Calls the real /voice/synthesize endpoint with the currently saved
  // voice + tts model, instead of the browser's own generic TTS — a
  // browser voice previewing "Suara Ceria" sounds nothing like what AXIS
  // actually says in a real conversation, which was actively misleading.
  const previewVoice = async (event: React.MouseEvent) => {
    event.stopPropagation();
    // Primed synchronously, still inside this click, before the
    // synthesize() fetch below breaks the gesture chain — see
    // primeAudioElement's own comment in lib/audio.
    const audioElement = primeAudioElement();
    setIsPreviewLoading(true);
    try {
      const result = await voiceAPI.synthesize({
        text:
          language === 'en'
            ? "Hi, I'm AXIS. I'm here to listen."
            : 'Hai, aku AXIS. Aku di sini siap dengerin kamu.',
        voice_id: voice,
        tts_model: ttsModel as any,
        language_pref: language,
      });
      if (!result.audio_output_base64) throw new Error('no audio returned');
      const src = dataUrlFromBase64(result.audio_output_base64, result.audio_output_format);
      await createAudioPlayer(src, undefined, audioElement).done;
    } catch (error) {
      console.warn('Profile: voice preview failed', error);
      addToast('Contoh suara gagal diputar, coba lagi ya.', 'error');
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const logout = async () => {
    await authAPI.logout().catch(() => undefined);
    clearSession();
    router.replace('/auth');
  };

  // Reverse-lookup: which character (if any) resolves to the currently
  // saved voice_id for the currently saved gender. No separate "character"
  // field exists server-side -- only the resolved voice name is persisted
  // (preferredVoiceId) -- so this is how the sheet knows which option to
  // highlight and what to fall back to as "hangat" if the saved voice_id
  // doesn't match any known pair (e.g. an old alloy/verse/aria/local value).
  const activeCharacter =
    (Object.keys(VOICE_CHARACTER_MAP) as CharacterId[]).find(
      (id) => VOICE_CHARACTER_MAP[id][gender === 'wanita' ? 'female' : 'male'] === voice
    ) || null;
  const activeVoice = VOICE_CHARACTERS.find((item) => item.id === activeCharacter) || VOICE_CHARACTERS[0];

  return (
    <V2Shell showTopbar={false}>
      <main className="space-y-2 pb-6">
        <MobileAppHeader />

        <div>
          <h1 className="text-[24px] font-bold leading-tight text-[var(--v2-ink)]">Profil</h1>
          <p className="mt-0.5 text-[12.5px] font-medium text-[var(--v2-muted)]">
            Kelola informasi dan preferensi kamu.
          </p>
        </div>

        {showSavedBanner ? (
          <div className="flex items-center justify-between rounded-[16px] border border-[#e3dbc8] bg-[#f7f3e8] px-3.5 py-2.5">
            <span className="flex items-center gap-2.5 text-[14px] font-bold text-[var(--v2-ink)]">
              <span className="grid h-[24px] w-[24px] place-items-center rounded-full bg-[#616f51] text-white">
                <Check className="h-[14px] w-[14px]" strokeWidth={3} />
              </span>
              Perubahan tersimpan
            </span>
            <button onClick={() => setShowSavedBanner(false)} aria-label="Tutup" className="v2-anim-pressable text-[var(--v2-ink)]">
              <X className="h-[18px] w-[18px]" />
            </button>
          </div>
        ) : null}

        <section className="flex items-center gap-3.5 rounded-[20px] bg-[#f6efe3] p-3">
          <div className="relative shrink-0">
            <Image
              src={avatarSrcForUser(user?.id ?? profile?.userId)}
              alt="Avatar"
              width={93}
              height={93}
              unoptimized
              className="h-[68px] w-[68px] rounded-full object-cover"
            />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-bold text-[#6b7355]">Nama tampilan</p>
            {isEditingName ? (
              <input
                autoFocus
                value={name}
                onChange={(event) => setName(event.target.value)}
                onBlur={commitName}
                onKeyDown={(event) => event.key === 'Enter' && commitName()}
                className="mt-0.5 w-full rounded-[10px] border border-[#ddd3bd] bg-white/70 px-2 py-1 text-[20px] font-bold text-[var(--v2-ink)] outline-none"
              />
            ) : (
              <button onClick={() => setIsEditingName(true)} className="v2-anim-pressable flex items-center gap-2.5">
                <span className="text-[19px] font-bold leading-tight text-[var(--v2-ink)]">{name || 'Tanpa nama'}</span>
                <Pencil className="h-[16px] w-[16px] text-[#6b7355]" />
                {savedField === 'name' ? <Check className="h-[15px] w-[15px] text-[#5f9e54]" /> : null}
              </button>
            )}
            <p className="mt-0.5 text-[11.5px] font-medium leading-snug text-[#8a8477]">
              Ini adalah nama yang akan ditampilkan di AXIS.
            </p>
          </div>
        </section>

        <ProfileRow
          Icon={Mail}
          label="Email"
          value={user?.email || '-'}
          helper="Akun terverifikasi"
          accessory={<ChevronRight className="h-[19px] w-[19px] text-[#8a8477]" />}
          onClick={() => router.push('/settings')}
        />

        {/* <div className="rounded-[20px] bg-[#f6efe3] px-3.5 py-2.5">
          <p className="text-[12.5px] font-bold text-[#6b7355]">Jenis kelamin</p>
          <p className="text-[11.5px] font-medium leading-snug text-[#8a8477]">
            Dipakai untuk menyesuaikan sapaan AXIS ke kamu.
          </p>
          <div className="mt-2 grid grid-cols-2 gap-2 rounded-[14px] bg-[#efe6d4] p-1">
            {(['wanita', 'pria'] as const).map((id) => (
              <button
                key={id}
                onClick={() => chooseGenderPreference(id)}
                className={`v2-anim-pressable rounded-[11px] py-2 text-[13.5px] font-bold capitalize ${
                  gender === id ? 'bg-white text-[var(--v2-ink)] shadow' : 'text-[#8a8477]'
                }`}
              >
                {id}
              </button>
            ))}
          </div>
        </div> */}

        <ProfileRow
          Icon={Globe}
          label="Bahasa"
          value={language === 'en' ? 'English' : 'Bahasa Indonesia'}
          helper={savedField === 'language' ? 'Tersimpan ✓' : 'Bahasa yang kamu gunakan di AXIS untuk percakapan'}
          accessory={<ChevronRight className="h-[19px] w-[19px] text-[#8a8477]" />}
          onClick={toggleLanguage}
        />

        <ProfileRow
          Icon={Mic}
          label="Karakter Suara pilihan"
          value={activeVoice.name}
          helper={savedField === 'voice' ? 'Tersimpan ✓' : activeVoice.helper}
          accessory={
            isPreviewLoading ? (
              <span className="flex h-[42px] items-center gap-2 rounded-full bg-[#adb694] px-4 text-[13.5px] font-bold text-white">
                <Loader2 className="h-[15px] w-[15px] animate-spin" /> 
              </span>
            ) : (
              <button
                onClick={previewVoice}
                aria-label="Putar contoh suara"
                className="v2-anim-pressable grid h-[42px] w-[42px] place-items-center rounded-full bg-[#efe6d4] text-[#5c6549]"
              >
                <Play className="h-[17px] w-[17px]" fill="currentColor" />
              </button>
            )
          }
          onClick={() => setVoiceSheetOpen(true)}
        />

        <section className="rounded-[20px] bg-[#f6efe3] p-3">
          <p className="flex items-center gap-1.5 text-[14.5px] font-bold text-[var(--v2-ink)]">
            <span aria-hidden>✨</span> Gaya respons
          </p>
          <p className="mt-0.5 text-[12.5px] font-medium text-[#8a8477]">
            Pilih gaya respons yang paling cocok untukmu.
          </p>
          <div className="mt-2.5 grid grid-cols-2 gap-2.5">
            {STYLES.map((style) => {
              const active = responseModel === style.id;
              return (
                <button
                  key={style.id}
                  onClick={() => chooseStyle(style.id)}
                  className={`v2-anim-pressable relative rounded-[16px] border p-2.5 text-left ${
                    active ? 'border-[1.5px] border-[var(--v2-olive)] bg-[#f2eee0]' : 'border-[#e7dfcc] bg-[#f4eee0]'
                  }`}
                >
                  {active ? (
                    <span className="absolute right-2.5 top-2.5 grid h-[22px] w-[22px] place-items-center rounded-full bg-[var(--v2-olive)] text-white">
                      <Check className="h-[13px] w-[13px]" strokeWidth={3} />
                    </span>
                  ) : null}
                  <style.Icon className="h-[22px] w-[22px] text-[#5c7345]" />
                  <p className="mt-1.5 text-[14px] font-bold text-[var(--v2-ink)]">{style.label}</p>
                  <p className="mt-0.5 text-[11px] font-medium leading-snug text-[#8a8477]">{style.helper}</p>
                </button>
              );
            })}
          </div>
        </section>

        <div className="pt-1">
          <p className="flex items-center gap-2 text-[15px] font-bold text-[var(--v2-ink)]">
            <Settings className="h-[17px] w-[17px]" /> Preferensi lanjutan
          </p>
          <p className="mt-0.5 text-[12px] font-medium text-[#8a8477]">Atur pengalaman AXIS sesuai kebutuhanmu.</p>
        </div>

        <ProfileRow
          Icon={Volume2}
          label="Suara Percakapan"
          value={(TTS_MODELS.find((item) => item.id === ttsModel) || TTS_MODELS[0]).name}
          helper={savedField === 'tts' ? 'Tersimpan ✓' : (TTS_MODELS.find((item) => item.id === ttsModel) || TTS_MODELS[0]).helper}
          accessory={<ChevronRight className="h-[19px] w-[19px] text-[#8a8477]" />}
          onClick={() => setTtsSheetOpen(true)}
        />

        <section className="rounded-[20px] bg-[#f6efe3] p-3.5">
          <p className="flex items-center gap-2.5 text-[14.5px] font-bold text-[var(--v2-ink)]">
            <ShieldCheck className="h-[19px] w-[19px] text-[#5c6549]" /> Informasi akun
          </p>
          <dl className="mt-2.5 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <dt className="text-[12.5px] font-medium text-[#6f6a5e]">User ID</dt>
              <dd className="flex min-w-0 items-center gap-2">
                <span className="truncate font-mono text-[11.5px] font-bold uppercase text-[var(--v2-ink)]">
                  {(userId || '-').slice(0, 18)}…
                </span>
                <button onClick={copyUserId} aria-label="Salin User ID" className="v2-anim-pressable text-[var(--v2-ink)]">
                  {savedField === 'userid' ? <Check className="h-[14px] w-[14px] text-[#5f9e54]" /> : <Copy className="h-[14px] w-[14px]" />}
                </button>
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-[12.5px] font-medium text-[#6f6a5e]">Dibuat pada</dt>
              <dd className="text-[12.5px] font-bold text-[var(--v2-ink)]">{formatDate(user?.createdAt)}</dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-[12.5px] font-medium text-[#6f6a5e]">Diperbarui</dt>
              <dd className="text-[12.5px] font-bold text-[var(--v2-ink)]">{formatDate(user?.updatedAt)}</dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-[12.5px] font-medium text-[#6f6a5e]">Akun terverifikasi</dt>
              <dd className="flex items-center gap-1.5 text-[12.5px] font-bold text-[var(--v2-ink)]">
                <span className="grid h-[17px] w-[17px] place-items-center rounded-full bg-[#5c8a4e] text-white">
                  <Check className="h-[10px] w-[10px]" strokeWidth={3.4} />
                </span>
                {user?.safetyTermsAccepted ? 'Terverifikasi' : 'Belum'}
              </dd>
            </div>
          </dl>
        </section>

        <button
          onClick={logout}
          className="v2-anim-pressable flex w-full items-center gap-3.5 rounded-[20px] bg-[#f7e5da] px-3.5 py-2.5 text-left"
        >
          <span className="grid h-[44px] w-[44px] shrink-0 place-items-center rounded-full bg-[#f2d8c8] text-[#a34a28]">
            <LogOut className="h-[22px] w-[22px]" />
          </span>
          <span>
            <span className="block text-[16px] font-bold text-[#a34a28]">Keluar dari akun</span>
            <span className="block text-[12.5px] font-medium text-[#8a8477]">
              Kamu akan keluar dari AXIS di perangkat ini.
            </span>
          </span>
        </button>

        {voiceSheetOpen ? (
          <div className={`fixed inset-0 z-[80] bg-black/35 ${animationClasses.sheetBackdropIn}`} onClick={() => setVoiceSheetOpen(false)}>
            <aside
              onClick={(event) => event.stopPropagation()}
              className={`absolute inset-x-0 bottom-0 mx-auto w-[min(100%,540px)] rounded-t-[26px] bg-[#f7f1e8] p-5 shadow-2xl ${animationClasses.sheetUp}`}
            >
              <h2 className="text-[19px] font-bold text-[var(--v2-ink)]">Pilih karakter suara</h2>

              <p className="mt-3 text-[12px] font-bold text-[#6b7355]">Suara wanita atau pria</p>
              <div className="mt-1.5 grid grid-cols-2 gap-2 rounded-[14px] bg-[#efe6d4] p-1">
                {(['wanita', 'pria'] as const).map((id) => (
                  <button
                    key={id}
                    onClick={() => chooseVoiceGender(id)}
                    className={`v2-anim-pressable rounded-[11px] py-2 text-[13.5px] font-bold capitalize ${
                      gender === id ? 'bg-white text-[var(--v2-ink)] shadow' : 'text-[#8a8477]'
                    }`}
                  >
                    {id}
                  </button>
                ))}
              </div>

              <div className="mt-3 space-y-2">
                {VOICE_CHARACTERS.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => chooseVoiceCharacter(item.id)}
                    className={`flex w-full items-center justify-between rounded-[16px] border px-4 py-3 text-left ${
                      activeCharacter === item.id ? 'border-[var(--v2-olive)] bg-[#f0eee0]' : 'border-[#e7dfcc] bg-[#fbf7ee]'
                    }`}
                  >
                    <span>
                      <span className="block text-[14.5px] font-bold text-[var(--v2-ink)]">{item.name}</span>
                      <span className="block text-[12px] font-medium text-[#8a8477]">{item.helper}</span>
                    </span>
                    {activeCharacter === item.id ? <Check className="h-[17px] w-[17px] text-[var(--v2-olive)]" /> : null}
                  </button>
                ))}
              </div>
            </aside>
          </div>
        ) : null}

        {ttsSheetOpen ? (
          <div className={`fixed inset-0 z-[80] bg-black/35 ${animationClasses.sheetBackdropIn}`} onClick={() => setTtsSheetOpen(false)}>
            <aside
              onClick={(event) => event.stopPropagation()}
              className={`absolute inset-x-0 bottom-0 mx-auto w-[min(100%,540px)] rounded-t-[26px] bg-[#f7f1e8] p-5 shadow-2xl ${animationClasses.sheetUp}`}
            >
              <h2 className="text-[19px] font-bold text-[var(--v2-ink)]">Pilih mesin suara</h2>
              <p className="mt-0.5 text-[12px] font-medium text-[#8a8477]">
                Menentukan kecepatan dan kualitas respons suara AXIS.
              </p>

              <div className="mt-3 space-y-2">
                {TTS_MODELS.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => chooseTts(item.id)}
                    className={`flex w-full items-center justify-between rounded-[16px] border px-4 py-3 text-left ${
                      ttsModel === item.id ? 'border-[var(--v2-olive)] bg-[#f0eee0]' : 'border-[#e7dfcc] bg-[#fbf7ee]'
                    }`}
                  >
                    <span>
                      <span className="block text-[14.5px] font-bold text-[var(--v2-ink)]">{item.name}</span>
                      <span className="block text-[12px] font-medium text-[#8a8477]">{item.helper}</span>
                    </span>
                    {ttsModel === item.id ? <Check className="h-[17px] w-[17px] text-[var(--v2-olive)]" /> : null}
                  </button>
                ))}
              </div>
            </aside>
          </div>
        ) : null}
      </main>
    </V2Shell>
  );
}
