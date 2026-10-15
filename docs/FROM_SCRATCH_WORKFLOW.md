# Khali system se poori workflow: kaun kya karega, kis tarteeb mein

Yeh guide ek **bilkul khali database** se shuru hoti hai. Har qadam mein likha hai: kaun sa user, kaun si screen/tab, kya bharna hai, aur kya nazar aana chahiye. Bank-pool wali tarteeb (Hissa 0 se Hissa 6) `backend/apps/core/test_from_scratch.py` mein **code se chala kar verify** ki gayi hai (tenant khali, har qadam ka role, aur har "yeh role nahi kar sakta" wala qadam bhi refuse hota hai). Hissa 7, 8, 9 (GL/period close, Circle, Investment pool) bhi ab khali system se API par verify ho chuke hain. Ab sab flows verify hain.

## Hissa 0: Database saaf karna

```
cd backend
python manage.py bootstrap_clean_tenant --flush --yes                # sirf superadmin
python manage.py bootstrap_clean_tenant --flush --yes --with-users   # superadmin + 11 role logins (khali system)
```

Password dono mein `Amanah@2026!`, domain `novutest.test` (`--domain` se badal sakte hain). Demo wapas chahiye to `python manage.py seed_project_data`. Servers: backend 8000, frontend 5173 (copilot 8001 sirf AI ke liye).

Agar `--with-users` na lagayein to saare users **Hissa 1** se khud banane hain (har password sirf ek baar screen par dikhta hai, copy kar lein).

## Hissa 1: Superadmin: users banana
Login: `superadmin@novutest.test`. Menu mein sirf **Administration**.
- Tab **User Administration** → naya user: email, naam, role. System password khud banata hai, **sirf ek baar** dikhata hai.
- Zaroori roles: Product Manager, Pool Manager, Finance Maker, Finance Checker (kam az kam 2 ho to behtar), Shariah Secretariat, Shariah Board (kam az kam **3** members taake quorum 2/3 ban sake), Risk & Compliance, Authorized Signatory, Auditor.
- Investor/depositor ke login baad mein (Hissa 6) banenge.

## Hissa 2: Bunyadi qawaid (product se pehle)
1. **Risk & Compliance** → address bar mein `/jurisdiction-rule-packs` kholein (ya Superadmin → Administration → tab *Jurisdiction & Rule Packs*): *Jurisdiction rule pack* propose karein (code, version, effective date, ceilings: PER 5%, IRR 10%, Mudarib cap 40%, WHT filer 15% / non-filer 30%, wajah likhein). Yeh proposal hai, lagu nahi hota.
2. **Finance Checker** → pending *config change* ko **Approve** karein (proposer khud approve nahi kar sakta). Ab rule pack default hai.
3. **Approval matrix**: Risk teen qaidein propose kare: `allocation_release` (Authorized Signatory, limit), `distribution_approve` (Authorized Signatory), `payout_approve` (Finance Checker). Finance Checker har ek approve kare.
4. **Account mapping** (Governance Config → Account Mappings): Finance Maker har logical account (catalog mein jitne hain) ka GL code propose kare; Finance Checker approve kare. Iske baghair GL hand-over aur journal nahi chalte.

Nazar aana chahiye: teen approval rules, ek default rule pack, har catalog account ka GL code.

## Hissa 3: Shariah approval, phir product
1. **Shariah Secretariat** → Shariah Governance → Fatwa Register: naya *Shariah decision* (code, title, type "product approval", fiqh reference, caveats, effective date) draft karein. Secretariat khud vote nahi de sakta.
2. **Shariah Board** (member A, phir member B) → decision kholein → **Review & sign**: har member apna vote + notes deta hai. **Ek member kaafi nahi**; quorum (kam az kam 2, ya Board ka 2/3) poora hone par status `approved` hota hai. Ek member do baar vote nahi de sakta.
3. **Product Manager** → Products & Pools → **New product / contract template**: template banayein (type Mudarabah Unrestricted, upar wala decision jodein). PM apna template khud approve nahi kar sakta; **Board** approve karta hai.
4. **Product Manager**: product banayein (naam, code, operating model `bank_pool`, template, currency, eligible assets, minimum subscription) → **Submit for review**. **Board** product approve kare.

## Hissa 4: Pool banana aur kholna
1. **Pool Manager** → Products & Pools → **New pool** (wizard): approved product chunein, naam, code, legal entity, branch, timezone, calendar (daily / Mon–Fri / Sun–Thu), effective date.
2. Pool detail ka **Activation readiness** batata hai kya baaki hai ("PSR approved nahi", "weightages approved nahi"…).
3. **Pool Manager**: PSR schedule (depositor 70% / mudarib 30%) aur weightage bands (har participant class ke liye) propose kare. **Shariah Board** har ek ko approve kare (Pool Manager khud nahi kar sakta).
4. **Pool Manager**: *Submit for approval* → **Board** approve → **Finance Checker (ya Authorized Signatory)** pool ko **Open** kare. (Pool Manager khud open nahi kar sakta.) Status `open`.

