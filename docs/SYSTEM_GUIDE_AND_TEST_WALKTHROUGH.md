# Amanah Pool OS: poora system samajhna aur khud test karna

Yeh guide beginner ke liye hai. Pehle samajh (Hissa 1 se 5), phir system chalana (Hissa 6), phir khud test karna (Hissa 7).
Hissa 8 batata hai ke presentation mein kya kehna theek hai aur kya nahi.

---

## Hissa 1: Yeh system kya hai (aam zubaan mein)

Ek bank ya fund ke paas bohot se logon ka paisa hota hai. Wo sab ka paisa ek jagah jama karke karobar mein lagata hai, aur jo
nafa (profit) aata hai wo logon mein baanta jata hai. Is ko **pool** kehte hain: misaal ke taur par mohalle ke 10 log apna paisa
ek matke mein daalein, matke se karobar ho, aur kamayi har banda apne hisse ke hisaab se le.

**Bina system ke** yeh sab spreadsheet par hota hai: ghalti ka khatra, ek aadmi akela hisaab bana bhi sakta aur manzoor bhi kar sakta,
aur baad mein saboot nahi hota. **Amanah Pool OS** yeh sab ek jagah karta hai: hisaab computer karta hai, har kaam do alag logon se
guzarta hai, aur har qadam ka record mehfooz rehta hai.

Aur yeh **Islami** isliye hai ke: byaaj (riba) nahi, haram income (jaise late fee ki penalty) khatedaaron mein nahi baanti balki alag
rakh kar khairat mein jati hai, nuqsan bhi hisse ke hisaab se baanta jata hai, aur koi naya product Shariah Board ki manzoori ke
baghair shuru nahi hota. System khud fatwa nahi deta; wo Board ki manzoori ko record aur lagu karta hai.

## Hissa 2: Zaroori lafz

| Lafz | Matlab |
|---|---|
| **Pool** | Logon ka ek jagah jama paisa, jis se karobar hota hai |
| **Product** | Pool ki qism ka "nuskha": kaunsa contract, kitne ka kam se kam, kab nikal sakte hain |
| **Contract (Mudarabah, Musharakah, Wakalah, Qard)** | Paise aur nafe ke baantne ka Islami muaahida. Mudarabah: ek paisa lagata, doosra kaam karta, nafa tay hisse se. Musharakah: dono paisa lagate, nuqsan paise ke hisse se. Wakalah: ek agent fees par kaam karta. Qard: bina nafe ka karz (committee) |
| **PSR (Profit Sharing Ratio)** | Nafa kis hisaab se banta: jaise 70% khatedaar, 30% bank |
| **Weightage** | Kisi qisam ke account ko thora zyada wazan (jaise lambi muddat ka deposit) |
| **Mudarib** | Wo jo paisa chalata hai (bank ya manager). Uska hissa nafe ka hota hai, paise ka nahi |
| **Allocation run** | Ek period ka profit baantne ka hisaab |
| **Maker / Checker** | Maker banata hai, doosra (Checker) jaanchta hai. Ek aadmi dono nahi ho sakta |
| **Daily close** | Din ke aakhir mein balances check karke din "band" karna (do log) |
| **Period close** | Mahine ka hisaab band aur lock karna |
| **Journal** | Hisaab-kitaab ki double entry: jo debit wahi credit |
| **GL** | Bank ka asli hisaab ka register (general ledger) |
| **Suspense** | Wo raqam jis ka maalik ya wajah abhi maloom nahi: usay naam ke saath rakha jata hai |
| **PER / IRR** | Do reserve jo achhe dinon mein jama hote hain taake bure dinon mein nafa barabar rahe |
| **Purification** | Haram income ko khatedaaron se alag karke khairat mein dena |
| **Fatwa / Shariah decision** | Shariah Board ka likha hua faisla jis par product khada hota hai |
| **Quorum** | Faisle ke liye board ke kam az kam itne log (yahan do tihai) |
| **KYC** | Customer ki shanakht ki tasdeeq |
| **Restatement** | Signed hisaab mein ghalti ho to usay mita kar nahi, ulta (reverse) karke naya hisaab banana |
| **Audit trail** | Har kaam ka kaun, kab, kya ka na mitne wala record |

