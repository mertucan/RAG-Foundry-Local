# Foundry Local RAG Demo Bilgileri

Bu proje, bilgisayar bilimi öğrencilerinin yerelde çalışan bir RAG tabanlı soru-cevap asistanı geliştirmesi için tasarlanmıştır. Uygulama internet bağlantısı olmadan çalışabilmeli ve cevaplarını yerel dokümanlardan alınan bağlama dayandırmalıdır.

RAG, Retrieval-Augmented Generation anlamına gelir. Sistem önce kullanıcının sorusuyla ilgili doküman parçalarını bulur, sonra bu parçaları dil modeline bağlam olarak verir. Bu yaklaşım modelin uydurma cevap verme riskini azaltır.

SQLite bu projede yerel veri saklama katmanı olarak kullanılır. Doküman parçaları, kaynak dosya adları ve embedding vektörleri tek bir SQLite veritabanı dosyasında tutulur.

İlk sürümde komut satırı arayüzü yeterlidir. Daha sonra Streamlit veya Flask ile basit bir web arayüzü eklenebilir.

