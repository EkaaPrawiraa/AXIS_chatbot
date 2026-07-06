import type { Metadata } from 'next';
import { LegalPageShell } from '@/components/v2/LegalPageShell';

export const metadata: Metadata = {
  title: 'Syarat & Ketentuan — AXIS',
  description: 'Ketentuan penggunaan layanan AXIS.',
};

export default function TermsPage() {
  return (
    <LegalPageShell title="Syarat & Ketentuan" lastUpdated="6 Juli 2026">
      <section>
        <p>
          Dengan membuat akun dan menggunakan AXIS, kamu menyetujui syarat dan ketentuan berikut.
          Jika kamu tidak setuju, mohon untuk tidak menggunakan layanan ini.
        </p>
      </section>

      <section>
        <h2>Tentang layanan</h2>
        <p>
          AXIS adalah teman refleksi harian berbasis AI yang dirancang untuk menemani, mendengarkan,
          dan membantu mahasiswa merefleksikan kondisi emosional sehari-hari, termasuk skrining mood
          mandiri (PHQ-9). AXIS <strong>bukan</strong> tenaga medis, psikolog, psikiater, atau
          layanan gawat darurat, dan tidak memberikan diagnosis atau resep medis apa pun.
        </p>
      </section>

      <section>
        <h2>Kelayakan pengguna</h2>
        <p>
          Layanan ini ditujukan untuk pengguna berusia 18 tahun ke atas. Kamu bertanggung jawab
          memberikan informasi akun yang benar dan menjaga kerahasiaan kata sandimu.
        </p>
      </section>

      <section>
        <h2>Penggunaan yang wajar</h2>
        <ul>
          <li>Jangan gunakan AXIS untuk aktivitas ilegal atau menyalahi hukum yang berlaku.</li>
          <li>Jangan mencoba merusak, membebani berlebihan, atau meretas sistem AXIS.</li>
          <li>Satu akun untuk satu pengguna; jangan bagikan kredensial akunmu ke orang lain.</li>
        </ul>
      </section>

      <section>
        <h2>Situasi darurat &amp; krisis</h2>
        <p>
          AXIS tidak dirancang untuk merespons keadaan darurat secara real-time. Jika kamu atau
          orang di sekitarmu berada dalam bahaya atau krisis kesehatan mental akut, segera hubungi
          layanan darurat atau lihat daftar kontak di halaman{' '}
          <a href="/hotlines">Hotline &amp; Bantuan Darurat</a>.
        </p>
      </section>

      <section>
        <h2>Konten &amp; kepemilikan</h2>
        <p>
          Kamu tetap memiliki hak atas isi pesan yang kamu kirim. Dengan menggunakannya di AXIS,
          kamu memberi izin kepada sistem untuk memproses dan menyimpan isi tersebut sebagaimana
          dijelaskan di <a href="/privacy">Kebijakan Privasi</a> kami, semata-mata untuk
          menjalankan layanan ini untukmu.
        </p>
      </section>

      <section>
        <h2>Batasan tanggung jawab</h2>
        <p>
          AXIS disediakan &quot;sebagaimana adanya&quot;. Kami berupaya menjaga layanan tetap
          bermanfaat dan aman, namun tidak menjamin balasan AI selalu akurat atau bebas kesalahan,
          dan tidak bertanggung jawab atas keputusan yang kamu ambil semata-mata berdasarkan
          balasan AXIS.
        </p>
      </section>

      <section>
        <h2>Penghentian akun</h2>
        <p>
          Kamu dapat menghapus akunmu kapan saja melalui halaman Pengaturan. Kami juga berhak
          menonaktifkan akun yang terbukti melanggar ketentuan ini.
        </p>
      </section>

      <section>
        <h2>Perubahan ketentuan</h2>
        <p>
          Ketentuan ini dapat diperbarui dari waktu ke waktu. Penggunaan berkelanjutan atas AXIS
          setelah pembaruan berarti kamu menyetujui ketentuan yang baru.
        </p>
      </section>

      <section>
        <h2>Hukum yang berlaku</h2>
        <p>Ketentuan ini tunduk pada hukum Republik Indonesia.</p>
      </section>

      <section>
        <h2>Kontak</h2>
        <p>
          Pertanyaan seputar ketentuan ini bisa dikirim ke{' '}
          <a href="mailto:mnugrahaekaprawira@gmail.com">mnugrahaekaprawira@gmail.com</a>.
        </p>
      </section>
    </LegalPageShell>
  );
}