## Hissa 3: Teen qisam ke pool

| Pool | Aam zubaan | Demo mein |
|---|---|---|
| **Bank Pool** | Bank ke khatedaaron ka jama paisa; bank karobar karta, nafa baantta | POOL-GEN-01 (General Depositor Pool) aur POOL-TREAS-02 (Treasury Wakala Pool) |
| **Investment Pool** | Log ek fund mein paisa lagate hain, manager asaasay mein lagata hai; nafa/nuqsan hisse ke hisaab se | POOL-CORP-03 (SME Diminishing Musharakah Pool) |
| **Community Circle** | Dosto/khandan ki committee: har mahine sab daalte hain, har mahine ek ki baari; koi byaaj nahi | POOL-CIR-01 (Karachi Healthcare Workers Welfare Circle, 5 members) |

**Profit kaise bantta hai (BRD ki apni misaal):** pool ne 12,000,000 kamaye, seedhe kharche 1,000,000, baaqi 11,000,000.
Khatedaar A ka paisa 60 million, B ka 40 million (kul 100). A ko 60% = **6,600,000**, B ko 40% = **4,400,000**.
Asal mein din ke hisaab se average funds, weightage aur bank ka hissa bhi shamil hote hain, magar asool wohi hai: jis ka paisa zyada
aur zyada din laga, usay zyada nafa.

## Hissa 4: Kaun kya karta hai (roles)

**Sab ka password: `Amanah@2026!`**. Email: `<naam>@novulabsdemo.test`

| Login | Kaun hai | Kya kar sakta hai | Kya NAHI kar sakta |
|---|---|---|---|
| `superadmin` | Platform administrator | Tenants, users, rule packs, website ki enquiries; audit trail dekhna | Audit log mein sirf platform ke events (login, users, tenants, settings); bank ka kaarobar aur raqam nahi |
| `pm` | Product manager | Product banana, draft karna | Apna product khud manzoor nahi |
| `poolmanager` | Pool manager | Pool banana, assets lagana, run tayyar karna, circle chalana | Run ya Shariah exception manzoor nahi |
| `maker` | Finance maker | Balances import, income/expense likhna, daily close tayyar karna, GL export banana, suspense propose karna | Apna likha khud post/manzoor nahi |
| `checker` | Finance checker | Maker ka kaam jaanchna: post, independent check, daily close sign, GL ka jawab darj karna | Apna banaya khud nahi |
| `secretariat` | Shariah secretariat | Research, Shariah review (run par) | Aakhri ruling nahi |
| `board`, `board2`, `board3` | Shariah Board | Fatwa manzoor (quorum), exceptions ka faisla, quarantined value ka treatment | Akela bandah fatwa nahi |
| `risk` | Risk & Compliance | Exceptions, limits, related-party, KYC, proposals | Profit mein dakhal nahi |
| `signatory` | Authorized signatory | Aakhri release (do logon ke baad teesra) | Jo run khud banai ya check ki wo release nahi |
| `auditor` | Auditor | Sirf padhna: evidence, audit log, sampling | Kuch post/badal nahi sakta |
| `investor` | Investor/depositor | Sirf apna data: statement, disclosures, consent, request | Kisi aur ka data nahi |
| `mudarabah.investor` | Investor (investment pool mein units) | Apne units dekhna, redemption request | Kisi aur ka data nahi |
| `member` | Circle member (MEM-002) | Apna circle, voting, receipts, request | Doosre ka data nahi |

