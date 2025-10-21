import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import SearchPage from './pages/SearchPage';
import DirectoryPage from './pages/DirectoryPage';
import GeneratorPage from './pages/GeneratorPage';
import StatusPage from './pages/StatusPage';
import './styles/index.css';

function App() {
  console.log('Needle Demo App loading...');
  
  return (
    <Router basename="/Needle/demo">
      <div className="App">
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
