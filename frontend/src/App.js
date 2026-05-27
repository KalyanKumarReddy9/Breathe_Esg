import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Upload from './components/Upload';
import BatchReview from './components/BatchReview';
import './App.css';
function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <div className="nav">
            <h1>Breathe ESG</h1>
            <nav>
              <Link to="/">Dashboard</Link>
              <Link to="/upload">Upload Data</Link>
            </nav>
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/batches/:id" element={<BatchReview />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
