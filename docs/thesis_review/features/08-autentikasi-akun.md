# Fitur 8: Autentikasi & Manajemen Akun

## Ringkasan
Satu-satunya fitur non-agentik dalam daftar ini — diimplementasikan penuh di Go (bukan Python), sebagai layanan terpisah (`backend/services/auth`) di belakang *gateway* (`backend/gateway`). Bertanggung jawab atas identitas pengguna, sesi, dan kendali data personal. Registrasi email/password (`POST /api/auth/register`) memakai bcrypt (`bcrypt.DefaultCost`) untuk hash kata sandi; login Google tidak menyimpan password sama sekali.

## Mekanisme token (`backend/shared/pkg/auth/jwt.go`)
- **Access token**: JWT HS256, klaim `sub` (user id), `iat`, `exp`, `jti` (id acak untuk daftar hitam). TTL 24 jam (`DefaultTTL`). Dibawa lewat header `Authorization: Bearer` atau cookie `axis_session` (HttpOnly).
- **Refresh token**: umur 30 hari, disimpan sebagai hash SHA-256 di tabel `refresh_tokens`, dirotasi setiap kali `/api/auth/refresh` dipanggil. Dibawa lewat cookie `axis_refresh`.
- **CSRF**: pola *double-submit* (`backend/shared/pkg/middleware/csrf.go`) — cookie `axis_csrf` (bisa dibaca JavaScript, tidak HttpOnly) harus dikirim ulang lewat header `X-CSRF-Token` pada permintaan yang mengubah state dan datang lewat cookie sesi (permintaan berbasis Bearer token dikecualikan). `initializeSession()` di frontend memakai keberadaan cookie `axis_csrf` sebagai gerbang untuk memutuskan apakah akan memanggil endpoint sesi sama sekali, sehingga kalau cookie ini hilang sementara `axis_session` masih valid, pengguna bisa terlihat ter-*logout* di frontend padahal sesi backend sebenarnya masih hidup.
- **Logout**: mencabut semua refresh token milik pengguna dan menambahkan `jti` access token ke tabel `token_blacklist`. **Tapi** middleware yang memverifikasi setiap permintaan (`backend/shared/pkg/middleware/auth.go`, dipasang sekali di *gateway*) hanya memeriksa tanda tangan dan `exp` JWT lewat `axisauth.Verify` — tidak pernah query ke `token_blacklist`. Jadi access token yang sudah "dicabut" lewat logout tetap diterima sebagai valid sampai TTL 24 jam-nya habis sendiri; yang benar-benar dicabut seketika hanyalah kemampuan refresh.
- **Komunikasi antar-layanan**: *gateway*/layanan Go ke layanan agentik Python diamankan lewat *shared secret* di header `X-Agentic-Private-Key`.

## Login Google OAuth
Endpoint `/api/auth/google` — verifikasi token Google lewat `backend/shared/pkg/googleauth/verify.go`, menolak token yang `email_verified`-nya `false`, lalu memetakan `sub` Google ke akun AXIS (kalau belum ada, akun baru dibuat tanpa `password_hash`). Kalau e-mail dari Google sudah terdaftar lewat jalur password, login Google ditolak dengan pesan untuk masuk pakai password.

## Rate limiting
Berbasis Redis (`backend/shared/pkg/middleware/ratelimit.go`): 30 giliran chat/jam dan 10 sesi/hari yang dipakai gateway (nilai persis dan batas lain seperti kuota pesan harian dicatat di Lampiran A laporan TA).

## Manajemen akun & data personal
- Profil (`GET/PUT /api/profile`, `backend/services/auth/internal/usecase/auth_usecase.go`): nama tampilan, bahasa preferensi, gender (`pria`/`wanita`, memengaruhi avatar dan personalisasi respons, lihat dokumen Fitur 1), suara *companion* pilihan, model TTS, dan gaya respons (`preferredResponseModel`: `gpt-5.4-nano` = "Ringkas", `gpt-5.5` = "Reflektif" — dipilih lewat `ResponseStyleSelector` di halaman profil).
- Selain itu ada preferensi "mode jawaban" (jawaban sekaligus vs bertahap/*stream*) di halaman pengaturan — ini murni state klien (`usePreferencesStore`), tidak dikirim atau disimpan di backend.
- Beberapa field `ProfileDTO` (`interactionStyle`, `reflectionPreference`, `companionTraits`) dikembalikan API tapi nilainya konstan hardcode di kode (`"empathetic"`, `"guided"`, `["supportive","calm"]`), bukan hasil input pengguna atau kalkulasi apa pun.
- Kendali data (semua diimplementasikan di frontend, `frontend_v2/components/v2/settings/`):
  - **Ekspor data**: tombol "Unduh data saya" (`PrivacyDataSection.tsx`) mengambil seluruh percakapan + pesan lewat API chat langsung dari browser dan merakitnya jadi file JSON yang diunduh klien — tidak ada endpoint ekspor di backend.
  - **Hapus riwayat**: tombol "Hapus riwayat percakapan" melakukan iterasi `DELETE /api/conversations/{id}` untuk tiap percakapan pengguna satu per satu (tidak ada endpoint *bulk delete* di layanan chat).
  - **Reset memori**: `DELETE /api/memories/kg/reset`.
  - **Hapus akun**: `POST /api/account/delete` (wajib isi ulang password) memicu *best-effort* `DELETE /api/memories/kg/purge-account` lebih dulu, lalu me-*revoke* semua refresh token dan soft-delete baris pengguna (email/nama dianonimkan, `account_status = 'deleted'`, `deleted_at` diisi — baris tidak benar-benar dihapus dari tabel `users`).
- Preferensi profil disimpan di Postgres dan dibaca balik oleh layanan agentik di awal setiap giliran (`_load_profile_context`, lihat dokumen Fitur 1) untuk personalisasi.

## Keterbatasan diketahui
- **Akun Google tidak bisa hapus akun sendiri**: alur hapus akun mewajibkan input password (`bcrypt.CompareHashAndPassword` di server, input password wajib diisi di `DeleteAccountSheet`), padahal akun yang dibuat lewat Google OAuth tidak pernah punya `password_hash`. Selama pengguna belum pernah set password manual, permintaan hapus akun mereka akan selalu gagal di langkah verifikasi password.
- **Logout tidak langsung mencabut akses**: `token_blacklist` diisi saat logout tapi tidak pernah dibaca oleh middleware otorisasi — access token lama tetap sah sampai kedaluwarsa (maks. 24 jam) meskipun pengguna sudah logout.
- Tidak ada verifikasi e-mail saat registrasi manual (hanya login Google yang mensyaratkan `email_verified`).
- Tidak ada alur lupa password / reset password lewat e-mail — tidak ditemukan endpoint maupun UI untuk ini.
- Ekspor data hanya menarik maksimum 50 percakapan pertama dan 200 pesan per percakapan (dibatasi di kode frontend), bukan ekspor lengkap tak terbatas.
- Audit kepatuhan privasi/PDP menyeluruh berada di luar cakupan tugas akhir ini.
