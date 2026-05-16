# Hybrid Work Scheduling Optimizer

Gurobi tabanlı haftalık hibrit çalışma programı optimizasyon sistemi.  
Çalışanların müsaitlik, tercih ve departman işbirliği kısıtlarını dengeleyerek optimal ofis-gün ataması üretir.

---

## İçindekiler

- [Sistem Gereksinimleri](#sistem-gereksinimleri)
- [Proje Yapısı](#proje-yapısı)
- [Kurulum — Docker ile (Önerilen)](#kurulum--docker-ile-önerilen)
- [Kurulum — Yerel Geliştirme](#kurulum--yerel-geliştirme)
- [API Kullanımı](#api-kullanımı)
- [Örnek İstek / Yanıt](#örnek-istek--yanıt)
- [Konfigürasyon](#konfigürasyon)
- [CI/CD](#cicd)
- [Mimari Özeti](#mimari-özeti)

---

## Sistem Gereksinimleri

| Gereksinim | Versiyon | Notlar |
|-----------|---------|--------|
| Docker | 24+ | `docker --version` ile kontrol et |
| Docker Compose | v2+ | `docker compose version` (`docker-compose` değil) |
| Gurobi Lisansı | 11.x | Zorunlu — aşağıya bak |
| Python *(yerel geliştirme için)* | 3.12+ | Docker ile çalışmak için gerekmez |

> **Gurobi Lisansı Nereden Alınır?**  
> Akademik kullanım için [Gurobi Academic License](https://www.gurobi.com/academia/academic-program-and-licenses/) ücretsizdir.  
> Deneme için [Gurobi Free Trial](https://www.gurobi.com/free-trial/) 30 günlük lisans verir.  
> Lisans dosyası `gurobi.lic` adında, genellikle `~/gurobi.lic` konumundadır.

---

## Proje Yapısı

```
.
├── backend/                        # Orkestrasyon servisi (port 8000)
│   ├── api/
│   │   ├── routes.py               # POST /schedule, GET /health
│   │   ├── dependencies.py         # FastAPI DI wiring
│   │   └── error_handlers.py       # Exception → HTTP map
│   ├── application/
│   │   ├── dtos.py                 # Pydantic request/response modelleri
│   │   ├── mappers.py              # DTO ↔ Domain dönüşümleri
│   │   ├── validators.py           # İş kuralı doğrulama
│   │   └── optimization_service.py # Ana orkestrasyon akışı
│   ├── domain/
│   │   ├── models.py               # Temel domain varlıkları (frozen dataclass)
│   │   ├── enums.py                # Weekday, SolverStatus
│   │   ├── exceptions.py           # Hata hiyerarşisi
│   │   └── interfaces.py           # SolverInterface, DataLoaderInterface (ABC)
│   ├── infrastructure/
│   │   ├── file_loader.py          # JSON dosyalarından veri yükleme
│   │   └── gurobi_adapter.py       # HTTP üzerinden solver çağrısı
│   ├── main.py                     # FastAPI uygulama entry point
│   ├── config.py                   # Env tabanlı konfigürasyon
│   ├── requirements.txt
│   └── Dockerfile
│
├── solver/                         # Gurobi optimizasyon servisi (port 8001)
│   ├── api/
│   │   └── routes.py               # POST /solve, GET /health
│   ├── domain/
│   │   └── models.py               # Pydantic istek/yanıt şemaları
│   ├── engine/
│   │   ├── model_builder.py        # MIP formülasyonu (değişkenler, kısıtlar, amaç)
│   │   ├── solver.py               # model.optimize() + status işleme
│   │   └── result_extractor.py     # Çözüm çıkarma ve metrikler
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── data/
│   └── sample/                     # Test için örnek JSON veri seti
│       ├── employees.json
│       ├── availability.json
│       ├── preferences.json
│       ├── capacity.json
│       ├── collaboration.json
│       └── weights.json
│
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI pipeline
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Kurulum — Docker ile (Önerilen)

Bu yöntem Python veya gurobipy kurmanı gerektirmez. Her şey container içinde çalışır.

### Adım 1 — Repoyu klonla

```bash
git clone <repo-url>
cd "New project"
```

### Adım 2 — Gurobi lisansını yerleştir

```bash
# Lisans dosyan ~/gurobi.lic konumundaysa:
cp ~/gurobi.lic ./gurobi.lic

# Ya da doğrudan proje köküne kopyala
```

> Lisans dosyası proje kök dizininde `gurobi.lic` adıyla olmalıdır.  
> Bu dosya `.gitignore`'a eklenmiştir — asla commit edilmez.

Lisansın doğru konumda olduğunu kontrol et:
```bash
ls -la gurobi.lic
# -rw-r--r-- ... gurobi.lic
```

### Adım 3 — Servisleri başlat

```bash
docker compose up --build
```

İlk çalıştırmada image'lar build edilir (~2-3 dakika). Sonraki başlatmalarda çok daha hızlıdır.

Beklenen çıktı:
```
[+] Building ...
[+] Running 2/2
 ✔ Container solver   Healthy
 ✔ Container backend  Started
```

### Adım 4 — Servislerin hazır olduğunu doğrula

```bash
curl http://localhost:8000/health
# {"status":"healthy","service":"backend"}

curl http://localhost:8001/health
# {"status":"healthy","solver":"gurobi"}
```

Her ikisi de `healthy` dönüyorsa sistem kullanıma hazır.

### Adım 5 — İlk optimizasyon isteğini gönder

```bash
curl -s -X POST http://localhost:8000/schedule \
  -H "Content-Type: application/json" \
  -d @data/sample/request_example.json | python3 -m json.tool
```

Ya da aşağıdaki inline örneği kullan:

```bash
curl -s -X POST http://localhost:8000/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "employees": [
      {"employee_id":"E001","name":"Alice","department":"Engineering","min_days":2,"max_days":4},
      {"employee_id":"E002","name":"Bob","department":"Engineering","min_days":3,"max_days":5}
    ],
    "availability": [
      {"employee_id":"E001","day":"monday","available":1},
      {"employee_id":"E001","day":"tuesday","available":1},
      {"employee_id":"E001","day":"wednesday","available":1},
      {"employee_id":"E001","day":"thursday","available":0},
      {"employee_id":"E001","day":"friday","available":1},
      {"employee_id":"E002","day":"monday","available":1},
      {"employee_id":"E002","day":"tuesday","available":1},
      {"employee_id":"E002","day":"wednesday","available":1},
      {"employee_id":"E002","day":"thursday","available":1},
      {"employee_id":"E002","day":"friday","available":1}
    ],
    "capacity": [
      {"day":"monday","capacity":3},
      {"day":"tuesday","capacity":3},
      {"day":"wednesday","capacity":3},
      {"day":"thursday","capacity":3},
      {"day":"friday","capacity":3}
    ]
  }' | python3 -m json.tool
```

### Adım 6 — Swagger UI

Tarayıcıda aç: **http://localhost:8000/docs**

Tüm endpoint'leri, şemaları ve interaktif test arayüzünü görürsün.

### Servisleri durdur

```bash
docker compose down
```

Log'ları takip etmek istersen:
```bash
docker compose logs -f backend
docker compose logs -f solver
```

---

## Kurulum — Yerel Geliştirme

Docker olmadan, doğrudan Python ile çalıştırmak için.

> **Not:** `gurobipy` kurulumu için geçerli bir Gurobi lisansına ihtiyaç vardır.

### Adım 1 — Repoyu klonla

```bash
git clone <repo-url>
cd "New project"
```

### Adım 2 — Virtual environment oluştur

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### Adım 3 — Bağımlılıkları kur

```bash
# Backend bağımlılıkları
pip install -r backend/requirements.txt

# Solver bağımlılıkları (gurobipy lisans gerektirir)
pip install -r solver/requirements.txt
```

### Adım 4 — İki terminal aç

**Terminal 1 — Solver servisi:**
```bash
source .venv/bin/activate
python -m uvicorn solver.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 — Backend servisi:**
```bash
source .venv/bin/activate
APP_SOLVER_URL=http://localhost:8001 python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Adım 5 — Test et

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
```

---

## API Kullanımı

### `POST /schedule`

Optimizasyon isteği gönder, haftalık program al.

**Request Body:**

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|---------|
| `employees` | array | ✓ | Çalışan listesi |
| `availability` | array | ✓ | Günlük müsaitlik kayıtları |
| `preferences` | array | — | Tercih edilen günler (soft) |
| `capacity` | array | ✓ | Günlük ofis kapasitesi |
| `collaboration` | array | — | Departman bazlı minimum katılım |
| `weights` | object | — | Amaç ağırlıkları (varsayılan: miss=10, idle=1, pref=2) |

**Olası HTTP Yanıtları:**

| Status | Durum | Açıklama |
|--------|-------|---------|
| `200` | Optimal / Partial | Çözüm başarıyla üretildi |
| `422` | Validation Error | Girdi verisi hatalı (hata detayları body'de) |
| `409` | Infeasible | Kısıtlar birbiriyle çelişiyor — çözüm yok |
| `504` | Timeout | Solver zaman sınırını aştı |
| `502` | Solver Error | Solver servisi iç hata |

### `GET /health`

Backend servisinin liveness kontrolü.

### `GET /docs`

Otomatik Swagger UI — interaktif test için.

---

## Örnek İstek / Yanıt

**Request:**
```json
{
  "employees": [
    {"employee_id": "E001", "name": "Alice Yılmaz", "department": "Engineering",
     "min_days": 2, "max_days": 4}
  ],
  "availability": [
    {"employee_id": "E001", "day": "monday",    "available": 1},
    {"employee_id": "E001", "day": "tuesday",   "available": 1},
    {"employee_id": "E001", "day": "wednesday", "available": 1},
    {"employee_id": "E001", "day": "thursday",  "available": 0},
    {"employee_id": "E001", "day": "friday",    "available": 1}
  ],
  "preferences": [
    {"employee_id": "E001", "day": "monday",    "preferred": 1},
    {"employee_id": "E001", "day": "wednesday", "preferred": 1}
  ],
  "capacity": [
    {"day": "monday",    "capacity": 5},
    {"day": "tuesday",   "capacity": 5},
    {"day": "wednesday", "capacity": 5},
    {"day": "thursday",  "capacity": 5},
    {"day": "friday",    "capacity": 5}
  ],
  "weights": {"w_miss": 10.0, "w_idle": 1.0, "w_pref": 2.0}
}
```

**Response (`200 OK`):**
```json
{
  "status": "optimal",
  "objective_value": 3.0,
  "schedules": [
    {
      "employee_id": "E001",
      "department": "Engineering",
      "assigned_days": {
        "monday": true,
        "tuesday": false,
        "wednesday": true,
        "thursday": false,
        "friday": false
      },
      "total_assigned": 2,
      "missing_days": 0.0
    }
  ],
  "day_summaries": [
    {"day": "monday",    "used_capacity": 1, "idle_capacity": 4.0},
    {"day": "tuesday",   "used_capacity": 0, "idle_capacity": 5.0},
    {"day": "wednesday", "used_capacity": 1, "idle_capacity": 4.0},
    {"day": "thursday",  "used_capacity": 0, "idle_capacity": 5.0},
    {"day": "friday",    "used_capacity": 0, "idle_capacity": 5.0}
  ],
  "employee_metrics": [
    {"employee_id": "E001", "preference_satisfaction": 1.0}
  ],
  "team_attendance": [
    {"department": "Engineering", "day": "monday",    "count": 1},
    {"department": "Engineering", "day": "wednesday", "count": 1}
  ],
  "total_missing": 0.0,
  "total_preference_violations": 0,
  "solve_time_seconds": 0.08,
  "infeasibility_explanation": null
}
```

**Infeasible Yanıt (`409 Conflict`):**
```json
{
  "error": "infeasible",
  "message": "The scheduling problem has no feasible solution",
  "explanation": "IIS constraints: collab_Engineering_tuesday, avail_E001_tuesday"
}
```

**Validation Hatası (`422`):**
```json
{
  "error": "validation_error",
  "message": "Input has 1 validation error(s)",
  "issues": [
    {
      "field": "employees",
      "message": "Duplicate employee_id: 'E001'",
      "severity": "error"
    }
  ]
}
```

---

## Konfigürasyon

Tüm parametreler environment variable ile değiştirilebilir. Hardcoded değer yoktur.

### Backend (`APP_` prefix)

| Değişken | Varsayılan | Açıklama |
|---------|-----------|---------|
| `APP_SOLVER_URL` | `http://solver:8001` | Solver servis adresi |
| `APP_SOLVER_TIMEOUT_SECONDS` | `120` | HTTP timeout (saniye) |
| `APP_LOG_LEVEL` | `INFO` | Log seviyesi (`DEBUG`, `INFO`, `WARNING`) |

### Solver (`SOLVER_` prefix)

| Değişken | Varsayılan | Açıklama |
|---------|-----------|---------|
| `SOLVER_TIME_LIMIT_SECONDS` | `300` | Gurobi zaman sınırı |
| `SOLVER_MIP_GAP` | `0.01` | Kabul edilebilir optimality gap (%1) |
| `SOLVER_LOG_OUTPUT` | `false` | Gurobi log çıktısı (debug için `true`) |
| `SOLVER_THREADS` | `0` | CPU thread sayısı (`0` = otomatik) |
| `GRB_LICENSE_FILE` | — | Gurobi lisans dosyası yolu |

### Docker Compose ile override:

```bash
SOLVER_TIME_LIMIT_SECONDS=60 APP_LOG_LEVEL=DEBUG docker compose up
```

### Yerel geliştirmede override:

```bash
APP_SOLVER_URL=http://localhost:8001 APP_LOG_LEVEL=DEBUG \
  python -m uvicorn backend.main:app --port 8000 --reload
```

---

## CI/CD

GitHub'a push yapıldığında otomatik olarak çalışır.

**Pipeline aşamaları:**

```
push to main / PR
       │
       ├── lint-backend  (ruff check)
       │       │
       ├── lint-solver   (ruff check)
       │       │
       └───────┴──→ docker-build (her iki image build + compose config verify)
```

**Tetikleyiciler:**
- `main` ve `develop` branch'lerine push
- `main`'e açılan Pull Request'ler

Image'lar commit SHA ile tag'lenir:
```
scheduling-backend:<commit-sha>
scheduling-solver:<commit-sha>
```

---

## Sık Karşılaşılan Sorunlar

**`solver` servisi `Unhealthy` kalıyor:**
```bash
docker compose logs solver
```
Büyük ihtimalle `gurobi.lic` dosyası yanlış konumda ya da geçersiz.

**`ModuleNotFoundError: No module named 'gurobipy'`:**
Gurobi lisansı olmadan `solver` servisi başlamaz. Lisansı `./gurobi.lic` konumuna koy.

**`422 Unprocessable Entity` geliyor:**
Request body şemasını kontrol et. `min_days > max_days` veya duplicate `employee_id` gibi durumlar 422 üretir. Response body'deki `issues` alanı neyin yanlış olduğunu söyler.

**`409 Conflict` — Infeasible:**
Kısıtlar çelişiyor. Örnek sebepler:
- Bir departmana `collaboration.min_required = 3` ama departmanda 2 kişi var
- Bir çalışanın hiç müsait olmadığı günde atama zorunluluğu
Response'daki `explanation` alanı hangi kısıtların çeliştiğini gösterir.

**Port zaten kullanımda:**
```bash
docker compose down       # mevcut container'ları durdur
docker compose up --build
```

---

## Mimari Özeti

```
Client
  │
  │ HTTP POST /schedule
  ▼
Backend (FastAPI :8000)
  ├── Pydantic validation (field-level)
  ├── InputValidator (cross-collection rules)
  ├── DTO → Domain mapping
  └── GurobiHttpAdapter
        │
        │ HTTP POST /solve
        ▼
      Solver (FastAPI :8001)
        ├── build_model()  — MIP formülasyonu
        ├── run_optimization()  — Gurobi solver
        └── extract_results()  — çözüm + metrikler
```

Kullanılan matematiksel model: **Weighted Mixed-Integer Program (MIP)**
- Binary karar değişkeni `x[e,d]` — atama
- Soft kısıt `miss[e]` — minimum gün hedefi
- Amaç: `min 10×miss + 1×idle + 2×pref_violation`

---

## Katkı

1. Fork et
2. Feature branch oluştur (`git checkout -b feature/my-feature`)
3. Commit et (`git commit -m "Add my feature"`)
4. Push et (`git push origin feature/my-feature`)
5. Pull Request aç

Kod kalitesi için `ruff check .` komutunu commit öncesi çalıştır.

---

## Lisans

MIT
