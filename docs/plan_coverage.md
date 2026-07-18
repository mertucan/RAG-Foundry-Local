# Summer School Foundry Local Plan Coverage

Kaynak dokuman: `Summer School Foundry Local Plan.docx`

## Gereksinim Durumu

| Plan maddesi | Durum | Projedeki karsiligi |
| --- | --- | --- |
| Yerel dokuman Q&A asistanı | Yapildi | `app/main.py`, `app/web.py` |
| RAG akisi: retrieve, augment, generate | Yapildi | `app/retrieve.py`, `app/generate.py` |
| Foundry Local ile yerel chat modeli | Yapildi | `app/foundry_runtime.py`, `app/generate.py` |
| Foundry hazir degilse test edilebilir fallback | Yapildi | `app/generate.py`, `app/embeddings.py` |
| Embedding uretimi | Yapildi | Foundry embedding modeli veya deterministic local hash fallback: `app/embeddings.py` |
| Vector similarity / cosine search | Yapildi | `app/retrieve.py` |
| SQLite chunk ve embedding saklama | Yapildi | `app/db.py`, `storage/rag.db` |
| Dokuman ingest pipeline | Yapildi | `app/ingest.py` |
| Chunking | Yapildi | `app/chunking.py` |
| `.txt`, `.md`, `.docx` kaynak dosya okuma | Yapildi | `app/document_loader.py` |
| CLI arayuzu | Yapildi | `app/main.py` |
| Modern web arayuzu | Yapildi | `app/web.py`, `app/static/` |
| Kaynak adlari ve skorlarini gosterme | Yapildi | CLI ve web cevap kaynaklari |
| Bos soru/eksik baglam kontrolu | Yapildi | `app/main.py`, `app/generate.py`, `app/web.py` |
| Healthcheck ve kurulum kontrolu | Yapildi | `app/healthcheck.py` |
| Proje dokumantasyonu | Yapildi | `README.md`, `docs/architecture.md` |
| Test/evaluation raporu | Kismen | Manuel test akisi var; otomatik test dosyalari henuz yok |
| Final sunum/demo materyali | Kapsam disi | Plan egitim programi icin ister; uygulama reposunda zorunlu degil |

## Link Kontrolu

| Link | Durum | Not |
| --- | --- | --- |
| https://learn.microsoft.com/en-us/azure/foundry-local/tutorials/tutorial-build-rag-app | Calisiyor | Microsoft Learn RAG tutorial sayfasi aciliyor |
| https://learn.microsoft.com/en-us/azure/foundry-local/what-is-foundry-local | Calisiyor | Microsoft Learn Foundry Local tanitim sayfasi aciliyor |
| https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/prompt-engineering | Calisiyor | Microsoft Learn prompt engineering sayfasi aciliyor |
| https://learn.microsoft.com/en-us/windows/apps/develop/data-access/sqlite-data-access | Calisiyor | Microsoft Learn SQLite sayfasi aciliyor |
| https://sqlite.org/index.html | Calisiyor | SQLite resmi ana sayfasi aciliyor |
| https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968 | Calisiyor | Microsoft Community Hub yazisi arama sonucunda ve sayfa basliginda dogrulandi |
| https://azurefeeds.com/2026/03/30/building-your-first-local-rag-application-with-foundry-local/ | Problemli | Arama sonucu kanonik kaynak olarak Microsoft Community Hub yazisini gosteriyor; dokumandaki Azure Feeds kopyasi yerine Tech Community linki tercih edilmeli |

## Kalan Iyilestirme Onerileri

- Otomatik test dosyalari eklenebilir: chunking, retrieval scoring, web API hata durumlari.
- README'deki Turkce karakter bozulmalari duzeltilebilir.
- Foundry embedding API yontemi kurulu SDK surumune gore ayrica denenmeli; fallback su an projeyi offline test edilebilir tutuyor.
