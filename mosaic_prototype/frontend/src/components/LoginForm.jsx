import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { styles } from '../styles/common';

const formContainerStyle = {
  ...styles.card,
  maxWidth: 360,
  margin: '80px auto',
  width: '100%',
};

function extractMessage(error, getFriendlyMessage) {
  if (!error) return 'Neznámá chyba';
  if (error.friendlyMessage) return error.friendlyMessage;
  if (error.code) return getFriendlyMessage(error.code, error.message);
  return error.message || 'Neznámá chyba';
}

export default function LoginForm() {
  const { login, isAuthenticated, getFriendlyMessage } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setError('');
    try {
      await login(username.trim(), password);
      const redirectTo = location.state?.from?.pathname || '/';
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(extractMessage(err, getFriendlyMessage));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={formContainerStyle}>
      <h2 style={{ marginBottom: 16 }}>Přihlášení</h2>
      {error && (
        <div style={{
          background: '#3b1f24',
          color: '#f28b82',
          padding: '10px 12px',
          borderRadius: 6,
          marginBottom: 12,
          border: '1px solid #5c1f24',
        }}>
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <input
          type="text"
          placeholder="Uživatelské jméno"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={styles.input}
          required
        />
        <input
          type="password"
          placeholder="Heslo"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={styles.input}
          required
        />
        <button type="submit" style={styles.button} disabled={loading}>
          {loading ? 'Přihlašuji…' : 'Přihlásit se'}
        </button>
      </form>
      <p style={{ marginTop: 16, fontSize: 14 }}>
        Nemáte účet? <Link to="/register">Registrujte se</Link>
      </p>
    </div>
  );
}
