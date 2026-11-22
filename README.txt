TACTICAL STRIKE ONLINE - RENDER DEPLOY PAKETI

Bu paket Python aiohttp sunucusunu ve index.html oyun istemcisini içerir.

Yayınlama:
1. ZIP'i çıkarın.
2. İçindeki dosyaları GitHub'da yeni bir depoya yükleyin (server.py, index.html, requirements.txt, render.yaml).
3. Render hesabında New > Web Service seçin ve GitHub deposunu bağlayın.
4. render.yaml algılanırsa ayarları onaylayıp deploy edin.
5. Deploy tamamlanınca Render'ın verdiği https://....onrender.com adresini kullanın.

Not: Ücretsiz Render servisi 15 dakika trafik almazsa uykuya geçebilir; sonraki bağlantıda yaklaşık bir dakika açılması gerekebilir. Kalıcı açık kalması için ücretli servis gerekir.
Bu oyun oyuncu/oda durumunu bellekte tutar; sunucu yeniden başlarsa aktif odalar ve oyuncular sıfırlanır.
