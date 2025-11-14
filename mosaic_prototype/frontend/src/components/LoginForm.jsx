import { useEffect, useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { login, selectIsAuthenticated } from '../store/authSlice';
import { getFriendlyMessage } from '../services/authService';
import { styles } from '../styles/common';
import { useForm } from 'react-hook-form';

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
  const dispatch = useDispatch();
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const navigate = useNavigate();
  const location = useLocation();
  const [authError, setAuthError] = useState('');
  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isSubmitting, touchedFields, isSubmitted },
  } = useForm({
    mode: 'onChange',
    defaultValues: {
      username: '',
      password: '',
    },
  });

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = async ({ username, password }) => {
    setAuthError('');
    try {
      await dispatch(login({ username: username.trim(), password })).unwrap();
      const redirectTo = location.state?.from?.pathname || '/';
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setAuthError(extractMessage(err, getFriendlyMessage));
    }
  };

  const showUsernameError = errors.username && (touchedFields.username || isSubmitted);
  const showPasswordError = errors.password && (touchedFields.password || isSubmitted);

  return (
    <div style={formContainerStyle}>
      <h2 style={{ marginBottom: 16 }}>Přihlášení</h2>
      {authError && (
        <div style={{
          background: '#3b1f24',
          color: '#f28b82',
          padding: '10px 12px',
          borderRadius: 6,
          marginBottom: 12,
          border: '1px solid #5c1f24',
        }}>
          {authError}
        </div>
      )}
      <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <input
          type="text"
          placeholder="Uživatelské jméno"
          autoComplete="username"
          {...register('username', {
            required: 'Zadejte uživatelské jméno nebo email.',
            validate: (value) => value.trim() !== '' || 'Zadejte uživatelské jméno nebo email.',
          })}
          style={{
            ...styles.input,
            border: showUsernameError ? '1px solid #d93025' : styles.input.border,
          }}
          aria-invalid={showUsernameError ? 'true' : 'false'}
        />
        {showUsernameError && (
          <span style={{ color: '#f28b82', fontSize: 12 }}>
            {errors.username.message}
          </span>
        )}
        <input
          type="password"
          placeholder="Heslo"
          autoComplete="current-password"
          {...register('password', {
            required: 'Zadejte heslo.',
            validate: (value) => value.trim() !== '' || 'Zadejte heslo.',
          })}
          style={{
            ...styles.input,
            border: showPasswordError ? '1px solid #d93025' : styles.input.border,
          }}
          aria-invalid={showPasswordError ? 'true' : 'false'}
        />
        {showPasswordError && (
          <span style={{ color: '#f28b82', fontSize: 12 }}>
            {errors.password.message}
          </span>
        )}
        <button
          type="submit"
          style={{
            ...styles.button,
            opacity: !isValid || isSubmitting ? 0.7 : 1,
            cursor: !isValid || isSubmitting ? 'not-allowed' : styles.button.cursor,
          }}
          disabled={!isValid || isSubmitting}
        >
          {isSubmitting ? 'Přihlašuji…' : 'Přihlásit se'}
        </button>
      </form>
      <p style={{ marginTop: 16, fontSize: 14 }}>
        Nemáte účet? <Link to="/register">Registrujte se</Link>
      </p>
    </div>
  );
}
