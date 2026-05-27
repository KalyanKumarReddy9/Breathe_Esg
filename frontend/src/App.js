import React from 'react';
import { createBrowserRouter, RouterProvider, Outlet, Link } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Upload from './components/Upload';
import BatchReview from './components/BatchReview';
import './App.css';

function Layout() {
  return (
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
        <Outlet />
      </main>
    </div>
  );
}

const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <Layout />,
      children: [
        { index: true, element: <Dashboard /> },
        { path: 'upload', element: <Upload /> },
        { path: 'batches/:id', element: <BatchReview /> },
      ],
    },
  ],
  {
    future: {
      v7_startTransition: true,
      v7_relativeSplatPath: true,
    },
  }
);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
