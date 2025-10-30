import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../store/authSlice';
import { styles } from '../styles/common';

export default function LogoutButton({ className, style }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await dispatch(logout({ silent: true })).unwrap();
    } finally {
      navigate('/login', { replace: true });
    }
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