**Teen sab se bari khoobiyan (presentation mein zaroor kahein):**
1. **Maker-Checker:** koi bhi paison ka kaam akela poora nahi kar sakta.
2. **Role separation:** har role ko sirf apni screens dikhti hain; server bhi baaqi cheezon se mana karta hai (sirf chhupa dena kaafi nahi).
3. **Saboot:** har qadam audit trail mein, aur signed hisaab badla nahi ja sakta (ghalti ho to ulta karke naya).

## Hissa 5: Menu mein kya kya hai (kaun si screen kis ko)

| Menu | Andar kya hai | Kis ko dikhti hai |
|---|---|---|
| **Command Center** | Apne role ka dashboard (counts aur "yahan kaam hai") | Sab staff |
| **Products & Pools** | Products, pools, **New Pool** wizard (6 qadam), pool detail (Overview, Weightage & PSR, Assets, Version Diff) | Sab staff |
| **Participants** | Khatedaar, accounts, KYC | Pool mgr, finance, risk, auditor |
| **Daily Operations** | Operations Cockpit, Balance Import, Income & Expense, Reconciliation, **Daily Close**, Period Close & Locking, Payout Clearing | Pool mgr, finance, risk, auditor, signatory |
| **Allocation Engine** | Allocation Simulator (profit ka hisaab), Scenario Comparison, runs aur unka ceremony | Operations, Shariah, signatory |
| **Investments** | Pool Dashboard, Investor Onboarding, Capital Accounts, Venture View, Subscription & Redemption, NAV, **Profit Distribution** | Operations, Shariah, signatory |
| **Community Circles** | Circle Setup, Roster, Calendar, **Rotation / Draw Room**, Rules Draw & Closure, Payout Release, Member Mobile, Hardship & Arrears, Proposals & Voting | Operations, Shariah |
| **Shariah Governance** | Board Workspace, Quorum & Fatwa Seal, Fatwa Register, Exception Cases, Purification Ledger, Shariah Audit Plan | Shariah, risk, auditor, pool mgr, pm, signatory |
| **Risk & Compliance** | Asset Registry, Provisions, **Exception Queue**, Related-Party, Risk Dashboard, Dispute Center | Operations roles |
| **Finance & Ledger** | Journal Batches, Income & Expense, **GL Hand-over & Trial Balance**, **Suspense** | Finance, signatory, risk, auditor, pool mgr |
| **AI & Analytics** | Copilot (Shariah sawal-jawab), Documents, Model Governance, Anomaly Queue | Shariah, pm, risk |
| **Reports** | Evidence bundle, audit trail verification, sampling, period report | Auditor, risk, pool mgr, checker, board |
| **Governance Config** | Approval matrix, account mapping, **pending changes** (maker-checker) | Risk, finance, pool mgr, auditor |
| **Administration** | Users, tenants, rule packs, security audit log, website enquiries | Sirf `superadmin` |
| **My Portal** (investor/member) | Apne accounts, statements, disclosures, privacy/consent, requests, circle | Investor, member |

Public website: **/welcome** (login se pehle).

## Hissa 6: System chalana

Teen cheezein chalti hain. Tino alag terminal mein.

