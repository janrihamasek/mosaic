import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { register as registerUser, selectIsAuthenticated } from '../store/authSlice';
import { getFriendlyMessage } from '../services/authService';
import { styles } from '../styles/common';

const containerStyle = {
  ...styles.card,
  maxWidth: 360,
  margin: '80px auto',
  width: '100%',
};

export default function RegisterForm() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const [form, setForm] = useState({ username: '', password: '', confirmPassword: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (loading) return;
    if (form.password !== form.confirmPassword) {
      setError('Hesla se musí shodovat');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await dispatch(registerUser({ username: form.username.trim(), password: form.password })).unwrap();
      setSuccess('Registrace proběhla úspěšně. Můžete se přihlásit.');
      setTimeout(() => navigate('/login'), 1200);
    } catch (err) {
      const message = err?.friendlyMessage || getFriendlyMessage(err?.code, err?.message) || err?.message;
      setError(message || 'Registrace se nezdařila');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={containerStyle}>
      <h2 style={{ marginBottom: 16 }}>Registrace</h2>
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
      {success && (
        <div style={{
          background: '#1f3b29',
          color: '#7cd992',
          padding: '10px 12px',
          borderRadius: 6,
          marginBottom: 12,
          border: '1px solid #2f5b3d',
        }}>
          {success}
        </div>
      )}
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <input
          type="text"
          name="username"
          placeholder="Uživatelské jméno"
          value={form.username}
          onChange={handleChange}
          style={styles.input}
          autoComplete="username"
          required
        />
        <input
          type="password"
          name="password"
          placeholder="Heslo"
          value={form.password}
          onChange={handleChange}
          style={styles.input}
          autoComplete="new-password"
          required
        />
        <input
          type="password"
          name="confirmPassword"
          placeholder="Potvrďte heslo"
          value={form.confirmPassword}
          onChange={handleChange}
          style={styles.input}
          autoComplete="new-password"
          required
        />
        <button type="submit" style={styles.button} disabled={loading}>
          {loading ? 'Registruji…' : 'Registrovat'}
        </button>
      </form>
      <p style={{ marginTop: 16, fontSize: 14 }}>
        Máte účet? <Link to="/login">Přejděte na přihlášení</Link>
      </p>
    </div>
  );
}
