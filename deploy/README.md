# Demo ko server par live karna (Roman Urdu)

Yeh **demo / showcase** ke liye hai: sab naam aur figures banawati hain, har screen par peeli patti "DEMO SYSTEM" dikhti hai. Asli customer ya asli paisa is setup par **mat** daalein (us ke liye `docs/PRODUCTION_READINESS_REQUIREMENTS.md`).

Teen hisse chalte hain: **db** (PostgreSQL), **backend** (Django + gunicorn), **web** (Caddy: website + HTTPS + `/api/` ko backend tak pohnchana). AI copilot is mein shamil nahi; AI screens "unavailable" dikhayengi.

## Kya chahiye
- Aik Linux server (Ubuntu 22.04/24.04), kam az kam 2 GB RAM, 20 GB disk
- Aik domain ya subdomain (jaise `demo.aapkidomain.com`) jiska **A record** server ke IP par ho. (Domain na ho to neeche "Sirf IP" dekhein.)
- Server par port 80 aur 443 khule hon

## Qadam ba qadam
```bash
# 1. Docker install (aik dafa)
curl -fsSL https://get.docker.com | sh

# 2. Code server par laayein (git clone ya zip copy), phir:
cd "pool management system/deploy"
cp .env.example .env
nano .env
```

`.env` mein yeh badlein:
| Cheez | Kya likhein |
|---|---|
| `SITE_ADDRESS` | aap ka domain, jaise `demo.aapkidomain.com` |
| `ALLOWED_HOSTS` | wahi domain |
| `CORS_ALLOWED_ORIGINS` | `https://` + domain |
| `SECRET_KEY` | `openssl rand -base64 48` ka nateeja |
| `DB_PASSWORD` | koi mazboot password |

```bash
# 3. Chalayein (pehli dafa 5-10 minute lagte hain)
docker compose up -d --build

# 4. Data daalein: DEMO data (poora bhara hua system) ...
docker compose exec backend python manage.py seed_project_data --allow-non-debug --password 'ApnaDemoPassword#1'
#    ... YA khali system (aap ke apne test ke liye):
docker compose exec backend python manage.py bootstrap_clean_tenant --allow-non-debug --with-users --password 'ApnaDemoPassword#1'

# 5. Check
docker compose ps
curl -s https://demo.aapkidomain.com/api/v1/health/
```

Browser mein `https://demo.aapkidomain.com` kholein. Demo data ke logins: `<role>@novulabsdemo.test` (jaise `pm@novulabsdemo.test`); khali system ke: `<role>@novutest.test`. Password wohi jo upar diya.

**Password zaroor apna rakhein.** `Amanah@2026!` docs mein likha hua hai; internet par us se koi bhi login kar lega.

## Sirf IP (domain nahi)
`.env` mein `SITE_ADDRESS=:80`, `ALLOWED_HOSTS=<server-ip>`, `CORS_ALLOWED_ORIGINS=http://<server-ip>`, `SECURE_SSL_REDIRECT=False`. Phir `http://<server-ip>`. Yeh HTTPS ke baghair hai: passwords khule safar karte hain, sirf thori der ke demo ke liye.

## Roz ke kaam
```bash
docker compose logs -f backend          # backend ke logs
docker compose restart                  # dobara chalana
git pull && docker compose up -d --build   # naya code
docker compose exec db pg_dump -U amanah amanah > backup.sql   # database ka backup
```

## Agar kuch na chale
| Masla | Hal |
|---|---|
| Website khulti hai, login par error | `docker compose logs backend`; aksar `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` mein domain ghalat |
| HTTPS certificate nahi bana | domain ka A record server ka IP? port 80/443 khule? `docker compose logs web` |
| "Too many redirects" | IP par chala rahe hain to `SECURE_SSL_REDIRECT=False` |
| AI screens unavailable | Theek hai: copilot is setup mein nahi |

Note: yeh setup is repo mein Docker ke baghair wali machine par banaya gaya; Docker par khud chala kar test **nahi** hua. Pehli dafa chalate waqt koi error aaye to uska text bhejein.