```
# 1. Backend (Django)
cd "D:\Projects\Pool Management\pool management system\backend"
set AUTH_THROTTLE_RATE=1000/min        (sirf testing ke liye; Windows cmd)
python manage.py runserver 8000

# 2. Frontend (website + app)
cd "D:\Projects\Pool Management\pool management system\frontend"
npm run dev

# 3. Copilot (AI Shariah sawal-jawab; na chalaye to sirf AI wali screens "unavailable" dikhengi)
cd "D:\Projects\Pool Management\pool management system\shariah-policy-copilot\backend"
venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

- Website: **http://localhost:5173/welcome**
- Login: **http://localhost:5173/login**
- Check: http://localhost:8000/api/v1/health/ready/ ("ready" aaye), http://localhost:8001/health ("ok")

**Demo data dobara taaza karna** (jab test ke baad sab gadbad ho jaye): backend folder mein `python manage.py seed_project_data`
(servers chalte rehne dein). Isse tamam demo records wapas shuru ki halat par aa jate hain.

**Demo data kis halat mein hai:** July aur August ki runs signed, September ki run intezar mein; investment pool ki September
distribution intezar mein; ek **critical exception khula** hai (yeh jaan-boojh kar hai, isse dikhta hai ke exception khula ho to release
nahi hota); 4 fatwa approved; circle ka pehla cycle settle.

## Hissa 7: Khud test karna: qadam ba qadam

Har test mein: **login (kaun)** → **kahan jana** → **kya karna** → **kya dikhna chahiye**. Beech mein login badalne ke liye
upar kone mein apne naam ke paas se sign out karein, ya browser ka naya (private) window kholein.
Agar kuch alag dikhe, **screenshot** lein aur note karein: test number, kya kiya, kya dikha.

### Test 1: Website aur login
1. Browser mein `http://localhost:5173/welcome` kholein. **Dikhna chahiye:** premium website (hero, concepts, models, demo form).
2. Neeche demo-request form bhar ke bhejein. **Dikhna:** "received" jaisa message. (Baad mein Test 17 mein `superadmin` isey dekhega.)
3. "Sign in" par click karein, galat password dalein. **Dikhna:** saaf galat-password ka paigham.
4. `checker@novulabsdemo.test` / `Amanah@2026!` se login. **Dikhna:** Command Center, aur menu mein sirf checker ki screens (Administration nahi).

### Test 2: Har role ko sirf apni screens
1. Baari baari login karein: `superadmin`, `pm`, `maker`, `risk`, `auditor`, `investor`.
2. Har ek ka **menu** dekhein aur Hissa 5 ki table se milayein.
3. Menu mein na dikhne wali screen ka address by-hand likhein (jaise `investor` ke saath `localhost:5173/allocation-engine`).
   **Dikhna:** wapas aapke ghar ki screen par bhej diya jata hai.
4. **Dikhna:** `superadmin` ko Administration ke siwa koi maali screen nahi; `investor` ko sirf "My Portal".

### Test 3: Investor ka portal
1. Login `investor`. **Dikhna:** "Assalamu alaikum" ke saath apne accounts, statements, disclosures, "My privacy", requests.
2. "My privacy" mein apni consent dekhein; "download my data" par click karein. **Dikhna:** sirf apna data.
3. Login `mudarabah.investor`. **Dikhna:** investment pool mein apne units aur statement.
4. Redemption request dein (units ki kam miqdar). **Dikhna:** request "pending" jaati hai; paisa abhi nahi nikla (checker baad mein manzoor karega).

### Test 4: Circle member
1. Login `member`. **Dikhna:** "My savings circles" mein sirf apna circle (MEM-002), apni contributions, payout position, circle ledger.
2. Circle ledger mein har cycle ka lene wala sirf **member reference** ke tor par dikhta hai (naam nahi).
3. Kisi proposal par vote dein. **Dikhna:** ek hi vote chalta hai; dobara dene se refuse.
4. Ek request ("Tell us what happened") bhejein. **Dikhna:** aapko dikhti hai; staff ko notification jati hai.

### Test 5: Naya product aur naya pool
1. Login `pm` → **Products & Pools** → naya product banayein (asset types ke tick boxes aur participation terms). **Dikhna:** draft ban gaya.
   Kam se kam raqam se zyada "cap" daal kar dekhein. **Dikhna:** refuse (galat combination).
2. Login `poolmanager` → **Products & Pools** → **New Pool**. 6 qadam wizard: Model, Contract, Economics, Assets, Governance, Review. **Dikhna:** draft pool.
3. Naye pool ke detail mein "Open Pool" ka button **poolmanager ko nahi** dikhta (sirf independent checker ya signatory activate kar sakta).

### Test 6: Maker-checker ki bunyad (income/expense)
1. Login `maker` → **Daily Operations** → **Income & Expense** → naya event likhein (income, September ki koi tareekh, raqam).
   **Dikhna:** "pending".
