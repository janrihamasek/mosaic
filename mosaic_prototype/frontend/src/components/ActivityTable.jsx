import React, { useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { styles } from '../styles/common';
import { formatError } from '../utils/errors';
import { useCompactLayout } from '../utils/useBreakpoints';
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

export default function ActivityTable({ onNotify, onOpenDetail }) {
  const dispatch = useDispatch();
  const { status, error } = useSelector(selectActivitiesState);
  const activities = useSelector(selectAllActivities);
  const [actionId, setActionId] = useState(null);
  const loading = status === 'loading';
  const refreshing = loading && activities.length > 0;
  const { isCompact } = useCompactLayout();

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

  const handleAction = async (thunk, id, successMessage, errorVerb) => {
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
  };

  const activityCardBase = {
    ...styles.card,
    margin: 0,
    padding: '1rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  };

  const actionButtonBase = {
    ...styles.button,
    width: isCompact ? '100%' : 'auto',
  };

  const inactiveButtonGroupStyle = {
    display: 'grid',
    gap: '0.5rem',
    gridTemplateColumns: isCompact ? '1fr' : 'repeat(2, minmax(0, 1fr))',
  };

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

  if (loading && activities.length === 0) {
    return <Loading message="Loading activities…" />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {refreshing && <Loading message="Refreshing activities…" inline />}

      {isCompact ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {sortedActivities.map((activity) => (
            <div key={activity.id} style={activityCardBase}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span
                  style={{ fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' }}
                  onClick={() => onOpenDetail?.(activity)}
                  title={activity.category ? `Category: ${activity.category}` : 'Category: N/A'}
                >
                  {activity.name}
                </span>
                <span style={{ ...styles.textMuted, fontSize: '0.8125rem' }}>
                  {activity.active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', fontSize: '0.875rem', color: '#c5ccd6' }}>
                <span>Category: {activity.category || 'N/A'}</span>
                <span>
                  Goal:{' '}
                  {typeof activity.goal === 'number'
                    ? activity.goal.toFixed(2)
                    : Number(activity.goal ?? 0).toFixed(2)}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {activity.active ? (
                  <button
                    onClick={() =>
                      handleAction(deactivateActivity, activity.id, 'Activity deactivated', 'deactivate activity')
                    }
                    style={{
                      ...actionButtonBase,
                      backgroundColor: '#8b1e3f',
                      opacity: actionId === activity.id ? 0.6 : 1,
                    }}
                    disabled={actionId === activity.id}
                  >
                    {actionId === activity.id ? 'Working...' : 'Deactivate'}
                  </button>
                ) : (
                  <div style={inactiveButtonGroupStyle}>
                    <button
                      onClick={() =>
                        handleAction(activateActivity, activity.id, 'Activity activated', 'activate activity')
                      }
                      style={{
                        ...actionButtonBase,
                        backgroundColor: '#29442f',
                        opacity: actionId === activity.id ? 0.6 : 1,
                      }}
                      disabled={actionId === activity.id}
                    >
                      {actionId === activity.id ? 'Working...' : 'Activate'}
                    </button>
                    <button
                      onClick={() =>
                        handleAction(removeActivity, activity.id, 'Activity was deleted', 'delete activity')
                      }
                      style={{
                        ...actionButtonBase,
                        backgroundColor: '#8b1e3f',
                        opacity: actionId === activity.id ? 0.6 : 1,
                      }}
                      disabled={actionId === activity.id}
                    >
                      {actionId === activity.id ? 'Working...' : 'Delete'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
          {!loading && sortedActivities.length === 0 && (
            <div style={{ ...styles.card, margin: 0, padding: '1rem', color: '#9ba3af', fontStyle: 'italic' }}>
              No activities to display.
            </div>
          )}
        </div>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr style={styles.tableHeader}>
              <th>Activity</th>
              <th>Category</th>
              <th>Goal</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sortedActivities.map((activity) => (
              <tr key={activity.id} style={styles.tableRow}>
                <td
                  style={{ cursor: 'pointer', textDecoration: 'underline', width: '25%' }}
                  title={activity.category ? `Category: ${activity.category}` : 'Category: N/A'}
                  onClick={() => onOpenDetail?.(activity)}
                >
                  {activity.name}
                </td>
                <td style={{ width: '20%' }}>{activity.category || 'N/A'}</td>
                <td style={{ width: '15%' }}>
                  {typeof activity.goal === 'number'
                    ? activity.goal.toFixed(2)
                    : Number(activity.goal ?? 0).toFixed(2)}
                </td>
                <td style={{ width: '10%' }}>{activity.active ? 'Active' : 'Inactive'}</td>
                <td style={{ ...styles.tableCellActions }}>
                  {activity.active ? (
                    <button
                      onClick={() =>
                        handleAction(deactivateActivity, activity.id, 'Activity deactivated', 'deactivate activity')
                      }
                      style={{
                        ...styles.button,
                        backgroundColor: '#8b1e3f',
                        opacity: actionId === activity.id ? 0.6 : 1,
                      }}
                      disabled={actionId === activity.id}
                    >
                      {actionId === activity.id ? 'Working...' : 'Deactivate'}
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() =>
                          handleAction(activateActivity, activity.id, 'Activity activated', 'activate activity')
                        }
                        style={{
                          ...styles.button,
                          backgroundColor: '#29442f',
                          width: '48%',
                          opacity: actionId === activity.id ? 0.6 : 1,
                        }}
                        disabled={actionId === activity.id}
                      >
                        {actionId === activity.id ? 'Working...' : 'Activate'}
                      </button>
                      <button
                        onClick={() =>
                          handleAction(removeActivity, activity.id, 'Activity was deleted', 'delete activity')
                        }
                        style={{
                          ...styles.button,
                          backgroundColor: '#8b1e3f',
                          width: '48%',
                          opacity: actionId === activity.id ? 0.6 : 1,
                        }}
                        disabled={actionId === activity.id}
                      >
                        {actionId === activity.id ? 'Working...' : 'Delete'}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {!loading && sortedActivities.length === 0 && (
              <tr>
                <td colSpan={5} style={{ padding: '0.75rem', color: '#9ba3af', fontStyle: 'italic' }}>
                  No activities to display.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
