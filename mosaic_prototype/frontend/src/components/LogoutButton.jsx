import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { styles } from '../styles/common';

export default function LogoutButton({ className, style }) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout({ silent: true });
    navigate('/login', { replace: true });
  };

  return (
    <button
      type="button"
      onClick={handleLogout}
      style={{ ...styles.button, ...(style || {}), backgroundColor: '#a33f3f' }}
      className={className}
    >
      Odhlásit se
    </button>
  );
}
