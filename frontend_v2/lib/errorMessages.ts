
const KNOWN_MESSAGES: Record<string, string> = {
  'invalid email or password': 'Email atau password salah.',
  'invalid password': 'Password yang kamu masukkan salah.',
  'email is already registered': 'Email ini sudah terdaftar. Coba masuk, ya.',
  unauthorized: 'Sesi kamu sudah berakhir. Silakan masuk lagi.',
  'daily_message_limit_reached': 'Kamu sudah mencapai batas pesan harian untuk riset TA ini. Coba lagi besok ya.',
};

const STATUS_FALLBACKS: Record<number, string> = {
  400: 'Permintaan tidak valid. Coba periksa kembali isiannya.',
  401: 'Sesi kamu sudah berakhir. Silakan masuk lagi.',
  403: 'Kamu tidak punya akses untuk melakukan ini.',
  404: 'Data yang kamu cari tidak ditemukan.',
  409: 'Data ini sudah ada sebelumnya.',
  429: 'Terlalu banyak permintaan dalam waktu singkat. Coba lagi sebentar lagi.',
};


export function friendlyErrorMessage(error: unknown, fallback = 'Terjadi gangguan. Coba lagi ya.'): string {
  const response = (error as { response?: { status?: number; data?: unknown }; isAxiosError?: boolean })?.response;
  const isAxiosError = Boolean((error as { isAxiosError?: boolean })?.isAxiosError);

  if (!isAxiosError && !response) {
    if (error instanceof Error && error.message && !/request failed|network error/i.test(error.message)) {
      return error.message;
    }
    return fallback;
  }

  const data = response?.data as { error?: string; message?: string } | undefined;
  const backendText = (data?.error || data?.message || '').toLowerCase().trim();
  if (backendText && KNOWN_MESSAGES[backendText]) {
    return KNOWN_MESSAGES[backendText];
  }

  if (response?.status && STATUS_FALLBACKS[response.status]) {
    return STATUS_FALLBACKS[response.status];
  }

  if (!response) {
    return 'Koneksi bermasalah. Periksa jaringan kamu dan coba lagi.';
  }

  return fallback;
}
