import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // eslint-disable-next-line no-console -- intentional error logging in boundary
    console.error('[CircuitMind ErrorBoundary]', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div style={{
          padding: 32,
          background: '#0a1a1f',
          color: '#e0f0f2',
          fontFamily: 'monospace',
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
        }}>
          <div style={{
            border: '1px solid #f87171',
            borderRadius: 8,
            padding: '24px 32px',
            maxWidth: 520,
            background: 'rgba(248, 113, 113, 0.06)',
          }}>
            <h2 style={{ color: '#f87171', margin: '0 0 12px', fontSize: 16 }}>
              ⚠ CircuitMind encountered an error
            </h2>
            <p style={{ color: '#a8c0c5', fontSize: 12, lineHeight: 1.6, margin: '0 0 16px' }}>
              The diagnostic console hit an unexpected error during rendering.
              This does not affect the underlying engine — the analysis results are still valid.
            </p>
            <details style={{ marginBottom: 16 }}>
              <summary style={{ color: '#67e6e7', cursor: 'pointer', fontSize: 11 }}>
                Technical details
              </summary>
              <pre style={{
                color: '#5a7a80',
                fontSize: 10,
                textAlign: 'left',
                marginTop: 8,
                overflow: 'auto',
                maxHeight: 120,
              }}>
                {this.state.error?.message}
                {'\n'}
                {this.state.error?.stack}
              </pre>
            </details>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              style={{
                padding: '8px 20px',
                background: 'rgba(103, 230, 231, 0.15)',
                border: '1px solid rgba(103, 230, 231, 0.4)',
                color: '#67e6e7',
                fontFamily: 'monospace',
                fontSize: 11,
                letterSpacing: '0.05em',
                cursor: 'pointer',
                borderRadius: 3,
              }}
            >
              RELOAD CONSOLE
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
