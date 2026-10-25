import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  name: string;
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class SectionBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // eslint-disable-next-line no-console -- intentional error logging in boundary
    console.error(`[SectionBoundary: ${this.props.name}]`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          border: '1px solid rgba(248, 113, 113, 0.3)',
          borderRadius: 8,
          padding: '12px 16px',
          margin: '8px 0',
          background: 'rgba(248, 113, 113, 0.04)',
          color: '#a8c0c5',
          fontSize: 11,
          fontFamily: 'monospace',
        }}>
          <b style={{ color: '#f87171' }}>⚠ {this.props.name} failed to render</b>
          <p style={{ margin: '4px 0 0', color: '#5a7a80' }}>
            {this.state.error?.message ?? 'Unknown error'} — other sections are unaffected.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
