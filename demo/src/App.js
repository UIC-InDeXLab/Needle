import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import SearchPage from './pages/SearchPage';
import DirectoryPage from './pages/DirectoryPage';
import GeneratorPage from './pages/GeneratorPage';
import StatusPage from './pages/StatusPage';
import './styles/index.css';

// Component to handle GitHub Pages SPA redirect
function RedirectHandler() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Check for redirect parameter from 404.html
    const urlParams = new URLSearchParams(location.search);
    const redirectPath = urlParams.get('p');
    
    if (redirectPath) {
      // Clean up the URL by removing the redirect parameter
      const newUrl = new URL(window.location);
      newUrl.searchParams.delete('p');
      window.history.replaceState({}, '', newUrl.pathname + newUrl.search + newUrl.hash);
      
      // Navigate to the intended path
      navigate(redirectPath, { replace: true });
    }
  }, [navigate, location.search]);

  return null;
}

function App() {
  console.log('Needle Demo App loading...');
  
  return (
    <Router basename="/Needle/demo">
      <div className="App">
        <RedirectHandler />
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/search" replace />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/directories" element={<DirectoryPage />} />
            <Route path="/generators" element={<GeneratorPage />} />
            <Route path="/status" element={<StatusPage />} />
          </Routes>
        </Layout>
      </div>
    </Router>
  );
}

export default App;
