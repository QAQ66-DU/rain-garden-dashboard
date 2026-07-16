import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  failed: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Dashboard render failure', error.name, info.componentStack);
  }

  render() {
    if (this.state.failed) {
      return (
        <section className="state-panel" role="alert">
          <p className="eyebrow">Interface error</p>
          <h1>The dashboard could not render</h1>
          <p>Refresh the page. If the problem continues, check the application logs.</p>
        </section>
      );
    }
    return this.props.children;
  }
}
