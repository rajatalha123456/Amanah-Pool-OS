# Amanah Pool OS: kis se kya poochna hai

System ka code BRD ke mutabiq taqreeban 78% sabit ho chuka hai (184 mein se 143 requirements). Baqi kaam ka bara hissa
**faislon aur maloomat** par ruka hai jo sirf mutalliqa log de sakte hain. Neeche har shakhs ke liye sawal hain, har sawal
ke saath:
- **Kyun:** yeh kis liye chahiye
- **Abhi system mein:** abhi kya rakha hua hai (taake woh "haan / nahi / yeh badlo" keh sakein)
- **BRD:** kaun si requirement khulegi

Jawab likh kar aayein to main unke mutabiq code aur settings bana dunga. Jahan system mein "default" likha hai, woh
**mera rakha hua andaza** hai, kisi ki manzoori nahi.

---

## 1. Shariah Board / Shariah Advisor
*(Shariah Board ke members ya bank ke Shariah Advisor. Secretariat meeting rakh sakta hai.)*

**1.1 Reserve (PER / IRR) se nuqsan poora karna**
- Kyun: agar kisi mahine pool ko nuqsan ho to kya PER / IRR reserve se nuqsan ka kuch hissa poora kiya ja sakta hai?
- Abhi system mein: reserve sirf jama hota hai; nuqsan mein reserve se paisa **nahi** nikalta, nuqsan seedha depositors par jata hai.
- Poochna hai: (a) Ijazat hai ya nahi? (b) Agar hai to kis reserve se (sirf IRR ya PER bhi)? (c) Kitni had tak (poora nuqsan ya kuch %)? (d) Kaun manzoor karega (Board har dafa, ya pehle se policy)? (e) Depositors ko kaise bataya jaye?
- BRD: R-087

**1.2 Exception (Shariah masle) ki time limits**
- Kyun: koi Shariah masla saamne aaye to kitne din mein faisla hona chahiye.
- Abhi system mein (mera andaza): critical 1 din, high 3 din, medium 7 din, low 14 din.
- Poochna hai: yeh din theek hain ya badalne hain? Time guzarne par kis ko itla'a jaye?
- BRD: R-044

**1.3 Ijarah aur Diminishing Musharakah assets**
- Kyun: abhi system sirf asset ki "type" likhta hai; in contracts ki tafseel nahi.
- Poochna hai: (a) Ijarah ka kiraya kab pool ki aamdani maana jaye (har mahine due hone par, ya wasool hone par)? (b) Asset ka takaful aur maintenance kis ke zimme (bank ya customer)? (c) Diminishing Musharakah mein customer ke units khareedne ka hisaab kis tarah ho, aur us hisse ka munafa kis ko jaye? (d) Asset kharab / tabah ho jaye to kya?
- BRD: R-007

**1.4 Qawaid ki tarteeb (rule hierarchy)**
- Kyun: BRD kehta hai: qanoon/regulator → manzoor shuda standards → Board ke faislay → contract → procedure. Takraao ho to pool na khule.
- Poochna hai: (a) Kaun se standards adopt kiye hain (AAOIFI ke kaun se, SBP ke kaun se circulars)? (b) Agar Board ka faisla kisi standard se mukhtalif ho to kis ko tarjeeh?
- BRD: R-097

**1.5 Contract ke laazmi parameters**
- Abhi system mein (BRD Section 5 se): Mudarabah: Rab-ul-Maal, Mudarib, profit ratio, loss clause. Musharakah: partners, profit ratio, loss clause. Wakalah: principal, agent, Wakalah fee, loss clause. Qard: parties, late payment policy.
- Poochna hai: yeh list theek hai? Kuch aur laazmi hona chahiye (jaise dispute resolution, purification clause, early termination)?
- BRD: R-048 (confirm)

**1.6 Community circle (committee)**
- (a) Wakalah model mein organizer fixed fee le sakta hai? Had kya ho? Abhi system mein: fixed fee har payout par, aik contribution se kam.
- (b) Guarantor (zamin) bina fees ke: theek hai? Guarantor ki zimmedari kya hogi agar member default kare?
- (c) Qisht der se aaye to kuch lena jaiz hai (jaise charity mein dena), ya bilkul kuch nahi? Abhi system mein: kuch nahi, sirf reminder aur hardship.
- BRD: R-074, R-031, R-076 (confirm)

**1.7 Purification (na-jaiz aamdani)**
- (a) Kaun si charity / idaray manzoor hain jinhein purification ka paisa diya ja sakta hai?
- (b) Kitne arse mein dena zaroori hai (har mahine, har saal)?
- (c) Saboot kya rakhna hai (receipt, bank transfer)?

