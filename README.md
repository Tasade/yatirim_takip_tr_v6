# Yatırım Takip Sistemi v6 (Türkiye/TRY) — Streamlit + Background Service

Bu sürüm **tam otomatik + zengin özellik** hedefiyle güçlendirildi:
- Servis Streamlit'ten bağımsız çalışır (APScheduler).
- SQLite **WAL** modu + busy_timeout: servis yazarken UI okurken kilitlenme azalır.
- Provider stratejisi:
  - Metals Primary: `kapalicarsi_apiluna` (Türkiye odaklı, TRY/gram + kurlar)
  - Metals Fallback: `metals_dev` (API key ile)
  - Final Fallback: `manual`
  - FX Primary: `exchangerate_host`, fallback: `frankfurter`, son çare: `tcmb` (günlük)

## Kurulum
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Çalıştırma
1) Servis:
```powershell
python service\run_service.py
```

2) UI:
```powershell
streamlit run app.py
```

## Manuel override
Provider bozulursa Streamlit içinden “Manuel Fiyat” sekmesinden fiyat gir, sistem çalışmaya devam eder.

## Not
Kapalıçarşı community endpoint'i üçüncü taraf olduğu için zaman zaman erişim sorunu yaşanabilir; bu yüzden fallback + stale stratejisi tasarlandı.