2. Isi screen par maker ko "post" ka button **nahi** dikhta.
3. Login `checker` → wahi screen → us event ko **Post** karein. **Dikhna:** ab "posted"; ab ye badla nahi ja sakta.

### Test 7: Daily close
1. Login `maker` → **Daily Operations** → **Daily Close** → POOL-GEN-01, tareekh 2026-09-29.
   **Dikhna:** gates (shartein) jo server khud nikalta hai; ek gate fail hai (khula critical exception). Din "open" rehta hai.
2. Login `checker` → wahi. **Dikhna:** fail wale gate ke saath din sign nahi hota.
3. Sabaq: gates haath se tick nahi hote, server ke records se aate hain.

### Test 8: Poori ceremony: investment pool ka nafa (check → Shariah → release)
Yeh sab se zaroori test hai. **Teen alag log**, teen alag qadam.
1. Login `checker` → **Investments** → pool **POOL-CORP-03** → **Profit Distribution**. **Dikhna:** September ki distribution "pending_approval".
   Pehle us par dobara click karke dekhein: raqam, manager ka hissa, investors ka hissa, har investor ki line.
2. `checker` → **Independent check**. **Dikhna:** status "checked".
3. Login `board` (ya `secretariat`) → wahi screen → **Shariah review** (note likhein). **Dikhna:** status "shariah_review".
4. Login `signatory` → **Release**. **Dikhna:** status "signed".
5. Login `maker` → **Finance & Ledger** → **Journal Batches** → pool POOL-CORP-03. **Dikhna:** nayi journal, debit = credit.
6. **Ulta test:** dobara naye run mein `checker` se seedha "Release" dhoondein: button hi nahi; aur `signatory` ko Check wala button nahi. Ek aadmi do qadam nahi kar sakta.

### Test 9: Bank pool ki run ka refuse hona (controls ka saboot)
1. Login `checker` → **Allocation Engine** → POOL-GEN-01 ki September run (intezar mein).
2. "Independent check" dabayein. **Dikhna:** refuse, kyunke September ke un dinon ki daily close sign nahi jin din balances hain (wajah saaf likhi aati hai).
3. Sabaq: bina signed din ke profit nahi bantta. Aur khula critical exception release bhi rokta hai (Test 13 mein hata kar dekhein).

### Test 10: GL ko journal bhejna aur Trial Balance
1. Login `maker` → **Finance & Ledger** → **GL Hand-over & Trial Balance** → pool POOL-GEN-01 → **Generate export**.
   **Dikhna:** ek file ban gayi, "Awaiting GL answer". Button dobara dabayein: "Every posted batch has been sent" (koi batch do baar nahi jati).
2. **Download** karke dekhein: file wahi hai jo bheji gayi.
3. Login `checker` → wahi tab → **Confirm posted** (GL ka reference likhein, jaise ERP-JV-001). **Dikhna:** "Posted in GL".
   Maker ko ye button nahi dikhta.
4. Neeche **Trial balance**: har GL code par debit/credit, **(balanced)** likha aata hai. "As of" tareekh badal kar dekhein.

### Test 11: Suspense
1. Login `maker` → **Finance & Ledger** → **Suspense** → "Park an amount": "Money in, owner not known", raqam 1234.50, reference, "kya maloom hai". **Propose**.
   **Dikhna:** "Proposed"; abhi kuch post nahi hua.
2. Login `checker` → **Approve and post**. **Dikhna:** "Open in suspense"; upar position mein "Every amount is a named item".
3. Login `maker` → us item par **Propose clearing** → "Depositor Payable" chunein, wajah likhein → `checker` **Approve clearing**. **Dikhna:** "Cleared".

### Test 12: Maker-checker config (approval matrix)
1. Login `risk` → **Governance Config** → approval matrix mein koi limit badalne ka proposal (wajah zaroor likhein).
   **Dikhna:** "Changes awaiting approval" mein pending; asli matrix abhi nahi badla.
