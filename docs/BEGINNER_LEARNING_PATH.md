# Amanah Pool OS: shuru se seekhne ka rasta (beginner)

Yeh guide aik kahani ki tarah chalti hai. Hum aik naya bank (tenant "Novu Labs Training") lete hain jiske system mein **kuch bhi nahi**, aur wahi tarteeb follow karte hain jo asal zindagi mein hoti hai: pehle kaun aata hai, woh kya karta hai, phir kis ki baari aati hai.

Har qadam mein 5 cheezein hain:
- **Kaun:** kaun sa user (login)
- **Kyun:** yeh kaam kis liye hai (aam misaal ke saath)
- **Kahan:** kaun si screen / tab
- **Kya karna hai:** button aur fields
- **Kya dekhna hai:** sahi hua to kya nazar aayega, aur kya **nahi** hona chahiye

Logins: sab ka password `Amanah@2026!`, email `<naam>@novutest.test` (jaise `risk@novutest.test`).
System chalana: backend 8000, frontend `http://localhost:5173`.
Khali database dobara chahiye ho: `cd backend` phir `python manage.py bootstrap_clean_tenant --flush --yes --with-users`.

Seekhne ka tareeqa: har qadam pehle **parhein**, phir **khud karein**, phir "kya dekhna hai" check karein. Aik din mein 2-3 qadam kaafi hain.

---

## Qadam 0: Pehle poori tasveer samajh lein (sirf parhna hai)

**System kya karta hai?** Islamic bank logon ka paisa aik "pool" (hauz) mein jama karta hai, us paisay se halal karobar karta hai (jaise Murabaha: cheez khareed kar munafay par bechna), aur jo **munafa** hota hai woh **aik tay shuda hissay (ratio)** mein logon aur bank ke darmiyan baant'ta hai. Islam mein fixed sood (interest) nahi hota: munafa hoga to baanta jayega, nuqsan hoga to paisa lagane wale uthayenge (agar bank ki ghalti na ho).

**Teen qisam ke pool:**
| Pool | Aasan misaal |
|---|---|
| Bank pool (Mudarabah) | Aap ka savings account: bank aap ka paisa lagata hai, munafa mahine ke aakhir mein baant'ta hai |
| Investment pool (NAV) | Mutual fund jaisa: aap "units" khareedte hain, unit ki qeemat (NAV) upar neeche hoti hai |
| Community circle (Qard) | "Committee" / BC: har mahine sab paisa daalte hain, baari baari aik ko poori raqam milti hai, koi sood nahi |

**Sab se zaroori usool (poore system mein yahi baar baar dikhega):**
1. **Maker-checker (chaar aankhein):** jo banda kaam banata hai, woh khud usay approve nahi kar sakta. Hamesha doosra banda.
2. **Har role ka apna kaam:** har user ko sirf apni screens dikhti hain, aur server bhi doosre ka kaam refuse karta hai.
3. **Shariah pehle:** koi product, pool ya munafay ki taqseem Shariah Board ki manzoori ke baghair nahi chalti.
4. **Sab kuch record hota hai:** har click ka audit log banta hai jo baad mein badla nahi ja sakta.

**Zaroori lafz (yaad kar lein):**
| Lafz | Matlab |
|---|---|
| Tenant | Aik bank / company. Har tenant ka data alag, koi doosre ka nahi dekh sakta |
| Mudarib | Jo paisa chalata hai (bank) |
| Rab-ul-Maal | Jis ka paisa hai (depositor / investor) |
| PSR (Profit Sharing Ratio) | Munafa kis ratio mein baantna hai, jaise 70% logon ka, 30% bank ka |
| Weightage | Lambi muddat ke account ko zyada hissa: jaise savings 1.00, term deposit 1.25 |
| PER / IRR | Reserve: achhe mahinon mein thora munafa side par rakhna taake bure mahine mein kaam aaye |
| Daily close | Har din ke balance check karke "band" karna |
| Allocation run | Mahine ke aakhir mein munafay ka hisaab |
| NAV | Investment pool mein aik unit ki qeemat |
| KYC | Customer ki pehchaan check karna (CNIC, address) |
| GL | Bank ka main hisaab kitaab (General Ledger) |
| Journal | Hisaab ki entry: debit aur credit, dono barabar |

