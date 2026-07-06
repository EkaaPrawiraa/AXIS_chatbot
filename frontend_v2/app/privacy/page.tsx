import type { Metadata } from 'next';
import { LegalPageShell } from '@/components/v2/LegalPageShell';

export const metadata: Metadata = {
  title: 'Kebijakan Privasi — AXIS',
  description: 'Bagaimana AXIS mengumpulkan, menggunakan, dan melindungi data kamu.',
};

export default function PrivacyPage() {
  return (
    <LegalPageShell title="Kebijakan Privasi" lastUpdated="6 Juli 2026">
      <section>
        <p>
          AXIS adalah teman refleksi harian berbasis AI untuk mahasiswa Indonesia. Kebijakan ini
          menjelaskan data apa saja yang kami kumpulkan, bagaimana data itu dipakai, dan hak kamu
          atas data tersebut. Dengan menggunakan AXIS, kamu menyetujui kebijakan ini.
        </p>
      </section>

      <section>
        <h2>Data yang kami kumpulkan</h2>
        <ul>
          <li>Data akun: email, nama tampilan, dan kata sandi (disimpan terenkripsi).</li>
          <li>
            Isi percakapan kamu dengan AXIS, termasuk pesan teks dan (jika kamu memakainya) rekaman
            suara yang diubah jadi teks.
          </li>
          <li>
            Hasil skrining mood/PHQ-9 yang kamu isi secara sukarela di dalam aplikasi.
          </li>
          <li>
            Memori jangka panjang yang disimpulkan dari percakapanmu (mis. orang-orang penting,
            pola pikir, pemicu stres) agar AXIS bisa merespons secara personal dari waktu ke waktu.
          </li>
        </ul>
      </section>

      <section>
        <h2>Bagaimana data dipakai</h2>
        <p>
          Data di atas dipakai untuk menjalankan dan mempersonalisasi percakapan, mengingat konteks
          antar sesi, dan menghitung skor skrining mood. Kami tidak menjual data kamu ke pihak
          ketiga mana pun.
        </p>
      </section>

      <section>
        <h2>Pihak ketiga yang memproses data</h2>
        <p>
          Untuk menghasilkan balasan, isi pesanmu diproses oleh penyedia model AI pihak ketiga
          (mis. Google Gemini/OpenAI) semata-mata untuk menghasilkan jawaban — bukan untuk melatih
          model publik mereka. Jika kamu memakai fitur suara, audio diproses oleh penyedia
          text-to-speech/speech-to-text pihak ketiga. Semua koneksi ini terenkripsi (HTTPS).
        </p>
      </section>

      <section>
        <h2>Penyimpanan &amp; keamanan</h2>
        <p>
          Data disimpan di server terkelola dengan akses dibatasi hanya untuk kebutuhan operasional
          sistem. Seluruh trafik antara perangkatmu dan server AXIS terenkripsi lewat HTTPS.
        </p>
      </section>

      <section>
        <h2>Penghapusan data</h2>
        <p>
          Kamu bisa menghapus akun kapan saja dari halaman Pengaturan. Menghapus akun akan
          menghapus data akun, riwayat percakapan, hasil skrining, dan seluruh memori jangka
          panjang yang tersimpan tentang kamu secara permanen.
        </p>
      </section>

      <section>
        <h2>Bukan pengganti layanan profesional</h2>
        <p>
          AXIS adalah teman refleksi berbasis AI, bukan tenaga medis, psikolog, atau psikiater.
          Skrining mood di dalam aplikasi bukan diagnosis klinis. Jika kamu dalam situasi darurat
          atau krisis, segera hubungi layanan bantuan di halaman{' '}
          <a href="/hotlines">Hotline &amp; Bantuan Darurat</a>.
        </p>
      </section>

      <section>
        <h2>Usia pengguna</h2>
        <p>AXIS ditujukan untuk mahasiswa/pengguna berusia 18 tahun ke atas.</p>
      </section>

      <section>
        <h2>Perubahan kebijakan</h2>
        <p>
          Kami dapat memperbarui kebijakan ini dari waktu ke waktu. Tanggal &quot;terakhir
          diperbarui&quot; di atas akan berubah setiap ada pembaruan berarti.
        </p>
      </section>

      <section>
        <h2>Kontak</h2>
        <p>
          Pertanyaan seputar privasi bisa dikirim ke{' '}
          <a href="mailto:mnugrahaekaprawira@gmail.com">mnugrahaekaprawira@gmail.com</a>.
        </p>
      </section>
    </LegalPageShell>
  );
}
