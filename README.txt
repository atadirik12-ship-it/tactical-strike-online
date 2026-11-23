TACTICAL STRIKE ONLINE V4

Dosyalar:
- index.html: oyun arayuzu (PC, telefon ve Gamepad API destekli)
- server.py: aiohttp + WebSocket oyun sunucusu
- requirements.txt: sunucu bagimliliklari
- render.yaml: Render dagitim ayarlari

V4 yenilikleri:
- Takim Savasi (Mavi - Kirmizi) ve Herkes Tek (FFA) modlari
- Takimlarda otomatik dengeli oyuncu dagitimi
- Takim arkadasina hasar kapali
- Takim skoru, oyuncu olum/oldurme istatistikleri
- TAB ile acilan skor tablosu
- Son oldurmeleri gosteren kill feed
- Oda basina 12 oyuncu siniri ve oda modu kontrolu
- Onceki silahlar, mobil kontroller, sesli menu ve gamepad destegi korundu

Yerel calistirma:
1. Python 3.10+ kurulu olsun.
2. Komut satirinda bu klasore girin.
3. pip install -r requirements.txt
4. python server.py
5. Tarayicida http://127.0.0.1:8080 acin.

Render:
Mevcut Render servisine bu paketteki server.py, index.html, requirements.txt ve render.yaml dosyalarini yukleyin. Build: pip install -r requirements.txt | Start: python server.py

Arkadasinla oynama:
Ayni oda kodunu ve ayni oyun modunu secin. Herkese acik oda icin PUBLIC kullanin.

Not: Bu V4, onceki V3 web projesinin devamidir. PS2/PS5 icin yerel konsol uygulamasi degildir; gamepad destegi tarayicinin Gamepad API'si uzerinden calisir. Gercek PS2 USB adaptoru ve kontrolcu eslemesi adaptore gore degisebilir.
