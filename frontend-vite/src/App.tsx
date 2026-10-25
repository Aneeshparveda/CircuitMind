import { useEffect, useState } from 'react';
import { Streamlit } from 'streamlit-component-lib';
import ErrorBoundary from './components/console/ErrorBoundary';
import ForensicsConsole from './components/console/ForensicsConsole';
import type { ConsoleArgs } from './components/console/types';

function App() {
  const [args, setArgs] = useState<ConsoleArgs>({});

  useEffect(() => {
    const onRender = (event: Event) => {
      const detail = (event as CustomEvent<{ args?: ConsoleArgs }>).detail;
      setArgs(detail.args ?? {});
    };
    // Subscribe before declaring readiness so the initial payload cannot be
    // emitted before React has installed its listener.
    Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
    Streamlit.setComponentReady();
    return () => Streamlit.events.removeEventListener(Streamlit.RENDER_EVENT, onRender);
  }, []);

  return (
    <ErrorBoundary>
      <ForensicsConsole args={args} />
    </ErrorBoundary>
  );
}

export default App;