**Kirdaar (roles) aur unki zimmedari:**
| Login | Role | Aasan zubaan mein kaam |
|---|---|---|
| superadmin | Platform Administrator | Users banata hai, settings. Paison ka data nahi dekhta |
| risk | Risk & Compliance | Qawaid tay karta hai, KYC check karta hai |
| maker | Finance Maker | Hisaab ki entries banata hai |
| checker | Finance Checker | Maker ka kaam check karke approve karta hai |
| secretariat | Shariah Secretariat | Shariah faislay ka draft likhta hai |
| board, board2, board3 | Shariah Board | Shariah faislay par vote dete hain |
| pm | Product Manager | Product (scheme) design karta hai |
| poolmanager | Pool Manager | Pool chalata hai, customers register karta hai |
| signatory | Authorized Signatory | Aakhri dastakhat: paisa release |
| auditor | Auditor | Sirf dekhta hai, kuch badal nahi sakta |
| (baad mein banega) | Investor / member | Customer: sirf apna account dekhta hai |

---

## HISSA A: Bunyaad rakhna (koi product banne se pehle)

### Qadam 1: Superadmin: system mein log daakhil karna
- **Kaun:** `superadmin`
- **Kyun:** naye daftar mein pehle staff ko chaabiyan (login) dete hain. Superadmin sirf "HR / IT" hai, bank ka paisa nahi dekh sakta.
- **Kahan:** menu mein sirf **Administration** dikhega. Tabs: Security & Audit Log, Multi-Tenant Configuration, **User Administration**, Jurisdiction & Rule Packs, Feature Flags & Encryption Keys, Website Enquiries.
- **Kya karna hai:** User Administration kholein. Wahan 11 users pehle se bane hain (`--with-users` ki wajah se). Aik test user bana kar dekhein: email, naam, role (jaise Auditor). Password **sirf aik baar** dikhega.
- **Kya dekhna hai:** naya user list mein aa jaye. Security & Audit Log mein "create" ki entry ho. Superadmin ko Pools / Participants jaisi screens **nahi** dikhni chahiyein.

### Qadam 2: Risk: mulk ke qawaid (Rule Pack)
- **Kaun:** `risk` (ya superadmin) propose karta hai, `checker` approve.
- **Kyun:** har mulk ke apne qanoon hain: tax kitna katna hai (WHT), reserve ki hadd kya hai, bank zyada se zyada kitna hissa le sakta hai. Yeh "rule pack" poore system ka qaida-qanoon hai.
- **Kahan:** Risk: address bar mein `/jurisdiction-rule-packs` (superadmin: Administration → Jurisdiction & Rule Packs). Approve: checker → **Governance Config** → "Changes awaiting approval".
- **Kya karna hai:** "+ Add Custom Rule Pack": code `PK-RULES`, version `2026.01`, naam, date, JSON mein PER 5, IRR 10, Mudarib cap 40, WHT filer 15 / non-filer 30, aur wajah. "Propose" dabayein. Phir checker se login karke Approve.
- **Kya dekhna hai:** propose ke baad pack **lagu nahi** hota (sirf proposal). Approve ke baad "Default regulatory engine" mein PK-RULES. Jis ne propose kiya woh khud approve nahi kar sakta.
- **Seekh:** yahan aap ne pehli baar **maker-checker** dekha.

### Qadam 3: Risk: kaun kitni raqam tak manzoori de sakta hai (Approval Matrix)
- **Kaun:** `risk` propose, `checker` approve.
- **Kyun:** bank mein har afsar ki "signing limit" hoti hai. Jaise: profit release sirf Authorized Signatory, 50 crore tak.
- **Kahan:** Governance Config → Approval Matrix.
- **Kya karna hai:** 3 rules: `allocation_release` → Authorized Signatory → 500000000; `distribution_approve` → Authorized Signatory → 500000000; `payout_approve` → Finance Checker → 50000000. Har aik ki wajah. Phir checker approve kare.
- **Kya dekhna hai:** teeno "active". Baad mein koi aur role release karne ki koshish kare to system rokega.

### Qadam 4: Finance Maker: hisaab ke khaate jorna (Account Mapping)
- **Kaun:** `maker` propose, `checker` approve.
- **Kyun:** system ke andar "pool_income", "depositor_payable" jaise naam hain; bank ke main hisaab (GL) mein har khaate ka apna code hota hai (jaise 4001). Yeh dono ko jorta hai, taake entries bank ke GL mein sahi khaate mein jaayein.
- **Kahan:** Governance Config → Accounting Mapping. Peeli tags "… - unmapped" batati hain kya baaki hai.
- **Kya karna hai:** har logical account chunein, GL code (jaise 4001, 5001, 2001…) aur naam, wajah, "Propose mapping". Checker approve kare. Saare 12.
- **Kya dekhna hai:** saari peeli tags khatam. (Yeh training codes hain; asli bank ke codes baad mein.)

