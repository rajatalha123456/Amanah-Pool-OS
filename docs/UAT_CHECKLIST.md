# User acceptance checklist

For the Shariah Board, Finance, Risk, Operations and the product owner. Each block is one role. A step passes only if what you
see matches "Expected". Record who tested, the date, and any step that failed, with a screenshot. Use a **demo database** (`seed_project_data`)
for the first round, then repeat the steps that matter on your own configured pools.

Demo logins (password `Amanah@2026!`, domain `@novulabsdemo.test`): `superadmin`, `pm` (product manager), `poolmanager`, `maker`,
`checker`, `secretariat`, `board`, `board2`, `board3`, `risk`, `signatory`, `auditor`, `investor`, `member`,
`mudarabah.investor@novulabsdemo.test`.

## A. Everyone
| # | Step | Expected |
|---|---|---|
| A1 | Open the site address, then sign in with a wrong password | You see the website first; a wrong password is refused with a clear message; after several wrong tries sign-in is throttled |
| A2 | Sign in, open the bell | Only your own notifications |
| A3 | Open the menu | Only the areas of your role (compare with the table in section K) |
| A4 | Type the address of a screen that is not in your menu | You are sent back to your home screen |

## B. Platform administrator (`superadmin`)
| # | Step | Expected |
|---|---|---|
| B1 | Sign in | Lands on Administration, no financial screens in the menu |
| B2 | Open Jurisdiction & Rule Packs | Rule packs listed; withholding rates shown (or "not set"); no permission error |
| B3 | Open Website Enquiries after submitting the demo form on the website | The enquiry appears; "Mark handled" works |
| B4 | Try to open a pool or a ledger by address | Refused |

## C. Product manager (`pm`)
| # | Step | Expected |
|---|---|---|
| C1 | Create a product with eligible asset types and participation terms | Saved as draft; invalid combinations (cap below minimum) are refused |
| C2 | Try to approve your own product | Not possible |

## D. Pool manager (`poolmanager`)
| # | Step | Expected |
|---|---|---|
| D1 | New Pool wizard, six steps, create | A draft pool with legal entity, branch, timezone, calendar |
| D2 | Open the pool: can you activate it? | No: only an independent checker or signatory sees "Open Pool" |
| D3 | Create an allocation run, submit it | The run waits for the independent check |
| D4 | Try to approve the run | Not offered |
| D5 | Freeze a pool with a reason, then try a subscription | The subscription is refused while frozen |

## E. Finance maker and checker (`maker`, `checker`)
| # | Step | Expected |
|---|---|---|
| E1 | Maker imports balances; a signed day then refuses a new import | "The day was signed off" |
| E2 | Maker prepares the daily close | The gates are computed by the server; a failing gate keeps the day open |
| E3 | Checker signs the day (a different user) | Signed; the maker cannot sign |
| E4 | Maker records income and an expense; checker posts them | Pending until the checker posts |
| E5 | Checker checks a pending run | The maker cannot check their own run |
| E6 | Provision: maker requests, checker approves | A balanced journal is posted; the checker cannot be the requester |

## F. Shariah (`secretariat`, `board`, `board2`, `board3`)
| # | Step | Expected |
|---|---|---|
| F1 | Draft a ruling with a scope that supersedes an approved one | Saved as draft |
| F2 | Quorum vote by the Board members | Approved only when the quorum is met; one member alone cannot approve |
| F3 | After approval | The older ruling shows superseded; the pools on the old contract are backed by the new ruling |
| F4 | Shariah review of a run in the ceremony | Recorded; Secretariat or Board only |
| F5 | Purification entry | Needs approval before disposition |
| F6 | Annual Shariah audit report | Figures match the plans and findings entered; the seal is shown |

## G. Risk & compliance (`risk`)
| # | Step | Expected |
|---|---|---|
| G1 | Related-party transaction: recommend without a conflict declaration | Refused |
| G2 | Recommend with a declaration and a benchmark | Status becomes "recommended"; Risk cannot approve it |
| G3 | Board or signatory gives the elevated approval | Approved; a failed price test needs a written justification |
| G4 | Verify KYC and set a tier | The tier is stored; a product that needs a higher tier refuses the subscription |
| G5 | Open the dashboard | Counts match what is on the screens |

## H. Authorized signatory (`signatory`)
| # | Step | Expected |
|---|---|---|
| H1 | Final release of a run that was checked and Shariah-reviewed | Released; journals and statements appear |
| H2 | Release a run you prepared or checked | Refused |
| H3 | Period close: certify and lock | Locked; later back-dated entries are refused |
| H4 | Edit a signed run | Not possible; only a reversal and linked rerun |

## I. Auditor (`auditor`)
| # | Step | Expected |
|---|---|---|
| I1 | Open Reports: evidence bundle, period report, audit chain verification | Works; the hash matches on re-run |
| I2 | Look for any button that posts, approves or edits | None |
| I3 | Sampling | A ranking with reasons; no opinion is issued |

