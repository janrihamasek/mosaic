import React, { useCallback, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { styles } from '../styles/common';
import { formatError } from '../utils/errors';
import {
  selectActivitiesState,
  selectAllActivities,
  activateActivity,
  deactivateActivity,
  removeActivity,
  loadActivities,
} from '../store/activitiesSlice';
import Loading from './Loading';
import ErrorState from './ErrorState';
import DataTable from './shared/DataTable';

export default function ActivityTable({ onNotify, onOpenDetail }) {
  const dispatch = useDispatch();
  const { status, error } = useSelector(selectActivitiesState);
  const activities = useSelector(selectAllActivities);
  const [actionId, setActionId] = useState(null);
  const loading = status === 'loading';
  const refreshing = loading && activities.length > 0;
  const resolveRowStyle = useCallback(
    (activity) => (activity.activity_type === 'negative' ? styles.negativeRow : styles.positiveRow),
    []
  );

  const sortedActivities = useMemo(() => {
    return [...activities].sort((a, b) => {
      if (a.active !== b.active) {
        return a.active ? -1 : 1;
      }
      const catCompare = (a.category || '').localeCompare(b.category || '', undefined, {
        sensitivity: 'base',
      });
      if (catCompare !== 0) {
        return catCompare;
      }
      return (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' });
    });
  }, [activities]);

  const handleAction = useCallback(
    async (thunk, id, successMessage, errorVerb) => {
      if (!id) return;
      setActionId(id);
      try {
        await dispatch(thunk(id)).unwrap();
        onNotify?.(successMessage, 'success');
      } catch (err) {
        onNotify?.(`Failed to ${errorVerb}: ${formatError(err)}`, 'error');
      } finally {
        setActionId(null);
      }
    },
    [dispatch, onNotify]
  );

  const actionCellStyle = useMemo(
    () => ({
      display: 'flex',
      gap: '0.5rem',
      flexWrap: 'wrap',
      justifyContent: 'flex-end',
    }),
    []
  );

  const columns = useMemo(
    () => [
      {
        key: 'name',
        label: 'Activity',
        width: '25%',
        render: (activity) => (
          <span
            style={{ cursor: 'pointer', textDecoration: 'underline' }}
            title={activity.category ? `Category: ${activity.category}` : 'Category: N/A'}
            onClick={(event) => {
              event.stopPropagation();
              onOpenDetail?.(activity);
            }}
          >
            {activity.name}
          </span>
        ),
      },
      {
        key: 'category',
        label: 'Category',
        width: '20%',
        render: (activity) => activity.category || 'N/A',
      },
      {
        key: 'goal',
        label: 'Goal',
        width: '15%',
        render: (activity) =>
          activity.activity_type === 'negative'
            ? '0.00'
            : typeof activity.goal === 'number'
              ? activity.goal.toFixed(2)
              : Number(activity.goal ?? 0).toFixed(2),
      },
      {
        key: 'activity_type',
        label: 'Type',
        width: '10%',
        render: (activity) => (activity.activity_type === 'negative' ? 'Negative' : 'Positive'),
      },
      {
        key: 'status',
        label: 'Status',
        width: '10%',
        render: (activity) => (activity.active ? 'Active' : 'Inactive'),
      },
      {
        key: 'actions',
        label: 'Actions',
        width: '20%',
        render: (activity) => {
          const disabled = actionId === activity.id;
          if (activity.active) {
            return (
              <div style={actionCellStyle}>
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    handleAction(deactivateActivity, activity.id, 'Activity deactivated', 'deactivate activity');
                  }}
                  style={{
                    ...styles.button,
                    backgroundColor: '#8b1e3f',
                    opacity: disabled ? 0.6 : 1,
                  }}
                  disabled={disabled}
                >
                  {disabled ? 'Working...' : 'Deactivate'}
                </button>
              </div>
            );
          }

          return (
            <div style={actionCellStyle}>
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  handleAction(activateActivity, activity.id, 'Activity activated', 'activate activity');
                }}
                style={{
                  ...styles.button,
                  backgroundColor: '#29442f',
                  opacity: disabled ? 0.6 : 1,
                }}
                disabled={disabled}
              >
                {disabled ? 'Working...' : 'Activate'}
              </button>
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  handleAction(removeActivity, activity.id, 'Activity was deleted', 'delete activity');
                }}
                style={{
                  ...styles.button,
                  backgroundColor: '#8b1e3f',
                  opacity: disabled ? 0.6 : 1,
                }}
                disabled={disabled}
              >
                {disabled ? 'Working...' : 'Delete'}
              </button>
            </div>
          );
        },
      },
    ],
    [actionCellStyle, actionId, handleAction, onOpenDetail]
  );

  if (status === 'failed') {
    const message = error?.friendlyMessage || error?.message || 'Failed to load activities.';
    return (
      <ErrorState
        message={message}
        onRetry={() => dispatch(loadActivities())}
        actionLabel="Retry load"
      />
    );
  }

  const isInitialLoading = loading && activities.length === 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {refreshing && <Loading message="Refreshing activities…" inline />}
      <DataTable
        columns={columns}
        data={sortedActivities}
        isLoading={isInitialLoading}
        loadingMessage="Loading activities…"
        emptyMessage="No activities to display."
        rowStyle={resolveRowStyle}
      />
    </div>
  );
}