---

## HISSA B: Shariah manzoori aur product

### Qadam 5: Shariah Secretariat: faislay ka draft
- **Kaun:** `secretariat`
- **Kyun:** koi bhi scheme chalane se pehle Shariah Board likh kar kehta hai ke yeh jaiz hai. Secretariat "munshi" ki tarah draft tayyar karta hai, faisla nahi karta.
- **Kahan:** **Shariah Governance** → Fatwa Register.
- **Kya karna hai:** naya decision: code `FATWA-T-001`, title "Unrestricted Mudarabah deposit pool", type product approval, fiqh reference (AAOIFI Standard 13), caveat "Loss is borne by the capital providers", date.
- **Kya dekhna hai:** status `draft`. Secretariat ko vote ka option **nahi** milna chahiye.

### Qadam 6: Shariah Board: vote (quorum)
- **Kaun:** `board`, phir `board2`
- **Kyun:** aik aalim ka faisla kaafi nahi; Board ke kam az kam do tihai (2/3) members mutfiq hon. 3 members hain to 2 votes chahiye.
- **Kahan:** Shariah Governance → Fatwa Register → decision par **Review & sign** (ya Multi-Mufti Quorum tab).
- **Kya karna hai:** board se vote "approve" + notes. Phir logout, board2 se yahi.
- **Kya dekhna hai:** pehle vote ke baad bhi status `draft` (quorum poora nahi). Doosre vote ke baad `approved`. Aik member do baar vote nahi de sakta.

### Qadam 7: Product Manager: contract aur product
- **Kaun:** `pm` banata hai, `board` approve karta hai.
- **Kyun:** contract template = customer se hone wale muahide ki shakl; product = scheme (jaise "General Depositor Pool"). Dono ko Board ki manzoori chahiye.
- **Kahan:** **Products & Pools**.
- **Kya karna hai:** contract template (type Mudarabah Unrestricted, upar wala fatwa jorein). Is type ke **laazmi clauses** (★ wale) bharein: Rab-ul-Maal (kis ka paisa), Mudarib (kaun chalayega), profit ratio, loss bearing clause. Inke baghair Board approve nahi kar sakta. Phir Board se approve. Phir product: naam, code `GEN-DEP`, model **bank_pool**, template, PKR, eligible assets (Murabaha, Ijarah), minimum subscription → **Submit for review**. Board approve kare.
- **Kya dekhna hai:** PM apna kaam khud approve **nahi** kar sakta.

---

## HISSA C: Pool banana aur kholna

### Qadam 8: Pool Manager: pool banana
- **Kaun:** `poolmanager`
- **Kyun:** product aik "design" hai; pool asal hauz hai jis mein paisa aata hai (aik product ke kai pool ho sakte hain, jaise 2026 wala).
- **Kahan:** Products & Pools → **New pool** (wizard).
- **Kya karna hai:** approved product chunein, naam "General Depositor Pool 2026", code `GEN-2026`, legal entity, branch, timezone, calendar Mon–Fri, date.
- **Kya dekhna hai:** pool `draft` mein. Pool detail mein **Activation readiness** batayega kya baaki hai ("PSR approved nahi", "weightages approved nahi").

### Qadam 9: Pool Manager + Board: munafay ka ratio aur weightage
- **Kaun:** `poolmanager` propose, `board` approve.
- **Kyun:** PSR batata hai munafa kaise baantna hai (70% logon ka, 30% bank ka). Weightage batata hai kis qisam ke account ko kitna wazan (savings 1.00, term 1.25).
- **Kya karna hai:** PSR depositor 70 / mudarib 30. Weightage: class `savings` 1.00, `term` 1.25. Board har aik approve kare.
- **Kya dekhna hai:** Pool Manager khud approve nahi kar sakta. Readiness ki list chhoti hoti jaye.

### Qadam 10: Pool kholna
- **Kaun:** `poolmanager` submit → `board` approve → `checker` (ya signatory) **Open**.
- **Kyun:** dukaan kholne se pehle teen aankhen: chalane wala, Shariah, aur finance.
- **Kya dekhna hai:** status `open`. Pool Manager khud open **nahi** kar sakta.

---

## HISSA D: Customers aur roz ka kaam

