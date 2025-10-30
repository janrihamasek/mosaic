import { useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useForm } from 'react-hook-form';
import { styles } from '../styles/common';
import { formatError } from '../utils/errors';
import { createActivity, selectActivitiesState } from '../store/activitiesSlice';
import { useCompactLayout } from '../utils/useBreakpoints';

const errorTextStyle = { color: '#f28b82', fontSize: 12 };
const buildInputStyle = (hasError, overrides) => ({
  ...styles.input,
  border: hasError ? '1px solid #d93025' : styles.input.border,
  ...(overrides || {}),
});

const defaultValues = {
  name: '',
  category: '',
  frequencyPerDay: 1,
  frequencyPerWeek: 1,
  description: '',
};

export default function ActivityForm({ onNotify }) {
  const dispatch = useDispatch();
  const { mutationStatus } = useSelector(selectActivitiesState);
  const isSaving = mutationStatus === 'loading';
  const { isMobile, isCompact } = useCompactLayout();
  const fieldWrapperStyle = { display: 'flex', flexDirection: 'column', gap: 4 };
  const formStyle = {
    ...styles.form,
    flexDirection: 'column',
    gap: isCompact ? '0.75rem' : '1rem',
  };
  const frequencySectionStyle = {
    display: 'grid',
    gridTemplateColumns: isCompact ? '1fr' : 'repeat(auto-fit, minmax(9rem, 1fr))',
    gap: '0.75rem',
    alignItems: 'flex-start',
  };

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isValid, isSubmitting },
  } = useForm({
    mode: 'onChange',
    defaultValues,
  });

  const frequencyPerDay = watch('frequencyPerDay');
  const frequencyPerWeek = watch('frequencyPerWeek');

  const avgGoalPerDay = useMemo(() => {
    const perDay = Number(frequencyPerDay) || 0;
    const perWeek = Number(frequencyPerWeek) || 0;
    return (perDay * perWeek) / 7;
  }, [frequencyPerDay, frequencyPerWeek]);

  const onSubmit = async (data) => {
    if (isSaving) return;
    try {
      // Backend derives `goal` server-side; avoid sending it because the schema forbids extra fields.
      await dispatch(
        createActivity({
          name: data.name.trim(),
          category: data.category.trim(),
          frequency_per_day: Number(data.frequencyPerDay),
          frequency_per_week: Number(data.frequencyPerWeek),
          description: data.description.trim(),
        })
      ).unwrap();
      onNotify?.('Activity was created', 'success');
      reset(defaultValues);
    } catch (err) {
      onNotify?.(`Failed to create activity: ${formatError(err)}`, 'error');
    }
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      style={formStyle}
    >
      <div style={fieldWrapperStyle}>
        <input
          type="text"
          placeholder="Activity"
          {...register('name', {
            required: 'Activity name is required.',
            minLength: { value: 2, message: 'Activity name must be at least 2 characters.' },
            maxLength: { value: 80, message: 'Activity name must be at most 80 characters.' },
            validate: (value) => value.trim().length > 0 || 'Activity name cannot be empty.',
          })}
          style={buildInputStyle(!!errors.name)}
          aria-invalid={errors.name ? 'true' : 'false'}
        />
        {errors.name && <span style={errorTextStyle}>{errors.name.message}</span>}
      </div>

      <div style={fieldWrapperStyle}>
        <input
          type="text"
          placeholder="Category"
          {...register('category', {
            required: 'Category is required.',
            minLength: { value: 2, message: 'Category must be at least 2 characters.' },
            maxLength: { value: 80, message: 'Category must be at most 80 characters.' },
            validate: (value) => value.trim().length > 0 || 'Category cannot be empty.',
          })}
          style={buildInputStyle(!!errors.category)}
          aria-invalid={errors.category ? 'true' : 'false'}
        />
        {errors.category && <span style={errorTextStyle}>{errors.category.message}</span>}
      </div>

      <div style={fieldWrapperStyle}>
        <input
          type="text"
          placeholder="Description (optional)"
          {...register('description', {
            maxLength: { value: 240, message: 'Description must be at most 240 characters.' },
          })}
          style={buildInputStyle(!!errors.description)}
          aria-invalid={errors.description ? 'true' : 'false'}
        />
        {errors.description && <span style={errorTextStyle}>{errors.description.message}</span>}
      </div>

      <div style={frequencySectionStyle}>
        <label style={{ ...fieldWrapperStyle, fontSize: 13 }}>
          <span>Per day</span>
          <select
            {...register('frequencyPerDay', {
              valueAsNumber: true,
              required: 'Select frequency per day.',
              min: { value: 1, message: 'Minimum is 1 per day.' },
              max: { value: 3, message: 'Maximum is 3 per day.' },
            })}
            style={buildInputStyle(!!errors.frequencyPerDay, { width: '100%' })}
            aria-invalid={errors.frequencyPerDay ? 'true' : 'false'}
          >
            {[1, 2, 3].map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
            {errors.frequencyPerDay && (
              <span style={errorTextStyle}>{errors.frequencyPerDay.message}</span>
          )}
        </label>

        <label style={{ ...fieldWrapperStyle, fontSize: 13 }}>
          <span>Per week</span>
          <select
            {...register('frequencyPerWeek', {
              valueAsNumber: true,
              required: 'Select frequency per week.',
              min: { value: 1, message: 'Minimum is 1 per week.' },
              max: { value: 7, message: 'Maximum is 7 per week.' },
            })}
            style={buildInputStyle(!!errors.frequencyPerWeek, { width: '100%' })}
            aria-invalid={errors.frequencyPerWeek ? 'true' : 'false'}
          >
            {[1, 2, 3, 4, 5, 6, 7].map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
            {errors.frequencyPerWeek && (
              <span style={errorTextStyle}>{errors.frequencyPerWeek.message}</span>
          )}
        </label>

        <div style={{ ...fieldWrapperStyle, justifyContent: 'flex-end', fontSize: 13 }}>
          <span style={{ fontWeight: 600 }}>Avg/day</span>
          <span>{avgGoalPerDay.toFixed(2)}</span>
        </div>
      </div>

      <button
        type="submit"
        style={{
          ...styles.button,
          ...(isMobile ? styles.buttonMobile : {}),
          opacity: isSaving || isSubmitting || !isValid ? 0.7 : 1,
          cursor: isSaving || isSubmitting || !isValid ? 'not-allowed' : styles.button.cursor,
        }}
        disabled={isSaving || isSubmitting || !isValid}
      >
        {isSaving || isSubmitting ? 'Saving...' : 'Enter'}
      </button>
    </form>
  );
}
