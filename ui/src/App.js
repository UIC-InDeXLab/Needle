import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import WelcomeScreen from './components/WelcomeScreen';
import SearchPage from './pages/SearchPage';
import DirectoryPage from './pages/DirectoryPage';
import GeneratePage from './pages/GeneratePage';
import GeneratorPage from './pages/GeneratorPage';
import StatusPage from './pages/StatusPage';
import { getSetupStatus } from './services/api';
import './styles/index.css';

function App() {
  const [ready, setReady] = useState(false);
  const [checked, setChecked] = useState(false);

  // Decide once on load whether onboarding is needed.
  useEffect(() => {
    let mounted = true;
    getSetupStatus()
      .then((r) => {
        if (mounted) {
          setReady(Boolean(r.data?.ready));
          setChecked(true);
        }
      })
      .catch(() => {
        // Backend not responding yet — show the welcome screen, which retries.
        if (mounted) setChecked(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (!checked || !ready) {
    return <WelcomeScreen onReady={() => setReady(true)} />;
  }

  return (
    <Router>
      <div className="App">
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/search" replace />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/directories" element={<DirectoryPage />} />
            <Route path="/generate" element={<GeneratePage />} />
            <Route path="/generators" element={<GeneratorPage />} />
            <Route path="/status" element={<StatusPage />} />
          </Routes>
        </Layout>
      </div>
    </Router>
  );
}

export default App;