### Qadam 11: Pool Manager: customers (depositors) register karna
- **Kaun:** `poolmanager` (ya maker)
- **Kahan:** **Participants** → **New participant**.
- **Kya karna hai:** do log banayein:
  - `CUS-001`, Aisha Depositor, class **savings**, CNIC, IBAN
  - `CUS-002`, Bilal Depositor, class **term**
  Phir har aik par **Add account**: pool GEN-2026, account `ACC-001` / `ACC-002`, opened 2026-01-01.
- **Kya dekhna hai:** KYC "pending". Class wahi likhein jo weightage mein hai, warna hisaab nahi banega.

### Qadam 12: Risk: KYC check
- **Kaun:** `risk` → Participants → **Verify**.
- **Kyun:** jab tak pehchaan check na ho, paisa nahi le sakte (anti money laundering).
- **Kya dekhna hai:** badge "verified". Maker / Pool Manager ko Verify button nahi milta.

### Qadam 13: Maker + Checker: pool ki aamdani aur kharcha
- **Kaun:** `maker` record, `checker` **Post**.
- **Kahan:** **Daily Operations** → Income & Expense (ya Finance & Ledger).
- **Kya karna hai:** income: "Financing Profit" 120,000 (date 2026-01-03). Expense: "Direct Takaful" 20,000.
- **Kya dekhna hai:** jab tak checker "post" na kare, yeh raqam munafay mein **nahi** gini jati.

### Qadam 14: Har din: balance import aur Daily Close
- **Kaun:** `maker` import + prepare, `checker` sign.
- **Kyun:** munafa "rozana balance" par baant'ta hai: jitne din jitna paisa raha, utna hissa. Isliye har din ka balance chahiye, aur din band (close) karna hota hai.
- **Kahan:** Daily Operations → **Balance Import**, phir **Daily Close**.
- **Kya karna hai:** 1 se 5 January, har din: ACC-001 = 1,000,000, ACC-002 = 500,000, control total 1,500,000. Phir prepare → checker sign.
- **Kya dekhna hai:** control total na mile to import rukega. Bina signed close ke mahine ka hisaab release nahi hota.

---

## HISSA E: Mahine ke aakhir mein munafay ki taqseem (sab se ahem)

### Qadam 15: Pehle hisaab samajh lein (misaal)
- Aamdani 120,000 − kharcha 20,000 = **100,000 baantne ke qabil munafa**
- PSR 70/30: logon ka hissa **70,000**, bank (mudarib) **30,000** (reserves set na hon to)
- Weightage ke saath wazan:
  - Aisha: 1,000,000 × 1.00 = 1,000,000
  - Bilal: 500,000 × 1.25 = 625,000
  - Kul = 1,625,000
- Aisha ko: 70,000 × 1,000,000 / 1,625,000 ≈ **43,077**
- Bilal ko: 70,000 × 625,000 / 1,625,000 ≈ **26,923**

(Asal system har din ka balance ginta hai; yahan saare din barabar maan kar seedha kiya hai.)

### Qadam 16: Simulator aur run
- **Kaun:** `maker`
- **Kahan:** **Allocation Engine** → Allocation Simulator.
- **Kya karna hai:** pool, value date 2026-01-05, period start 2026-01-01. Pehle **Simulate** (kuch save nahi hota, sirf dikhata hai), phir run banayein.
- **Kya dekhna hai:** upar wale numbers ke qareeb. Status `simulated`.

### Qadam 17: Chaar logon ki "ceremony"
| Tarteeb | Kaun | Button | Kya roka jata hai |
|---|---|---|---|
| 1 | maker | Submit for checking | — |
| 2 | checker | Check | maker khud check nahi kar sakta |
| 3 | secretariat ya board | Shariah sign-off | check se pehle nahi |
| 4 | signatory | Approve (release) | maker ya checker release nahi kar sakte |

- **Kya dekhna hai:** aakhir mein status `signed`. Journal khud ban jata hai. Phir maker **Generate statements**.
- **Seekh:** yeh poore system ka dil hai: aik paisa bhi chaar alag logon ki manzoori ke baghair nahi niklta.

### Qadam 18: Customer ko login dena
- **Kaun:** `superadmin` user banaye (role **Investor / member**, email jaise `cus001@novutest.test`), `poolmanager` Participants mein Aisha par **Link login**.
- **Kya dekhna hai:** Aisha ke login se sirf **Investor Portal**: apna account aur statement. Bilal ka kuch nazar nahi aana chahiye.

---

## HISSA F: Hisaab ko bank ke GL mein bhejna aur mahina band karna

