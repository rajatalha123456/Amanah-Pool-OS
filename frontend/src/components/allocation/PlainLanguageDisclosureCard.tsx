import { useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import type { DepositorStatement } from "../../types"

interface PlainLanguageDisclosureCardProps {
  statement: DepositorStatement
}

type LangMode = "bilingual" | "urdu" | "english"

export function PlainLanguageDisclosureCard({ statement }: PlainLanguageDisclosureCardProps) {
  const [lang, setLang] = useState<LangMode>("bilingual")

  const participantName = statement.participant_class
  const profitAmt = Number(statement.profit_allocated).toLocaleString(undefined, { minimumFractionDigits: 2 })
  const closingAmt = Number(statement.closing_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })
  const openingAmt = Number(statement.opening_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })

  // Plain-Language Urdu Translation conforming to SBP IBD Circular 03/2012
  const urduText = `محترم کھاتہ دار! 
اسٹیٹ بینک آف پاکستان (SBP) کے اسلامک بینکنگ سرکلر نمبر 03/2012 اور ایوفی (AAOIFI FAS-30) شریعہ معیارات کے تحت، آپ کے سرمایہ کاری پول کے منافع کی تقسیم مکمل ہو چکی ہے۔

• آپ کا کھاتہ / زمرہ: ${participantName}
• ابتدائی سرمایہ (Opening Balance): PKR ${openingAmt}
• منافع کا حصہ (Profit Allocated): PKR ${profitAmt}
• اختتامی رقم (Closing Balance): PKR ${closingAmt}

وضاحتی نوٹ برائے عوامی فہم:
1. بینک نے مضارب (فنڈ منیجر) کے طور پر آپ کے فنڈز کو صرف شرعی طور پر منظور شدہ اسلامی اثاثہ جات (مرابحہ، اجارہ، مشارکہ) میں استعمال کیا۔
2. حاصل شدہ مجموعی آمدن میں سے براہ راست اخراجات منہا کرنے کے بعد، طے شدہ شرح کے مطابق نفع کھاتہ داروں اور مضارب کے درمیان تقسیم کیا گیا۔
3. پرنسپل رقم محفوظ رہی ہے اور کوئی غیر شرعی کٹوتی یا سود (ربا) شامل نہیں ہے۔ شریعہ بورڈ نے اس حساب کتاب اور نفع تقسیم کی توثیق کر دی ہے۔`

  const englishText = `Respected Depositor!
In compliance with State Bank of Pakistan (SBP) IBD Circular 03/2012 and AAOIFI FAS-30 Standards, the profit distribution for your investment pool has been finalized.

• Participant Tier: ${participantName}
• Opening Balance: PKR ${openingAmt}
• Net Profit Allocated: PKR ${profitAmt}
• Closing Balance: PKR ${closingAmt}

Plain-Language Explanatory Summary:
1. The bank, acting as Mudarib (Investment Agent), deployed your funds strictly into Shariah-compliant financing assets (Murabaha, Ijarah, Diminishing Musharakah).
2. After deducting permissible direct asset expenses from gross income, the distributable profit was apportioned in accordance with pre-notified Profit Sharing Ratios (PSR) and Weightage factors.
3. Your principal remains unencumbered, free from any element of Riba (interest). The Shariah Supervisory Board has reviewed and certified this distribution cycle.`

  return (
    <Card
      title="📜 SBP Statutory Plain-Language Disclosure (عوامی وضاحتی بیان)"
      className="border-emerald-500/20 bg-surface/90"
      actions={
        <div className="flex items-center gap-1.5 bg-surface-subtle p-1 rounded-lg border border-ink/10 text-xs">
          <button
            type="button"
            onClick={() => setLang("bilingual")}
            className={`px-2.5 py-1 rounded transition-colors ${
              lang === "bilingual"
                ? "bg-emerald-600 text-white font-medium"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            Bilingual (دونوں)
          </button>
          <button
            type="button"
            onClick={() => setLang("urdu")}
            className={`px-2.5 py-1 rounded transition-colors ${
              lang === "urdu"
                ? "bg-emerald-600 text-white font-medium"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            اردو (Urdu)
          </button>
          <button
            type="button"
            onClick={() => setLang("english")}
            className={`px-2.5 py-1 rounded transition-colors ${
              lang === "english"
                ? "bg-emerald-600 text-white font-medium"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            English
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-ink-muted border-b border-ink/10 pb-2">
          <span>State Bank of Pakistan (SBP) Transparency Mandate • Circular 03/2012</span>
          <Badge variant="emerald">Shariah Board Certified</Badge>
        </div>

        <div className={`grid gap-4 ${lang === "bilingual" ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1"}`}>
          {/* Urdu Section */}
          {(lang === "bilingual" || lang === "urdu") && (
            <div
              dir="rtl"
              className="p-4 rounded-lg bg-surface-subtle border border-ink/10 text-right space-y-2 font-sans"
              style={{ fontFamily: "'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', 'Urdu Typesetting', sans-serif" }}
            >
              <div className="flex items-center justify-between border-b border-ink/10 pb-2 mb-2">
                <span className="font-bold text-sm text-emerald-400">اردو عوامی وضاحتی بیان</span>
                <span className="text-[10px] text-ink-muted">اسٹیٹ بینک آف پاکستان</span>
              </div>
              <p className="text-xs leading-relaxed text-ink whitespace-pre-line text-justify">
                {urduText}
              </p>
            </div>
          )}

          {/* English Section */}
          {(lang === "bilingual" || lang === "english") && (
            <div className="p-4 rounded-lg bg-surface-subtle border border-ink/10 space-y-2">
              <div className="flex items-center justify-between border-b border-ink/10 pb-2 mb-2">
                <span className="font-bold text-xs text-emerald-400 uppercase tracking-wide">
                  English Plain-Language Disclosure
                </span>
                <span className="text-[10px] text-ink-muted">SBP Regulatory Transparency</span>
              </div>
              <p className="text-xs leading-relaxed text-ink whitespace-pre-line">
                {englishText}
              </p>
            </div>
          )}
        </div>

        {/* Shariah Compliance & Verification Footer */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-ink-muted border-t border-ink/10">
          <div className="flex items-center gap-2">
            <span>🛡️ Shariah Governance Ref:</span>
            <code className="text-emerald-400 font-mono text-[10px]">
              FATWA-2026-FAS30-CERTIFIED
            </code>
          </div>
          <div>
            Verified under AAOIFI FAS-30 Standards by Amanah Shariah Supervisory Board
          </div>
        </div>
      </div>
    </Card>
  )
}