**1.8 Board ka quorum aur delegation**
- Abhi system mein: Board ke 2/3 members (kam az kam 2) approve karein tab faisla. Secretariat sirf draft karta hai.
- Poochna hai: Board ke kitne members hain aur kaun? Kya kuch chhote faislay Secretariat ko "delegate" kiye ja sakte hain (BRD: "no final ruling unless delegated")?

**1.9 Hiba (bank ka apne hissay mein se depositors ko dena)**
- Poochna hai: kab aur kitna jaiz hai, aur kaun manzoor kare?

**1.10 AI Copilot ke documents**
- Kyun: Copilot sirf manzoor shuda documents se jawab deta hai, har jawab ke saath hawala.
- Poochna hai: kaun se fatwe, standards aur policies is mein daalein? Inki soft copies (PDF) chahiye. Kya Board AI ke jawab test karne ke liye kuch sawal de sakta hai?
- BRD: R-119, R-185

**1.11 Shariah UAT (test aur likhit manzoori)**
- Poochna hai: Board kab system test kar sakta hai (`docs/UAT_CHECKLIST.md` tayyar hai)? Aakhir mein likhit approval kaun dega?
- BRD: R-183

---

## 2. CFO / Chief Accountant / Finance Controller
*(Bank ke finance department ka head, ya jo GL aur month-end close dekhta hai.)*

**2.1 Chart of accounts (GL codes)**
- Kyun: system 18 "logical" khaate istemal karta hai; har ek ka bank ke GL mein asli code chahiye.
- Khaate: pool income, pool direct expense, distributable profit, PER reserve, IRR reserve, Mudarib payable, depositor payable, investor capital, investor profit payable, settlement receivable, redemption payable, rounding account, accrued income receivable, expense payable, non-permissible income clearing, charity payable, circle member payable, Wakalah fee income (aur provisions, suspense, pool cash, WHT/Zakat payable).
- Poochna hai: har ek ke liye GL code aur naam.

**2.2 Accrual aur realization**
- Abhi system mein: income/expense post hote hi accrual journal banta hai; paisa aane par checker "Received/Paid" karta hai to cash journal banta hai.
- Poochna hai: (a) Income roz accrue ho ya mahine ke aakhir mein? (b) Kaun si income sirf wasooli par maani jaye? (c) Yeh tareeqa bank ki accounting policy se milta hai?
- BRD: R-045, R-028

**2.3 Posting calendar**
- Poochna hai: kaun se din kaam ke hain (holidays ki list kahan se), roz ki cut-off time kya hai, month-end close kitne din mein hota hai?
- BRD: R-045

**2.4 Aamdani aur kharche ki categories**
- Abhi system mein: kharcha "direct" ya "overhead" hai, kuch alfaaz (salary, rent wagairah) dekh kar overhead maana jata hai.
- Poochna hai: bank ki manzoor shuda list do: kaun se kharche pool par daale ja sakte hain (direct) aur kaun se bank khud uthata hai.
- BRD: R-042

**2.5 Purani tareekh ki entries**
- Abhi system mein: band din ki entry ya to refuse hoti hai, ya "adjustment period" (aaj ki tareekh) mein jati hai aur asli tareekh record par rehti hai.
- Poochna hai: yeh tareeqa theek hai?
- BRD: R-096 (confirm)

**2.6 Rounding aur tolerance**
- Abhi system mein: hisaab poori precision mein, aakhir mein 2 decimal; bacha hua paisa "rounding account" mein; ek run mein had ~1 paisa per line.
- Poochna hai: theek hai? Pichhle mahine ke muqable mein munafa kitna badle to "alert" dena chahiye (abhi sirf dikhata hai, koi had nahi)? Anomaly check abhi 40% farq par alert deta hai: theek hai?
- BRD: R-065, R-058 (confirm)

**2.7 Tax aur Zakat** *(tax advisor ke saath)*
- Poochna hai: filer aur non-filer ki withholding tax rate kya hai (abhi training mein 15% / 30%)? Zakat source par kaatni hai ya nahi? Kis ko exemption milti hai?

**2.8 Parallel run aur hisaab ka milan**
- Kyun: BRD kehta hai do periods purane system ke saath saath chalein, aur hisaab independent spreadsheet se milaya jaye.
- Poochna hai: (a) Kaun se do mahine? (b) Purane system ke nateeje (statements, journals) mil sakte hain? (c) Finance ki apni Excel workbook jis se hum hisaab milayein?
- BRD: R-184, R-179