## J. Investor and member (`investor`, `mudarabah.investor@...`, `member`)
| # | Step | Expected |
|---|---|---|
| J1 | See only your own accounts, statements, disclosures | No one else's data anywhere |
| J2 | Acknowledge a disclosure, then subscribe | Possible only after acknowledging the current version |
| J3 | Request a redemption | Waits for a checker; notice and gate rules apply |
| J4 | Raise a dispute or a hardship request | Visible to you; staff are notified; you cannot work the request |
| J5 | Circle member: vote on a proposal | One vote only; the result shows after closing |
| J6 | Circle ledger and receipt | Totals and references only |
| J7 | Withdraw a consent; download my data | Withdrawn consents stay in the history; the file holds only your data |

## K. Menu by role (expected)
Product Manager: Command Center, Products & Pools, Shariah Governance, AI & Analytics. Pool Manager: all operations areas, Reports and read-only Governance Config. Finance Maker / Checker: operations, ledger, Governance Config (Checker also Reports). Secretariat: Command Center, Products & Pools, Allocation, Circles, Shariah Governance, AI & Analytics. Board: as Secretariat plus Investments and Reports. Risk: everything except Administration. Secretariat also sees Investments (the Shariah review of distributions). Signatory: Command Center, Products & Pools, Allocation, Investments, Shariah Governance, Finance & Ledger, Daily Operations (Period Close only). Auditor: read-only everywhere except Administration. Investor / Member: My Portal only.

## M. Added after the 2026-10-13 audit
| # | Step | Expected |
|---|---|---|
| M1 | Pool manager proposes a change to a reserve rate or cap (with a reason) | "Proposed"; nothing changes yet; the change appears in Governance Config |
| M2 | The same pool manager tries to approve it | Refused; a different finance checker approves, and only then the rate changes |
| M3 | Try to set a reserve balance through the screen or the API | Not possible; the balance only changes with signed runs |
| M4 | Risk proposes a change to a rule pack (WHT rates, Mudarib cap); then a finance checker or the authorized signatory approves | Rule pack unchanged until approved; both steps are in the audit trail |
| M5 | Prepare a distribution for an investment pool, submit; finance checker checks; Secretariat or Board reviews; signatory releases | Each step by a different person; the signatory cannot release before the review; a second release is refused |
| M6 | Leave a high-severity exception open on a pool, then try to release a run | Refused until the exception is decided |
| M7 | Open the Risk Limit screen | Limits show where they come from (rule pack or "placeholder defaults, not confirmed"); no regulator is named as the source |
| M8 | Sign in as the Super Admin and open the audit log | Who, what, when are visible; amounts and reasons are not |
| M9 | Try to change an account's opening date | Refused |
| M10 | Create a run for a period with a day that has balances but no signed daily close, then try the independent check | Refused, naming the days; after the maker prepares and a different checker signs those days, the check works. A weekend with no balances needs no close |
| M11 | Finance maker: Finance & Ledger > GL Hand-over, generate an export; try again | The first file holds every posted batch not sent yet; the second attempt is refused (nothing new to send) |
| M12 | Finance checker records the GL's answer with its reference (or rejects with a reason) | Recorded with the checker's name; the maker cannot do it; after a rejection the batches can be sent again; the downloaded file is identical to what was sent |
| M13 | Open the trial balance, then pick an earlier "as of" date | Debits equal credits; the totals change with the date |
| M14 | Finance maker parks an unidentified receipt in suspense (Finance & Ledger > Suspense); checker approves | Nothing is posted until the checker approves; the maker cannot approve; the position shows every amount as a named item |
| M15 | Maker proposes clearing it to the account it belongs to; checker approves | The item is cleared and the suspense balance drops by the amount; a refused clearing returns the item to open |
| M16 | Leave an item open past 30 days (or the rule-pack limit), then try to close the period | Period close gate 6 fails and names the overdue items |
| M17 | Pool manager proposes an asset transfer (value and its basis required); the proposer tries to approve; a finance checker approves | Nothing moves until a different person approves; the new assignment shows the valuation |
| M18 | Risk quarantines an amount on an open exception; try to close the case; the Shariah Board decides the treatment; close with a disclosure | The case refuses to close while value is held, and after the Board's decision still needs the disclosure |
| M19 | Draw room: open the ceremony | Two steps: seal (shows the fingerprint), then reveal with a seed the members type; no pre-filled seed |

## L. Sign-off
| Function | Name | Date | Passed all steps? | Notes |
|---|---|---|---|---|
| Shariah Board | | | | |
| Finance | | | | |
| Risk & Compliance | | | | |
| Operations (Pool Manager) | | | | |
| Product owner | | | | |

Go-live also needs the finance **parallel run** of at least two representative periods against your own spreadsheets (BRD section 18);
this checklist does not replace it.
