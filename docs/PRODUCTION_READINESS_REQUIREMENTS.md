# Production readiness tak ki requirements

Maujooda halat (2026-10-15): BRD ke 186 requirements mein PASS 104, PARTIAL 61, MISSING 9, NOT TESTED 4, BLOCKED 6, N/A 2. Backend 485 tests, audit 42 tests pass. Faisla: **NOT READY for production**. Yeh file batati hai ke "READY" kehne ke liye kya kya chahiye, kis tarteeb mein, kaun karega, aur kab kaam "poora" mana jayega.

Effort ke andaze `audit_reports/IMPLEMENTATION_ROADMAP.md` se hain; paise ke andaze pichli list se (andaza, quote nahi). Jin cheezon ka faisla koi aur karta hai (bank, Shariah Board, accountant) unka owner wahi likha hai.

## Gate 0: Faislay jo code se pehle chahiye (1-3 hafte, sirf logon ka waqt)
| ID | Faisla | Kaun | Kis cheez ko unblock karta hai |
|---|---|---|---|
| D-1 | Accounting policy: accrual vs realization, posting calendar, income/expense/purification journals ke debit-credit | Bank ka accountant / CFO | R-045, R-122, R-123, R-125, R-028 |
| D-2 | Reserve (PER/IRR) se loss cover karna: kab, kitna, kaun approve kare | Shariah Board | R-087 ka baqi hissa |
| D-3 | Back-dated entry: adjustment period kaise bane | Finance + auditor | R-096 |
| D-4 | Circle: guarantee (kafala) ka model, Wakalah fee ka tareeqa, payment mandates | Shariah Board + product | R-031, R-074, R-076, R-009 |
| D-5 | Tolerance numbers (fairness, residual, prior-period, negative-yield) | Finance + Risk | R-065 |
| D-6 | Tax, Zakat, retention sign-off | Tax / legal | R-158, rule pack |
| D-7 | Regulator ki taraf se kaun se returns/formats chahiye | Compliance | R-035, R-144 |
| D-8 | Pilot bank / partner aur pilot ka daira (ek bank pool, manual settlement) | Management | Gate 3 |

Exit: har faisla likhit, `docs/DECISIONS.md` mein darj.

## Gate 1: Baqi code (4-8 hafte, ek ya do developers)
**A. Moali nizam (D-1 ke baad)**
1. Income/expense event aur purification ke journals; accrual policy object; posting calendar (R-045, R-122, R-123, R-125).
2. Back-dated entry ka adjustment period (R-096, D-3).
3. Reserve release for loss (R-087, D-2) agar Board manzoor kare.
4. Fairness / tolerance / prior-period / negative-yield tests aur golden examples (R-065, R-178, R-179).

**B. Circles (D-4 ke baad)**
5. Guarantees aur payment mandates; Wakalah model; closure par surplus/shortfall journal (R-031, R-074, R-076, R-080).

**C. Shariah aur governance**
6. Policy mapping, exception SLA timer, Contract Studio ke mandatory parameters enforce (R-032, R-044, R-024, R-048).
7. Asset transfer valuation aur ring-fencing ki tamiri (R-027, R-041).

**D. AI**
8. Model inventory (owner, validation, retirement) aur metrics: drift, bias, override, false-positive (R-115, R-117, R-120).
9. Urdu/Arabic disclosure generation signed run se (R-111).
10. AI red-team dobara, documents ingest karne ke baad (R-185); hallucination aur drift suite.

**E. Platform**
11. Super Admin feature flags aur encryption-key control (R-013).
12. Privacy: DSAR, retention enforcement (R-158).
13. Regulatory return formats aur examiner data room (R-035, R-144).
14. Metrics, traces, alerts, lineage (R-162).
15. WCAG 2.2 AA ka poora audit, Arabic UI aur RTL review (R-160, R-161).
16. Circle roster par "Link login" UI aur khali-system se baqi workflows (Investment, Circle, GL, period close) ka end-to-end test.

Exit: matrix mein FAIL 0, MISSING sirf wahi jo integrations hain, NOT TESTED 0; saare suites (backend, audit, Playwright) green.

