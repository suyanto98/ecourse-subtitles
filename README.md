# Subtitle Bahasa Inggris Otomatis untuk E-Course

Menaruh video (.mp4/.mkv/.mov/.avi/.webm/.m4v) di `~/Videos` akan otomatis
menghasilkan file subtitle Inggris (`.srt`) dengan nama yang sama di folder
yang sama, tanpa perlu menjalankan command apa pun. Kebanyakan video player
(VLC, mpv, browser HTML5 `<video>`) otomatis memuat file `.srt` yang basename-nya
sama dengan videonya.

Pipeline: ffmpeg (extract audio) -> faster-whisper `medium` (transkrip EN) -> file `.srt`.

## Kecepatan (CPU-only, tanpa GPU)

- Transkripsi: ±2-3x lebih cepat dari durasi video (video 1 jam ≈ 20-30 menit)
- Tidak ada langkah translate lagi, jadi ini sekarang satu-satunya tahap yang
  butuh waktu. Proses berjalan di background, tidak perlu ditunggu.

## Cek status service

```
systemctl --user status subtitle-watcher   # cek jalan/tidak
journalctl --user -u subtitle-watcher -f   # lihat log real-time
systemctl --user restart subtitle-watcher  # restart manual kalau perlu
```

Service otomatis start saat boot/login (linger diaktifkan), dan auto-restart
kalau crash.

## File di folder ini

- `watcher.py` — pemantau folder ~/Videos
- `pipeline.py` — extract audio -> transkrip -> tulis srt
  (bisa dijalankan manual: `.venv/bin/python pipeline.py path/ke/video.mp4`)
- `batch_folder.py` — proses semua video di satu folder sekaligus
  (`.venv/bin/python batch_folder.py path/ke/folder`)
- `state.json` — daftar video yang sudah diproses (supaya tidak diulang saat
  restart). Hapus isinya (`{}`) kalau ingin memaksa semua video diproses ulang.
- `subtitle-watcher.log` — log proses & error
