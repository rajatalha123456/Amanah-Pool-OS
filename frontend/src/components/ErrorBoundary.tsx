import { Component, type ErrorInfo, type ReactNode } from "react"
import { Button } from "./Button"

interface Props {
  children: ReactNode
  fallbackTitle?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error caught by ErrorBoundary:", error, errorInfo)
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 m-4 rounded-xl border border-red-500/30 bg-red-950/20 text-text-primary max-w-2xl mx-auto my-12">
          <div className="flex items-center gap-3 mb-3 text-red-400">
            <span className="text-2xl">⚠️</span>
            <h2 className="text-lg font-bold">
              {this.props.fallbackTitle || "Something went wrong in this module"}
            </h2>
          </div>
          <p className="text-sm text-text-secondary mb-4">
            An unexpected error occurred while rendering this view. Our diagnostic logger has recorded the event.
          </p>
          {this.state.error && (
            <pre className="p-3 mb-4 rounded bg-slate-950/80 border border-slate-800 text-xs text-red-300 font-mono overflow-x-auto whitespace-pre-wrap">
              {this.state.error.message}
            </pre>
          )}
          <div className="flex items-center gap-3">
            <Button variant="primary" size="sm" onClick={this.handleReset}>
              🔄 Refresh Module
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                window.location.href = "/"
              }}
            >
              Return to Command Center
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
