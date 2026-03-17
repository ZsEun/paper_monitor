import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './services/AuthContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import JournalManagementPage from './pages/JournalManagementPage';
import DigestHistoryPage from './pages/DigestHistoryPage';
import DigestViewPage from './pages/DigestViewPage';
import SettingsPage from './pages/SettingsPage';

const PrivateRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/dashboard"
              element={
                <PrivateRoute>
                  <DashboardPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/journals"
              element={
                <PrivateRoute>
                  <JournalManagementPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/digests"
              element={
                <PrivateRoute>
                  <DigestHistoryPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/digest/:id"
              element={
                <PrivateRoute>
                  <DigestViewPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <PrivateRoute>
                  <SettingsPage />
                </PrivateRoute>
              }
            />
            <Route path="/" element={<Navigate to="/login" />} />
          </Routes>
        </Layout>
      </Router>
    </AuthProvider>
  );
}

export default App;