## Hissa 5: Depositors, roz ka kaam, nafa ka run (bank pool)
1. **Pool Manager (ya Finance Maker)** → Participants → **New participant** (reference, naam, class jo weightage band se match kare, CNIC, IBAN, bank, tax status). Auditor yeh nahi kar sakta.
2. **Risk & Compliance** → Participants → **Verify** (KYC). Maker/PM verify nahi kar sakte. KYC verify hone tak balance import nahi hota.
3. Har participant par **Add account** (pool, account number, opened date). Account numbers tenant mein unique.
4. **Finance Maker** → Daily Operations → **Income & Expense**: income (jaise Financing Profit) aur expense (jaise Takaful) record karein. **Finance Checker** *Post* kare; Maker khud post nahi kar sakta. Post se pehle koi cheez nafe mein nahi gini jati.
5. Har din: **Balance Import** (account number + balance + control total) → **Daily Close**: Maker *prepare*, Finance Checker *sign*. Maker khud sign nahi kar sakta. Signed close ke baghair run check/release nahi hota.
6. **Finance Maker** → Allocation Engine: run banayein (pool, value date, period start). Simulator wahi hisab dikhata hai bina kuch likhe.
7. Ceremony, **chaar alag log**: Maker *Submit for checking* → **Finance Checker** *Check* (maker nahi) → **Shariah Secretariat/Board** *Shariah sign-off* (checker ke baad hi) → **Authorized Signatory** *Approve* (na maker, na checker). Har galat tarteeb/role refuse hota hai. Final status `signed`.
8. **Maker** → *Generate statements*.

## Hissa 6: Investor ko login dena
1. **Superadmin** → User Administration → role **Investor / member** ka user banayein (password ek baar).
2. **Pool Manager** → Participants → us participant par **Link login** → woh email dalein. Ek login sirf ek participant se jur sakta hai.
3. Us investor se login karein: home par Investor Portal, sirf apne accounts aur statements (`my-statements`).

## Hissa 7: GL, suspense, period close (code se khali system par verify hua)
1. **Finance Maker** → Finance & Ledger → *GL Hand-over*: pending batches dekhein, **Generate export**. **Finance Checker** (maker nahi) GL ka jawab record kare: **Confirm** (GL reference ke saath) ya Reject (wajah ke saath). Phir *Trial Balance*: debit = credit.
2. **Suspense**: Maker kisi na-mile paise ko propose kare (side: unidentified receipt / unexplained shortfall, amount, wajah, reference); Checker approve kare tab journal banta hai.
3. **Period close** (Daily Operations → Period Close & Locking): Pool Manager period banaye → *Auto-verify gates* → tarteeb se sign-offs: **Pool Manager** pehle, phir **Shariah reviewer** (Secretariat/Board; fatwa reference lazmi), phir **CFO checker** (Finance Checker). Teeno alag log. Phir **Finance Checker ya Authorized Signatory** *Lock ceremony*. Lock ke baad us period mein back-dated entry refuse hoti hai (restatement chahiye).

## Hissa 8: Community Circle (Qard), khali system se verify hua
1. **Secretariat** ruling draft → **Board A, B** quorum vote. 2. **PM** contract template (type Qard) → **Board** approve. 3. **PM** product (model *community_circle*) → review → **Board** approve. 4. **Pool Manager** pool banaye → submit → **Board** approve → **Finance Checker** open (circle ko PSR/weightage nahi chahiye).
5. **Pool Manager**: *Rules publish* (contribution amount, cycle days, pehli due date). 6. Har member: **Pool Manager** create → **Risk** KYC verify → **Pool Manager** rules acceptance record kare (dastakhat ka saboot). Member ko login dena ho to Member Roster par **Link login**.
7. **Draw**: Pool Manager *commit* (result chhupa hota hai) → *execute* (client seed ke saath); Auditor *verify* kar sakta hai.
8. **Contribution**: sirf **Finance Maker** record karta hai (bank/Raast ki payment reference lazmi). Pool Manager khud nahi kar sakta.
9. **Payout**: Pool Manager/Maker request (amount hamesha jama shuda pot ke barabar), **Finance Checker** approve (requester nahi), Maker/Checker *Settle*.
10. Teeno cycles ke baad **Closure**: Pool Manager *prepare* (jama = diya hua, farq 0), phir sirf **Finance Checker** *close* kar sakta hai.

## Hissa 9: Investment Pool (NAV), khali system se verify hua
1. Shariah ruling, template (Mudarabah), product (model *investment_pool*), pool, PSR (Board approve), open: bank pool jaisa hi (Hissa 3-4), weightage ki zaroorat nahi.
2. **Pool Manager** *Capital account* banaye; **Finance Maker** investor profile (ID, suitability); **Risk** KYC verify.
3. **Disclosure**: Pool Manager/PM *prepare*, **Risk ya Board** (doosra banda) *approve*, phir Maker/PM investor ka *acknowledge* record kare (in-person, risk acknowledged). Iske baghair subscription refuse.
4. **Pehla NAV**: nayi pool mein koi unit nahi, isliye Maker NAV screen par *Total Pool Asset Value = 0* aur **Opening price per unit** (jaise 10.00) bhare; **Finance Checker** publish kare. (Yeh option is dauran naya banaya gaya: pehle pehli subscription mumkin hi nahi thi.)
5. **Finance Maker** *Subscribe* (amount, date). Units NAV ke hisaab se milte hain.
6. Mahine ke aakhir mein: income event (Maker) → post (Checker); naya NAV (value ke saath); phir **Profit Distribution** ceremony: Maker run → Maker *submit* → Checker *check* → Shariah *sign-off* → Authorized Signatory *approve*.
7. **Redemption**: Finance Maker request (units, date), **Finance Checker** approve (maker nahi).

## Kaun kya NAHI kar sakta (jaldi check karne ke liye)
| Koshish | Nateeja |
|---|---|
| Maker apna income event post kare / daily close sign kare / run check kare | refuse |
| Secretariat vote de | refuse (sirf Board) |
| Ek Board member akela fatwa approve kare (Board mein 2+ ho) | refuse, quorum chahiye |
| PM apna template ya product approve kare | refuse |
| Pool Manager pool khud open kare ya PSR approve kare | refuse |
| Auditor koi bhi cheez banaye | refuse (read-only) |
| Shariah sign-off check se pehle, ya release sign-off se pehle | refuse |
| Release checker se / maker se | refuse |