2. Login `checker` → wahi screen → **Approve**. **Dikhna:** ab lagu hua. `risk` khud approve nahi kar sakta.

### Test 13: Exception ka paisa rokna (quarantine)
1. Login `risk` → **Risk & Compliance** → **Exception Queue** → "Late Transit Float Interest Credited by Correspondent Bank" kholein.
2. "Quarantined value" mein raqam (jaise 9000) aur wajah likh kar **Quarantine this value**. **Dikhna:** "Treatment not decided yet".
3. Case band karne ki koshish (Resolve). **Dikhna:** refuse: pehle Shariah Board faisla kare.
4. Login `board` → wahi case → Treatment (jaise "Purify: route to charity") aur wajah → **Record the Board's decision**.
5. Login `risk` → Notes aur **Disclosure** likh kar Resolve. **Dikhna:** case band, disclosure darj.
6. **Asar:** ab pool par koi khula serious exception nahi, to daily close aur release ka ek rukawat hat gayi.

### Test 14: Shariah Governance
1. Login `board` → **Shariah Governance** → **Fatwa Register**: 4 approved rulings. Kisi ko kholein.
2. **Quorum & Fatwa Seal**: Board ki do tihai manzoori ka tareeqa. Ek akela member manzoor nahi kar sakta (agar naya ruling draft karein to dekh sakte hain).
3. **Purification Ledger**: haram income jo khairat mein jayegi, alag record.
4. **Shariah Audit Plan**: plan, findings, aur saalana report.

### Test 15: Community circle
1. Login `poolmanager` → **Community Circles** → **Member Roster** (5 log), **Contribution Calendar**, **Payout Release Ceremony** (pehla cycle settle).
2. **Rotation / Draw Room** → "Draw ceremony". **Dikhna:** do qadam: (1) Seal (fingerprint dikhta hai), (2) Reveal members ke apne seed se.
   Is demo circle mein sab ki baari pehle se tay hai, is liye seal par "har member ko position mil chuki" ka paigham aa sakta hai: yeh theek hai.
3. Reveal wala button tab tak band jab tak seed 4 harf se kam ho. Seed browser khud nahi banata.
4. **Mutual Hardship Turn Swap**: wajah ka box khaali hota hai (pehle se likha nahi), aur dono members ki razamandi ka reference zaroori hai.

### Test 16: AI Copilot (copilot service chalni chahiye)
1. Login `board` → **AI & Analytics** → **Ask**: "What is the policy on late payment charges?". **Dikhna:** jawab **hawale ke saath** (document, section, page).
2. Aisa sawal poochein jis ka demo documents mein jawab nahi (jaise "Atlantis ki rajdhani?"). **Dikhna:** ek tay shuda "koi approved ruling nahi mili" jawab: wo kuch gharta nahi.
3. **Model Governance**: har AI output ka record, usme "source, confidence, reason" aur insaan ka faisla (accept/reject).
4. Copilot band kar ke dekhein: baaqi system ka maali kaam waise hi chalta hai.

### Test 17: Administration (superadmin)
1. Login `superadmin` → **Administration**: Users, Tenants, Rule Packs, **Website Enquiries** (Test 1 wala form yahan dikhega, "Mark handled").
2. **Security & Audit Log**: kaun-kya-kab dikhta hai, magar **raqam aur wajah chhupi** hoti hain.
3. Maali screens (pools, runs) address likh kar kholne ki koshish: wapas bhej diya jata hai / refuse.

### Test 18: Auditor
1. Login `auditor` → **Reports**: evidence bundle banayein, audit trail ki chain verify karein (hash match hona chahiye), sampling.
2. Koi button dhoondein jo post/approve/edit kare: **koi nahi hona chahiye**.

### Test 19: Zubaan
Upar kone mein **EN / اردو** switch: menu aur kai ibaratein Urdu (right-to-left) mein badalti hain.

