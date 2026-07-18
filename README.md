# RAG-Foundry-Local

Yerelde çalışan RAG soru-cevap asistanı. Uygulama dokümanları parçalara böler, embedding üretir, SQLite'a kaydeder, soruya en yakın parçaları getirir ve bu bağlamı Microsoft Foundry Local üzerindeki yerel chat modeline gönderir.

Foundry Local SDK kuruluysa gerçek yerel model çağrılarını kullanır. SDK veya model henüz hazır değilse, proje akışını test edebilmek için deterministic embedding ve extractive fallback moduna geçer.

## Kurulum

Önce Python 3.11 veya üzeri kurulu olmalı. Kontrol:

```powershell
py --version
```

Eğer `No installed Python found` görürsen Python'u kurup PATH'e eklemen gerekir: https://www.python.org/downloads/

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Eğer Windows'ta `python` komutu bulunamazsa aynı komutları `py` ile dene:

```powershell
py -m venv .venv
.\.venv\Scripts\activate
py -m pip install -r requirements.txt
```

Foundry Local paketi kurulamazsa ilk deneme için yine de uygulamayı çalıştırabilirsin; kod fallback moduyla çalışır. Gerçek LLM cevabı için Foundry Local SDK kurulumunu tamamlamak gerekir.

Windows için Microsoft dokümanı `foundry-local-sdk-winml`, diğer platformlar için `foundry-local-sdk` paketini önerir. `requirements.txt` bunu platforma göre seçer.

Kurulum ve model kataloğunu kontrol etmek için:

```powershell
py -m app.healthcheck
```

## Doküman Ekleme

Metin dosyalarını şu klasöre koy:

```text
data/documents/
```

`.txt`, `.md` ve `.docx` dosyaları desteklenir.

Plan dosyasını doğrudan eklemek için:

```powershell
py -m app.ingest --file "C:\Users\mertu\OneDrive\Masaüstü\Summer School Foundry Local Plan.docx"
```

## Veritabanını Oluşturma

```powershell
python -m app.ingest
```

Alternatif:

```powershell
py -m app.ingest
```

Bu komut dokümanları okuyup `storage/rag.db` dosyasına parçaları ve embeddingleri yazar.

## Asistanı Çalıştırma

```powershell
python -m app.main
```

Alternatif:

```powershell
py -m app.main
```

Daha fazla kaynak parçası getirmek için:

```powershell
py -m app.main --top-k 5
```

Daha küçük ve hızlı bir Foundry Local modeli seçmek için:

```powershell
py -m app.main --top-k 5 --model qwen2.5-0.5b
```

Foundry Local model yüklemesi takılırsa veya sadece retrieval tarafını test etmek istersen:

```powershell
py -m app.main --top-k 5 --no-foundry
```

Çıkmak için:

```text
q
```

## Web Arayüzü

Modern yerel web arayüzünü başlatmak için:

```powershell
python -m app.web
```

Alternatif:

```powershell
py -m app.web
```

Tarayıcıda aç:

```text
http://127.0.0.1:8000
```

Foundry Local modelini yüklemeden yalnızca retrieval ve fallback cevabı test etmek için:

```powershell
py -m app.web --no-foundry
```

Farklı model veya daha fazla kaynak parçası için:

```powershell
py -m app.web --model qwen2.5-0.5b --top-k 5
```

## Proje Yapısı

```text
app/
  chunking.py    Metinleri parçalara böler
  config.py      Yol ve ayarlar
  db.py          SQLite işlemleri
  embeddings.py  Foundry veya fallback embedding
  generate.py    Foundry veya fallback cevap üretimi
  ingest.py      Dokümanları veritabanına işler
  main.py        CLI soru-cevap uygulaması
  web.py         Yerel web API ve statik arayüz sunucusu
  static/        HTML, CSS ve JS web arayüzü
  healthcheck.py Python, SQLite ve Foundry Local durumunu kontrol eder
data/documents/  Yerel bilgi kaynakları
storage/rag.db   Oluşturulan SQLite veritabanı
docs/architecture.md  RAG mimarisi ve Foundry notları
docs/plan_coverage.md  Summer school planına göre kapsam kontrolü
```

## Foundry Local Ayarları

Varsayılan chat model alias'ı:

```powershell
$env:FOUNDRY_CHAT_MODEL="qwen2.5-0.5b"
```

Embedding için Foundry Local catalog'unda uygun bir model alias'ı varsa:

```powershell
$env:FOUNDRY_EMBEDDING_MODEL="embedding-model-alias"
```

Bu değişken verilmezse retrieval tarafı yerel hash embedding ile çalışır. Chat tarafı yine Foundry Local kullanır.

## Kaynaklar

- Microsoft Foundry Local documentation: https://learn.microsoft.com/en-us/azure/foundry-local/
- Get started with Foundry Local: https://learn.microsoft.com/en-us/azure/foundry-local/get-started
- Foundry Local SDK reference: https://learn.microsoft.com/en-us/azure/foundry-local/reference/reference-sdk-current
- Microsoft Tech Community local RAG example: https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968