**2.9 GL ko bhejne ka format**
- Poochna hai: bank ka ERP / GL kis file format mein journals leta hai (CSV, Excel, API)? Columns kya hon?
- BRD: R-137

**2.10 Settlement account**
- Poochna hai: payouts kis bank account se jayenge, aur uska balance system ko kaise milega (abhi ek setting mein haath se likha jata hai)?

---

## 3. Risk & Compliance Head
*(Bank ka risk / compliance head, ya Chief Compliance Officer.)*

**3.1 Concentration limits**
- Abhi system mein (andaza, "unconfirmed" likha hua): single obligor, connected group, real estate sector, top-5 obligors, related party ke liye default % limits.
- Poochna hai: har limit ki asli value, aur kaun si SBP ki hai aur kaun si bank ki apni.
- BRD: R-041, R-150

**3.2 Liquidity buffer**
- Poochna hai: pool mein kam az kam kitna naqd (liquid) rakhna zaroori hai?

**3.3 Regulator ki reports**
- Kyun: system mein abhi regulator ke formats nahi.
- Poochna hai: SBP ko kaun si reports kis format aur kitne arse mein bhejni hain (pool management, profit distribution, etc.)? Examiner ko kya data dena hota hai?
- BRD: R-035, R-144

**3.4 KYC / KYB**
- Poochna hai: individual aur company ke liye kaun se documents zaroori hain? KYC ke "tiers" kya hain? AML screening kis service se hoti hai?
- BRD: R-138 (aur bank IT ke saath)

**3.5 Data residency aur retention**
- Poochna hai: data sirf Pakistan mein rehna zaroori hai? Kaun sa data kitne saal rakhna hai (statements, journals, KYC, audit log)?
- BRD: R-158

**3.6 Regulator ki manzoor shuda misaalein**
- Poochna hai: SBP / Shariah audit ke paas profit distribution ki koi solved misaalein hain jin se hum system ka hisaab test karein?
- BRD: R-178

**3.7 Penetration test**
- Poochna hai: bank ka approved pen-test vendor kaun hai, aur scope kya hoga?
- BRD: R-182

---

## 4. Bank ka IT / Core Banking / Operations team
*(Head of IT, core banking team, payments team, information security.)*

**4.1 Core banking se data**
- Poochna hai: rozana account balances, naye accounts, financing assets aur unki aamdani hum tak kaise aayegi: API, SFTP file ya kuch aur? Specification document aur test environment.
- BRD: R-136, R-054, R-057

**4.2 Payments (Raast / 1LINK)**
- Poochna hai: profit payouts aur circle payouts ke liye Raast / 1LINK ka access, message format, aur certification ka tareeqa.
- BRD: R-139

**4.3 KYC / AML services**
- Poochna hai: NADRA Verisys aur sanctions screening ke liye bank kaun sa service / API istemal karta hai?
- BRD: R-138

**4.4 Doosri services**
- E-signature provider (investor contracts) – R-141
- SMS / WhatsApp gateway (customers ko itla'a) – R-142
- Market data (benchmarks, FX) – R-140
- BI / data warehouse – R-143

**4.5 Security**
- Poochna hai: (a) Login ke liye bank ka SSO (Active Directory / Azure AD)? (b) Encryption keys ka KMS / HSM? (c) WAF aur endpoint security?
- BRD: R-156, R-013

**4.6 Hosting**
- Poochna hai: production kahan chalega (bank ka data center ya cloud, kaun sa region)? High availability (2 zones), backup aur restore drill kaun karega?
- BRD: R-154, R-155, R-159

---

## 5. Management / Product Owner (aap khud ya Chairman)

**5.1 Pilot**
- Kaun sa bank ya partner pilot karega? Pehle kaun sa pool (BRD ka mashwara: aik Mudarabah deposit pool)? Investment pool aur circle ka pilot kab aur kis ke saath?
- BRD: R-173, R-175, R-176

**5.2 Har role ke liye naam**
- BRD 19 kehta hai configuration se pehle har role ka banda tay ho: Shariah advisor / Board, finance checker, risk reviewer, product owner, authorized signatory.

**5.3 Timeline aur budget**
- Integrations aur infrastructure ka budget aur ko'i target date.

**5.4 Translation**
- Urdu aur Arabic screens aur statements kis se check karwani hain (native speaker)?
- BRD: R-161

---

## Jawab aane ke baad
Har jawab mujhe bhej dein (seedha text, ya document). Main:
1. faislay system ki settings ya code mein daalunga,
2. har tabdeeli ka test likhunga,
3. BRD matrix mein us requirement ko update karunga.
