import React, { useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { styles } from '../styles/common';
import { formatError } from '../utils/errors';
import {
  selectActivitiesState,
  selectAllActivities,
  activateActivity,
  deactivateActivity,
  removeActivity,
} from '../store/activitiesSlice';

export default function ActivityTable({ onNotify, onOpenDetail }) {
  const dispatch = useDispatch();
  const { status } = useSelector(selectActivitiesState);
  const activities = useSelector(selectAllActivities);
  const [actionId, setActionId] = useState(null);
  const loading = status === 'loading';

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

  return (
    <div>
      {loading && <div style={styles.loadingText}>⏳ Loading activities...</div>}

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
                style={{ cursor: 'pointer', textDecoration: 'underline', width: '20%' }}
                title={activity.category ? `Category: ${activity.category}` : 'Category: N/A'}
                onClick={() => onOpenDetail?.(activity)}
              >
                {activity.name}
              </td>
              <td style={{ width: '20%' }}>{activity.category || 'N/A'}</td>
              <td style={{ width: '10%' }}>
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
                      width: '100%',
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
                        width: '50%',
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
                        width: '50%',
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
              <td colSpan={6} style={{ padding: '12px', color: '#888' }}>
                No activities to display.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
