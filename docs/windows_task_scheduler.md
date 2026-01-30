# Windows Task Scheduler ile otomatik başlatma (Servis)

1) Task Scheduler -> Create Task...
2) Triggers:
   - At startup (isteğe bağlı)
   - Repeat task every: 30 minutes (alternatif: servisi sürekli açık tutmak yerine cron gibi)
3) Actions -> Start a program
   - Program: `C:\...\python.exe`
   - Arguments: `service\run_service.py`
   - Start in: proje klasörü

> En stabil kullanım: servisi tek sefer başlatıp arka planda açık bırakmaktır.
