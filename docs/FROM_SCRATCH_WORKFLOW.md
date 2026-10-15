# Khali system se poori workflow: kaun kya karega, kis tarteeb mein

Yeh guide ek **bilkul khali database** se shuru hoti hai. Har qadam mein likha hai: kaun sa user, kaun si screen/tab, kya bharna hai, aur kya nazar aana chahiye. Bank-pool wali tarteeb (Hissa 0 se Hissa 6) `backend/apps/core/test_from_scratch.py` mein **code se chala kar verify** ki gayi hai (tenant khali, har qadam ka role, aur har "yeh role nahi kar sakta" wala qadam bhi refuse hota hai). Investment pool aur Circle wale hisse (Hissa 7, 8) abhi khali system se end-to-end verify **nahi** hue; woh `SYSTEM_GUIDE_AND_TEST_WALKTHROUGH.md` ke Test 8 aur Test 15 ke mutabiq chalein, aur jo ruke woh mujhe batayein.

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

## Hissa 7: GL, journal, period close
**Finance Maker/Checker** → Finance & Ledger: *Journal Batches* (run ke baad journal), *GL Hand-over & Trial Balance* (export banao → bank ka GL confirm kare → trial balance), *Suspense*. **Period Close** (Daily Operations) mahine ke akhir mein. Yeh hissa abhi sirf unit tests aur Test 10/11 se cover hai, khali system se end-to-end nahi.

## Hissa 8: Doosre models (abhi unverified from empty)
Investment pool (Investments: Investor Onboarding → Capital Accounts → Subscription → NAV → Profit Distribution) aur Community Circle (Circle Setup → Member Roster → Contributions → Draw → Payout Ceremony → Closure) ke liye `SYSTEM_GUIDE_AND_TEST_WALKTHROUGH.md` Test 8 aur 15 dekhein. Is dauran jo screen khali dikhe ya button gayab ho, woh batayein: wahi asli gap hai.

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