## Gate 2: Infrastructure aur security (3-6 hafte, parallel)
| Kaam | Dev effort | Saboot jo chahiye |
|---|---|---|
| Production hosting, multi-zone HA, worker queue, load test (R-154, R-155) | 15-25 din | 99.9% ka measurement, P95 < 2 s, million-account load report |
| PostgreSQL WAL archiving + encrypted backups + **restore drill** (R-159) | 3-5 din | RPO 15 min, RTO 4 ghante ka timed drill |
| SSO, secrets vault, WAF/EDR (R-156) | 8-12 din | config evidence |
| Monitoring aur alerting (R-162) | 5-8 din | alert test |
| External penetration test (R-182) | 2-4 hafte vendor | report aur sab High/Critical band |
| Disaster recovery drill | 2-3 din | likhit report |

Exit: pen test ke High/Critical band, restore drill pass, HA load test pass.

## Gate 3: Integrations (6-12 hafte, bank par depend; pilot se pehle zaroori nahi)
Pehle pilot **manual settlement** par ho sakta hai (roadmap ka rasta). Integrations ke liye har ek ko bank ki specification, test environment aur certification chahiye.

| Integration | BRD | Effort | Dependency |
|---|---|---|---|
| Core banking (balances, GL) | R-136, R-137 | 20+ din | bank API/SFTP |
| Payment rails Raast / 1LINK | R-139 | 20+ din | bank, 1LINK certification |
| KYC / AML (NADRA Verisys, sanctions) | R-138 | 20+ din | vendor accounts |
| E-signature | R-141, R-067 | 5-8 din | vendor |
| SMS / email | R-142 | 2-3 din | vendor |
| Market data, BI | R-140, R-143 | baad mein | P3 |

Exit: har integration par bank ke test environment mein end-to-end run, reconciliation 0 difference.

## Gate 4: Pilot, UAT, parallel run (calendar time, 3-6 mahine)
| Qadam | Kaun | Saboot |
|---|---|---|
| Shariah Board UAT (`docs/UAT_CHECKLIST.md`) | Board | likhit approval (R-183) |
| Finance parallel run, **do periods**, purane system ke muqable | Finance team | difference report, 0 unexplained (R-184) |
| Pilot bank pool live (R-173) | bank | ek poora period signed run |
| Phir investment pool pilot (R-175) aur circle pilot (R-176) | bank | har ek ka ek period |
| Independent reperformance: spreadsheet se hisab ka milan | auditor | R-179 |

Exit: dono sign-offs (Shariah, Finance), pilot ka ek period bina P1 incident.

## Gate 5: Go-live ki tayyari
- Runbook aur on-call, incident aur rollback plan.
- Training: har role ke liye (is repo ke guides se).
- Data migration plan aur cut-over rehearsal.
- Regulator / SBP ko pehle se itla'a jahan lazmi ho.
- Final Go/No-Go meeting: Shariah, Finance, Risk, Security, Management ke dastakhat.

## Kul timeline (mojooda andaza)
| Marhala | Muddat |
|---|---|
| Gate 0 faislay | 1-3 hafte |
| Gate 1 code + Gate 2 infra (parallel) | 6-10 hafte |
| Gate 3 integrations (pilot ke baad bhi ho sakte hain) | 6-12 hafte |
| Gate 4 pilot, UAT, parallel run | 3-6 mahine |
| **Production Go-live** | **lagbhag 6-9 mahine**, bank ke sahyog par bohat depend |

Sab se bara risk code nahi, log hain: bank ki specs, Shariah Board ka waqt, finance ka parallel run.

## "READY" ki tareef (aakhri checklist)
- [ ] Gate 0 ke saare faislay likhit
- [ ] Gate 1 pura, saare suites green, FAIL/MISSING/NOT TESTED = 0 (integrations ke ilawa)
- [ ] Pen test: koi High/Critical open nahi
- [ ] Restore drill aur HA load test pass
- [ ] Shariah Board aur Finance ke likhit sign-offs
- [ ] Do periods ka parallel run, koi unexplained difference nahi
- [ ] Pilot ka ek period live
- [ ] Runbook, training, rollback tayyar
- [ ] Final Go/No-Go par dastakhat
