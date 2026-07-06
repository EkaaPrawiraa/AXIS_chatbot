# AXIS frontend_v2 Animation Library

File `index.ts` berisi token animasi yang dipakai ulang di seluruh `frontend_v2`.

## Isi

- `animationTimings`: durasi standar (`quick`, `standard`, `calm`, `slow`) dalam milidetik.
- `animationEasings`: kurva easing yang terasa lembut untuk UI AXIS.
- `animationClasses`: nama class CSS reusable yang implementasinya ada di `app/globals.css`.
- `motionStyleVars()`: helper untuk mengatur durasi, delay, dan easing per komponen melalui CSS variables.

## Class Yang Tersedia

- `v2-anim-page-enter`: masuk halaman dengan fade dan slide kecil.
- `v2-anim-card-enter`: masuk kartu/section dengan gerak lebih halus.
- `v2-anim-field-group-enter`: animasi field yang muncul, misalnya field tambahan saat pindah dari login ke register.
- `v2-anim-soft-pop`: feedback halus untuk error/info state.
- `v2-anim-pressable`: micro-interaction untuk tombol yang bisa ditekan.
- `v2-anim-segment-indicator`: transisi indikator segmented control seperti Login/Register.
- `v2-anim-hero-enter`: animasi masuk untuk hero utama dashboard atau halaman landing.
- `v2-anim-stagger-item`: animasi item berurutan, misalnya quick action di dashboard.
- `v2-anim-image-float`: gerak ilustrasi sangat halus agar halaman terasa lebih hidup.
- `v2-anim-chat-bubble-in`: animasi bubble chat saat pesan muncul.
- `v2-anim-composer-in`: animasi composer chat saat halaman dibuka.
- `v2-anim-sheet-backdrop-in`: fade backdrop untuk bottom sheet, misalnya riwayat chat.
- `v2-anim-sheet-up`: bottom sheet naik halus dari bawah.
- `v2-anim-progress-grow`: progress bar bertumbuh dari kiri, dipakai pada PHQ/mood check bertahap.

## Prinsip Pemakaian

Gunakan animasi hanya untuk membantu orientasi user, bukan untuk membuat UI terasa ramai. Prioritaskan transform dan opacity agar performa mobile tetap ringan. Semua class mengikuti `prefers-reduced-motion`, sehingga user yang mengurangi animasi di sistem operasi tetap mendapat pengalaman yang nyaman.