### Qadam 19: GL Hand-over aur Trial Balance
- **Kaun:** `maker` export, `checker` confirm.
- **Kahan:** **Finance & Ledger** → GL Hand-over & Trial Balance.
- **Kya karna hai:** pending batches dekhein → Generate export → checker GL reference (jaise GL-001) ke saath Confirm. Phir Trial Balance.
- **Kya dekhna hai:** trial balance mein debit = credit.

### Qadam 20: Suspense (na-maloom paisa)
- **Kyun:** kabhi bank mein paisa aata hai par pata nahi kis ka. Usay "suspense" mein naam ke saath rakhte hain jab tak pata na chale.
- **Kya karna hai:** maker: side "unidentified receipt", 150, wajah, reference → checker approve.
- **Kya dekhna hai:** 30 din se purana ho jaye to Command Center par "control alert".

### Qadam 21: Period close (mahina band)
- **Kahan:** Daily Operations → Period Close & Locking.
- **Tarteeb:** poolmanager period banaye (Jan 1–31) → gates check → sign-off: **pool manager** pehle, phir **Shariah reviewer** (secretariat, fatwa reference ke saath), phir **CFO checker** (checker). Phir signatory **Lock**.
- **Kya dekhna hai:** lock ke baad January mein koi purani entry dalne ki koshish refuse hogi ("restatement chahiye").

---

## HISSA G: Investment pool (NAV) seekhna
Bunyaad wahi hai (fatwa → template → product → pool → PSR → open), bas product model **investment_pool**, aur weightage nahi.
1. **Capital account** (poolmanager) → investor profile (maker) → KYC (risk).
2. **Disclosure:** poolmanager tayyar kare, **risk ya board** approve, maker investor ki "acknowledgement" record kare. Iske baghair paisa nahi le sakte (customer ko khatre bataye bina nahi).
3. **Pehla NAV:** nayi pool mein koi unit nahi, isliye value 0 aur **opening price per unit** 10.00 (maker), checker publish.
4. **Subscribe** (maker): 100,000 → 10,000 units.
5. Mahine ke aakhir: income post, naya NAV, phir **Profit Distribution** wahi chaar logon ki ceremony.
6. **Redemption:** maker request, checker approve.

## HISSA H: Community circle (committee) seekhna
1. Fatwa (Qard), template type **qard**, product model **community_circle**, pool open (PSR nahi chahiye).
2. **Rules publish** (poolmanager): har mahine 10,000, 30 din ka cycle.
3. Members (poolmanager) → KYC (risk) → rules qabool karne ka saboot record.
4. **Draw:** commit (nateeja chhupa) → execute → auditor verify. Isse baari ki tarteeb insaaf se tay hoti hai.
5. Har cycle: maker sab ki contribution record kare (Raast reference ke saath) → jis ki baari hai uska payout: request → checker approve → settle. Payout hamesha **jitna jama hua utna** (3 × 10,000 = 30,000), aik paisa zyada nahi (sood nahi).
6. Teeno cycles ke baad **Closure:** prepare → checker close (farq 0).

## HISSA I: Nigrani wale kirdaar
- **Auditor:** har jagah dekh sakta hai (Reports, audit trail, evidence bundle), kuch badal nahi sakta. Koshish karein: koi bhi "Create" button nahi milna chahiye.
- **Risk & Compliance screen:** assets, provisions (qarz doobne ka khatra), exceptions, related-party, limits.
- **Exceptions:** kuch ghalat ho to case banta hai; paisa "quarantine", Board faisla, disclosure. Time limit guzre to alert.
- **AI & Analytics:** Shariah copilot sawal ka jawab **hawalay (citation)** ke saath deta hai; AI kabhi faisla, approval ya posting nahi karta, sirf mashwara.

---

## Seekhne ka schedule (mashwara)
| Din | Kya |
|---|---|
| 1 | Qadam 0 parhein, Qadam 1-4 karein |
| 2 | Qadam 5-10 (Shariah, product, pool) |
| 3 | Qadam 11-14 (customers, roz ka kaam) |
| 4 | Qadam 15-18 (munafa aur ceremony) |
| 5 | Qadam 19-21 (GL aur period close) |
| 6 | Hissa G (investment pool) |
| 7 | Hissa H (circle) aur Hissa I |

Har din ke aakhir mein khud se poochein: **"Aaj kis ne kya banaya, kis ne approve kiya, aur kis ko roka gaya?"** Agar yeh teen jawab aa gaye to aap ne woh hissa samajh liya.

Koi screen kaam na kare ya samajh na aaye to screenshot ke saath batayein. Mazeed tafseel: `FROM_SCRATCH_WORKFLOW.md` (tarteeb), `SCREEN_REFERENCE.md` (har screen).
