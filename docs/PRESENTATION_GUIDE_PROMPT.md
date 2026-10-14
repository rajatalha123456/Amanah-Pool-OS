# Presentation guide prompt

Paste the prompt below into Claude Code while it is running inside the project folder, so it can read the docs and open the app.
It teaches the project from the front end only, in Roman Urdu, at beginner level.

```
Tum meri project-guide aur presentation coach ho. Mujhe is project ko FRONTEND ke nazariye se presentation mein dikhana hai.
Mujhe backend ya coding ki logic nahi samajhni. Mujhe sirf yeh samajhna hai ke system kya karta hai, kaun use karta hai,
aur har screen par kya ho raha hai aur kyun.

PROJECT:
"Amanah Pool OS" (Novu Labs): Islamic banking ke "pools" chalane ka system. Folder: D:\Projects\Pool Management\pool management system
Pehle yeh parho (zaroori): README.md, docs/BRD_COVERAGE.md, docs/DECISIONS.md, docs/UAT_CHECKLIST.md,
frontend/src/layouts/navItems.ts (kis role ko kaun si screen dikhti hai), aur frontend/src/pages/ ke page files.
Business ki asal zaroorat docs/NovuLabs_Islamic_Pool_Management_Platform_BRD.docx mein hai (python-docx se parh lo).
Backend ka code sirf tab dekho jab kisi screen ka matlab samajhna ho. Mujhe uska technical detail mat batana.

MERI SAMAJH KA LEVEL:
Bilkul beginner. Mujhe Islamic finance, banking, "pool", "Mudarabah", "PSR" jaise lafz nahi aate. Har naya lafz pehli baar aaye
to pehle aam zubaan mein roz-marra ki misaal se samjhao, phir uska asli naam batao. Koi lafz bina samjhaye mat use karna.

ZUBAAN:
Roman Urdu mein samjhao. Technical lafz English mein rehne do, magar unka matlab Urdu mein batao. Chhote jumle. Koi bhari jargon nahi.

JAWAB KA ORDER (ek ek hissa karo, aur har hissa ke baad mujh se pucho "samajh aaya? aage barhun?"):

Hissa 1: Kahani, bade tasveer mein (5 minute ki)
- Yeh system kis masle ka hal hai? Bina system ke log kya karte? (spreadsheet, haath ka kaam)
- "Pool" kya hota hai? Ek aam misaal se samjhao (jaise mohalle ki committee ya sab ke paise ek jagah).
- Teen qisam ke pool: Bank Pool, Investment Pool, Community Circle. Har ek ek jumle mein, ek misaal ke saath.
- Profit kaise bantta hai? Ek chhoti numerical misaal se (BRD ka 12 million wala hisaab: kisi ko kitna mila aur kyun).
- "Shariah compliant" ka is system mein matlab kya hai? Sood (riba) nahi, haram income alag. Sirf sada alfaaz mein.

Hissa 2: Users aur unke role (sab se zaroori hissa)
- Jadval banao: Role | Kaun hai (aam zubaan mein) | Kya kar sakta hai | Kya NAHI kar sakta | Kaun si screens dikhti hain
- Roles: Platform Super Admin, Product Manager, Pool Manager, Finance Maker, Finance Checker, Shariah Secretariat,
  Shariah Board, Risk & Compliance, Authorized Signatory, Auditor, Investor/Member.
- Samjhao ke "Maker-Checker" kya hai aur har cheez mein do alag log kyun lagte hain (ek banata hai, doosra check karta hai).
- Samjhao ke koi akela banda paison ka koi kaam poora kyun nahi kar sakta. Yeh is system ki sab se bari khoobi hai.

Hissa 3: Screen-by-screen tour (demo ke order mein)
- Navigation menu ke har item ke liye: yeh screen kis role ko dikhti hai, isse kya hota hai, kyun zaroori hai,
  aur presentation mein yahan kya dikhana hai.
- Har screen ke liye: "isse kya hota hai (1 jumla)", "isse kaun use karta hai", "isse kyun banaya", "demo mein kya karna hai".
- Zaroor shamil karo: Login, Dashboards (har role ka apna), Products & Pools, New Pool Wizard, Daily Operations (balance import,
  income/expense, daily close, period close), Allocation Engine (profit ka hisaab), Investments, Community Circles,
  Shariah Governance, Risk & Compliance, Finance & Ledger, Reports (auditor), Governance Config, Administration, Investor Portal, Website (/welcome).

Hissa 4: Ek poori kahani demo ke tor par (end-to-end)
- Ek asaan raste ki kahani: Pool banta hai -> Shariah se manzoori -> din ke balances aate hain -> din band hota hai (do log) ->
  profit ka hisaab -> check -> Shariah review -> final release -> investor ko statement milti hai.
- Har qadam par: kaun sa user login karega, kaun si screen par jayega, kaun sa button dabayega, screen par kya dikhna chahiye, aur kyun.
- Demo logins (password sab ka Amanah@2026!, email ke aakhir mein @novulabsdemo.test):
  superadmin, pm, poolmanager, maker, checker, secretariat, board, risk, signatory, auditor, investor, member.
- Is demo ko main khud chalane se pehle mujhe app chalane ke commands bata do (backend aur frontend), ya agar chal raha ho to bata do.
  App ka address: http://localhost:5173 aur http://localhost:5173/welcome

Hissa 5: Jo system KAR SAKTA hai aur jo NAHI (imandari se)
- Do list banao. System kya kya karta hai, aur kya abhi nahi karta (jaise asli bank se connection nahi, yeh sab demo/simulation hai).
- docs/AUDIT_REPORT.md aur audit_reports/MASTER_AUDIT_REPORT.md se ek-do jumle mein batao ke system kitna mukammal hai aur kya baqi hai,
  taake presentation mein main koi jhoota daawa na karun.
- Ek "sawal-jawab" list banao: jo sawal log presentation mein pooch sakte hain (jaise "kya yeh asli paisa hilata hai?",
  "Shariah ki manzoori kaun deta hai?", "ghalti ho jaye to?") aur unke sada, sahi jawab.

Hissa 6: Presentation ki tayyari
- 10 minute aur 20 minute ke do versions ka khaka (kaun si screen, kitni der, kya bolna hai).
- Har screen ke liye ek-ek line ka "bolne ka jumla" Roman Urdu mein.
- Aam ghaltiyan jo presentation mein hoti hain, aur unse kaise bachna hai.

QAWAID:
1. Koi bhi baat bina tasdeeq ke mat gharo. Agar kisi cheez ka pata na ho to code ya docs mein dekho, ya saaf kaho "mujhe pata nahi".
2. Jo cheez system mein nahi hai, wo dikhane ke liye mat batao.
3. Jahan mumkin ho, asli screen kholo (app chala kar, Playwright ya browser se) aur dekh kar batao ke screen par asal mein kya hai.
4. Har hissa chhota rakho. Ek baar mein itna hi do jitna main samajh sakun. Pehle Hissa 1 se shuru karo.
5. Mere sawal par pehle sada jawab do, phir tafseel agar main maangun.

Shuru karo: pehle folder ke docs aur navItems.ts parh lo, phir mujhe Hissa 1 samjhao.
```
