import { useEffect, useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import {
  fetchFraudCollusionAnalysis,
  type FraudCollusionResponse,
  type GraphNode,
} from "../../api/fraudCollusion"
import { extractErrorMessage } from "../../api/errors"

interface FraudCollusionGraphViewProps {
  poolId?: string
}

export function FraudCollusionGraphView({ poolId }: FraudCollusionGraphViewProps) {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<FraudCollusionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [showDossier, setShowDossier] = useState(false)
  const [copied, setCopied] = useState(false)

  const loadData = () => {
    setLoading(true)
    setError(null)
    fetchFraudCollusionAnalysis(poolId)
      .then((res) => {
        setData(res)
        if (res.graph.nodes.length > 0) {
          setSelectedNode(res.graph.nodes[0])
        }
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadData()
  }, [poolId])

  const copyDossier = () => {
    if (!data?.investigation_dossier) return
    navigator.clipboard.writeText(data.investigation_dossier)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  if (loading) {
    return (
      <Card title="AI Fraud & Collusion Syndicate Graph">
        <div className="flex items-center gap-2 py-12 text-ink-secondary justify-center">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Analyzing participant graph centrality & circular loops...</span>
        </div>
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card title="AI Fraud & Collusion Syndicate Graph">
        <div className="p-4 rounded-lg border border-red-500/30 bg-red-950/20 text-xs text-red-300">
          <p className="font-semibold">Graph Network Analysis Failed</p>
          <p className="mt-1">{error || "Unable to compute network graph."}</p>
          <Button variant="secondary" className="mt-3 text-xs" onClick={loadData}>
            Retry Analysis
          </Button>
        </div>
      </Card>
    )
  }

  // Calculate radial coordinates for visual SVG network
  const svgWidth = 520
  const svgHeight = 380
  const centerX = svgWidth / 2
  const centerY = svgHeight / 2
  const radius = 135

  const nodePositions: Record<string, { x: number; y: number }> = {}
  const totalNodes = data.graph.nodes.length

  data.graph.nodes.forEach((node, i) => {
    const angle = (i / totalNodes) * 2 * Math.PI - Math.PI / 2
    nodePositions[node.id] = {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    }
  })

  return (
    <div className="space-y-6">
      {/* Top Banner Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg border border-ink/10 bg-surface">
          <div className="text-[11px] text-ink-secondary uppercase tracking-wider font-semibold">
            Network Risk Index
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold font-mono ${
                data.overall_network_risk >= 75
                  ? "text-red-400"
                  : data.overall_network_risk >= 50
                  ? "text-gold-400"
                  : "text-emerald-400"
              }`}
            >
              {data.overall_network_risk}
            </span>
            <span className="text-xs text-ink-muted">/ 100</span>
          </div>
          <div className="mt-2">
            <Badge
              variant={
                data.risk_tier === "CRITICAL"
                  ? "neutral"
                  : data.risk_tier === "HIGH"
                  ? "gold"
                  : "emerald"
              }
            >
              {data.risk_tier} RISK TIER
            </Badge>
          </div>
        </div>

        <div className="p-4 rounded-lg border border-ink/10 bg-surface">
          <div className="text-[11px] text-ink-secondary uppercase tracking-wider font-semibold">
            Syndicate Rings
          </div>
          <div className="mt-1 text-2xl font-bold font-mono text-ink">
            {data.cluster_count}
          </div>
          <div className="mt-2 text-xs text-ink-muted">Flagged collusion rings</div>
        </div>

        <div className="p-4 rounded-lg border border-ink/10 bg-surface">
          <div className="text-[11px] text-ink-secondary uppercase tracking-wider font-semibold">
            High Risk Entities
          </div>
          <div className="mt-1 text-2xl font-bold font-mono text-gold-400">
            {data.suspicious_member_count}
          </div>
          <div className="mt-2 text-xs text-ink-muted">Above moral hazard threshold</div>
        </div>

        <div className="p-4 rounded-lg border border-ink/10 bg-surface flex flex-col justify-between">
          <div>
            <div className="text-[11px] text-ink-secondary uppercase tracking-wider font-semibold">
              Regulatory Status
            </div>
            <div className="mt-1 text-xs font-semibold text-emerald-400">
              SBP AML-04 Active
            </div>
          </div>
          <Button
            variant="secondary"
            className="text-xs w-full mt-2"
            onClick={() => setShowDossier(!showDossier)}
          >
            {showDossier ? "Hide SBP Dossier" : "📄 View SBP Dossier"}
          </Button>
        </div>
      </div>

      {/* Main Interactive Graph & Member Detail Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SVG Network Graph Canvas */}
        <div className="lg:col-span-2 rounded-lg border border-ink/10 bg-surface p-4 flex flex-col items-center">
          <div className="w-full flex items-center justify-between border-b border-ink/10 pb-3 mb-3">
            <div>
              <h4 className="text-xs font-bold text-ink uppercase tracking-wide">
                🕸️ Interactive Entity & Guarantee Link Network
              </h4>
              <p className="text-[11px] text-ink-secondary">
                Click any participant node to inspect underwriting attributes and guarantee chains
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                <span className="text-ink-muted">Circular Loop</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-gold-400"></span>
                <span className="text-ink-muted">Shared Address</span>
              </div>
            </div>
          </div>

          <svg
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            className="w-full max-w-[520px] h-[340px] select-none"
          >
            {/* Draw Graph Edges */}
            <defs>
              <marker
                id="arrowhead-red"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#ef4444" />
              </marker>
              <marker
                id="arrowhead-gold"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#f59e0b" />
              </marker>
            </defs>

            {data.graph.edges.map((edge) => {
              const src = nodePositions[edge.source]
              const tgt = nodePositions[edge.target]
              if (!src || !tgt) return null

              const isRed = edge.type === "CIRCULAR_GUARANTEE"
              return (
                <g key={edge.id}>
                  <line
                    x1={src.x}
                    y1={src.y}
                    x2={tgt.x}
                    y2={tgt.y}
                    stroke={edge.color}
                    strokeWidth={isRed ? "2.5" : "1.8"}
                    strokeDasharray={isRed ? "5 3" : undefined}
                    markerEnd={isRed ? "url(#arrowhead-red)" : "url(#arrowhead-gold)"}
                    className="opacity-75 hover:opacity-100 transition-opacity"
                  />
                </g>
              )
            })}

            {/* Draw Graph Nodes */}
            {data.graph.nodes.map((node) => {
              const pos = nodePositions[node.id]
              if (!pos) return null
              const isSelected = selectedNode?.id === node.id

              const nodeFill =
                node.risk_score >= 75
                  ? "#7f1d1d" // dark red
                  : node.risk_score >= 50
                  ? "#78350f" // dark amber
                  : "#064e3b" // dark emerald

              const strokeColor =
                node.risk_score >= 75
                  ? "#ef4444"
                  : node.risk_score >= 50
                  ? "#f59e0b"
                  : "#10b981"

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  className="cursor-pointer"
                  onClick={() => setSelectedNode(node)}
                >
                  <circle
                    r={isSelected ? "22" : "18"}
                    fill={nodeFill}
                    stroke={strokeColor}
                    strokeWidth={isSelected ? "3" : "2"}
                    className="transition-all hover:scale-110"
                  />
                  <text
                    textAnchor="middle"
                    dy="4"
                    fill="#ffffff"
                    fontSize="10"
                    fontWeight="bold"
                    className="pointer-events-none font-mono"
                  >
                    P{node.payout_position ?? "?"}
                  </text>
                  <text
                    textAnchor="middle"
                    dy="32"
                    fill="#e2e8f0"
                    fontSize="10"
                    className="pointer-events-none font-medium"
                  >
                    {node.label.split(" ")[0]}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>

        {/* Selected Entity Forensics Detail Card */}
        <div className="rounded-lg border border-ink/10 bg-surface p-4 flex flex-col justify-between">
          <div>
            <h4 className="text-xs font-bold text-ink uppercase tracking-wide border-b border-ink/10 pb-2 mb-3">
              Participant Underwriting Profile
            </h4>

            {selectedNode ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-ink">{selectedNode.label}</span>
                  <Badge
                    variant={
                      selectedNode.risk_score >= 75
                        ? "neutral"
                        : selectedNode.risk_score >= 50
                        ? "gold"
                        : "emerald"
                    }
                  >
                    Risk: {selectedNode.risk_score}%
                  </Badge>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-surface-subtle">
                    <span className="text-ink-secondary text-[10px]">Reference:</span>
                    <p className="font-mono font-medium text-ink">{selectedNode.ref}</p>
                  </div>
                  <div className="p-2 rounded bg-surface-subtle">
                    <span className="text-ink-secondary text-[10px]">Rotation Draw:</span>
                    <p className="font-medium text-ink">
                      Position #{selectedNode.payout_position ?? "Unassigned"}
                    </p>
                  </div>
                  <div className="p-2 rounded bg-surface-subtle">
                    <span className="text-ink-secondary text-[10px]">Disbursement:</span>
                    <p className="font-medium text-ink">
                      {selectedNode.is_paid_out ? "✅ Received" : "⏳ Pending Draw"}
                    </p>
                  </div>
                  <div className="p-2 rounded bg-surface-subtle">
                    <span className="text-ink-secondary text-[10px]">Circle Pool:</span>
                    <p className="font-medium text-ink truncate">{selectedNode.pool}</p>
                  </div>
                </div>

                {/* Risk Flags */}
                <div>
                  <span className="text-[11px] font-semibold text-ink-secondary">
                    Forensic Anomaly Flags:
                  </span>
                  {selectedNode.flags.length > 0 ? (
                    <ul className="mt-1 space-y-1">
                      {selectedNode.flags.map((flag, idx) => (
                        <li
                          key={idx}
                          className="text-[11px] text-amber-300 bg-amber-950/20 border border-amber-500/20 px-2 py-1 rounded"
                        >
                          ⚠️ {flag}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-[11px] text-emerald-400">
                      ✓ Zero behavioral anomalies detected.
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-xs text-ink-secondary py-8 text-center">
                Click a node on the network graph to inspect details.
              </p>
            )}
          </div>

          <div className="pt-4 border-t border-ink/10">
            <Button
              variant="secondary"
              className="w-full text-xs text-red-400 hover:text-red-300 border-red-500/20"
              onClick={() => {
                alert(`Directing risk hold for ${selectedNode?.label || "member"}. Form AML-04 flag recorded.`)
              }}
            >
              🔒 Place Risk Hold on Payout
            </Button>
          </div>
        </div>
      </div>

      {/* Detected Syndicate Clusters List */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-ink uppercase tracking-wide">
          Detected Collusion Syndicates & Circular Chains ({data.clusters.length})
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.clusters.map((c) => (
            <div
              key={c.cluster_id}
              className={`p-4 rounded-lg border space-y-2 ${
                c.severity === "CRITICAL"
                  ? "border-red-500/30 bg-red-950/20"
                  : "border-gold-500/30 bg-gold-950/20"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-ink">{c.title}</span>
                <Badge variant={c.severity === "CRITICAL" ? "neutral" : "gold"}>
                  {c.severity}
                </Badge>
              </div>

              <p className="text-xs text-ink-secondary">{c.description}</p>

              <div className="text-[11px] text-ink-muted">
                <span className="font-semibold text-ink">Involved:</span> {c.members.join(", ")}
              </div>

              <div className="p-2.5 rounded bg-surface border border-ink/10 text-[11px] text-emerald-300">
                <span className="font-semibold">SBP Directive:</span> {c.recommended_action}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SBP Regulatory AML Dossier Viewer */}
      {showDossier && (
        <Card
          title="Official SBP & FIA Anti-Money Laundering Forensic Memorandum"
          actions={
            <Button variant="secondary" className="text-xs" onClick={copyDossier}>
              {copied ? "✓ Copied to Clipboard" : "📋 Copy Dossier"}
            </Button>
          }
        >
          <pre className="font-mono text-xs text-ink-secondary bg-surface-subtle p-4 rounded-lg whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed border border-ink/10">
            {data.investigation_dossier}
          </pre>
        </Card>
      )}
    </div>
  )
}