### Test 20: Har role ka dashboard
Har role se login karke **Command Center** dekhein. Har ek ko apne kaam ki ginti dikhti hai (jaise finance ko "daily closes intezar mein", risk ko "high exceptions", signatory ko "release ke liye tayyar runs"). Dashboard ke figure screens ke figures se milne chahiye.

## Hissa 8: Presentation mein kya kehna theek hai aur kya nahi

**Kehna theek hai:**
- "Har paisay ka kaam do alag logon se guzarta hai; system khud rokta hai."
- "Signed hisaab badla nahi jata, ghalti ho to ulta karke naya hisaab."
- "Har role ko sirf apni screens; investor sirf apna data."
- "Haram income alag, byaaj nahi, aur product Shariah Board ki manzoori ke baghair nahi."
- "AI sirf salah deta hai, faisla insaan ka; har AI jawab record hota hai."

**Jhoot ho sakta hai, mat kahein:**
- "Yeh asli bank se jura hua hai." **Nahi.** Raast/1LINK/core banking/KYC/e-sign sab **simulation** hain ya insaan ke haath se hotey hain.
- "Yeh asli paise ke liye tayyar hai." **Nahi.** Abhi pilot nahi hua; Shariah UAT, parallel run, penetration test, backup ka saboot baqi hain.
- "Tax ya Zakat sahi lagta hai." Withholding rates (15%/30%) sirf demo ki qeematein hain, adviser se tasdeeq baaqi.
- "Yeh fatwa ya qanooni raay deta hai." **Nahi.** Disclaimer BRD mein bhi hai.
- "Regulator ki limits lagu hain." Concentration limits abhi placeholder hain; screen khud likhti hai ke tasdeeq-shuda nahi.

**Sawal jo log pooch sakte hain:**
| Sawal | Seedha jawab |
|---|---|
| Kya yeh asli paisa hilata hai? | Nahi. Settlement abhi insaan bank portal par karta hai; system hisaab, manzoori aur saboot sambhalta hai |
| Ghalti ho jaye to? | Signed hisaab badalta nahi; reversal aur nayi run, dono par naye manzoori |
| Shariah ki manzoori kaun deta hai? | Shariah Board, do tihai quorum se; system sirf record aur lagu karta hai |
| Agar AI ghalat jawab de? | AI kabhi khud kuch post/manzoor nahi karta; jawab hawale ke saath, aur har ek par insaan ka faisla darj |
| Ek hi insan sab kuch kar le to? | Nahi: maker, checker, Shariah reviewer, signatory alag alag zaroori |
| Dusra tenant ka data? | Alag; har tenant ka data aapas mein nazar nahi aata (test se saabit) |

## Hissa 9: Agar kuch kaam na kare

| Masla | Wajah / hal |
|---|---|
| Login par "connection refused" | Backend (8000) ya frontend (5173) band hai: Hissa 6 se dobara chalayein |
| AI screens "unavailable"/503 | Copilot (8001) band hai, ya demo data seed nahi hua: copilot chalayein, `seed_project_data` chalayein |
| Bohot saare logins par "too many attempts" | Login throttle: backend ko `AUTH_THROTTLE_RATE=1000/min` ke saath chalayein |
| Koi screen khaali/ajeeb | `seed_project_data` se demo taaza karein, phir dobara |
| Kisi step par aisa paigham jo samajh na aaye | Screenshot lein; paigham aam tor par wajah batata hai (jaise "ek aur approver chahiye") |

Teknikal tafseel (agar kabhi chahiye): `docs/DEPLOYMENT.md` (chalana aur taiyaari), `docs/DECISIONS.md` (jo faislay hum ne liye aur jo logon ko confirm karne hain),
`docs/UAT_CHECKLIST.md` (rolewar test jadwal), `audit_reports/MASTER_AUDIT_REPORT.md` (audit ka nateeja).
