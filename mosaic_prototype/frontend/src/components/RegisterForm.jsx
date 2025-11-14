import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { useForm } from 'react-hook-form';
import { register as registerUser, selectIsAuthenticated } from '../store/authSlice';
import { getFriendlyMessage } from '../services/authService';
import { styles } from '../styles/common';

const containerStyle = {
  ...styles.card,
  maxWidth: 360,
  margin: '80px auto',
  width: '100%',
};

const errorTextStyle = { color: '#f28b82', fontSize: 12 };

export default function RegisterForm() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const [serverError, setServerError] = useState('');
  const [success, setSuccess] = useState('');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isValid, isSubmitting },
  } = useForm({
    mode: 'onChange',
    defaultValues: {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
  });

  const passwordValue = watch('password');

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const buildInputStyle = (hasError) => ({
    ...styles.input,
    border: hasError ? '1px solid #d93025' : styles.input.border,
  });

  const onSubmit = async (data) => {
    if (isSubmitting) return;
    setServerError('');
    try {
      // Backend accepts username & password only; email stays client-side for validation UX.
      await dispatch(registerUser({ username: data.username.trim(), password: data.password })).unwrap();
      setSuccess('Registrace proběhla úspěšně. Můžete se přihlásit.');
      setTimeout(() => navigate('/login'), 1200);
    } catch (err) {
      const message = err?.friendlyMessage || getFriendlyMessage(err?.code, err?.message) || err?.message;
      setServerError(message || 'Registrace se nezdařila');
    }
  };

  return (
    <div style={containerStyle}>
      <h2 style={{ marginBottom: 16 }}>Registrace</h2>
      {serverError && (
        <div
          style={{
            background: '#3b1f24',
            color: '#f28b82',
            padding: '10px 12px',
            borderRadius: 6,
            marginBottom: 12,
            border: '1px solid #5c1f24',
          }}
        >
          {serverError}
        </div>
      )}
      {success && (
        <div
          style={{
            background: '#1f3b29',
            color: '#7cd992',
            padding: '10px 12px',
            borderRadius: 6,
            marginBottom: 12,
            border: '1px solid #2f5b3d',
          }}
        >
          {success}
        </div>
      )}
      <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <input
            type="text"
            placeholder="Uživatelské jméno"
            autoComplete="username"
            {...register('username', {
              required: 'Uživatelské jméno je povinné.',
              minLength: { value: 3, message: 'Jméno musí mít alespoň 3 znaky.' },
              maxLength: { value: 80, message: 'Jméno může mít maximálně 80 znaků.' },
              validate: {
                trimmed: (value) => value.trim().length === value.length || 'Jméno nesmí obsahovat mezery na začátku nebo konci.',
                noSpaces: (value) => !/\s/.test(value) || 'Jméno nesmí obsahovat mezery.',
              },
            })}
            style={buildInputStyle(!!errors.username)}
            aria-invalid={errors.username ? 'true' : 'false'}
          />
          {errors.username && <span style={errorTextStyle}>{errors.username.message}</span>}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <input
            type="email"
            placeholder="E-mail"
            autoComplete="email"
            {...register('email', {
              required: 'E-mail je povinný.',
              pattern: {
                value: /^[\w-.]+@([\w-]+\.)+[\w-]{2,}$/i,
                message: 'Zadejte platný e-mail.',
              },
            })}
            style={buildInputStyle(!!errors.email)}
            aria-invalid={errors.email ? 'true' : 'false'}
          />
          {errors.email && <span style={errorTextStyle}>{errors.email.message}</span>}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <input
            type="password"
            placeholder="Heslo"
            autoComplete="new-password"
            {...register('password', {
              required: 'Heslo je povinné.',
              minLength: { value: 8, message: 'Heslo musí mít alespoň 8 znaků.' },
            })}
            style={buildInputStyle(!!errors.password)}
            aria-invalid={errors.password ? 'true' : 'false'}
          />
          {errors.password && <span style={errorTextStyle}>{errors.password.message}</span>}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <input
            type="password"
            placeholder="Potvrďte heslo"
            autoComplete="new-password"
            {...register('confirmPassword', {
              required: 'Potvrzení hesla je povinné.',
              validate: (value) => value === passwordValue || 'Hesla se musí shodovat.',
            })}
            style={buildInputStyle(!!errors.confirmPassword)}
            aria-invalid={errors.confirmPassword ? 'true' : 'false'}
          />
          {errors.confirmPassword && <span style={errorTextStyle}>{errors.confirmPassword.message}</span>}
        </div>

        <button
          type="submit"
          style={{
            ...styles.button,
            opacity: !isValid || isSubmitting ? 0.7 : 1,
            cursor: !isValid || isSubmitting ? 'not-allowed' : styles.button.cursor,
          }}
          disabled={!isValid || isSubmitting}
        >
          {isSubmitting ? 'Registruji…' : 'Registrovat'}
        </button>
      </form>
      <p style={{ marginTop: 16, fontSize: 14 }}>
        Máte účet? <Link to="/login">Přejděte na přihlášení</Link>
      </p>
    </div>
  );
}
