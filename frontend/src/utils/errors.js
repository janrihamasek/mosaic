export function formatError(error, fallback = 'Došlo k chybě') {
  if (!error) return fallback;
  if (error.friendlyMessage) return error.friendlyMessage;
  if (error.code && error.message) return error.message;
  if (error.message) return error.message;
  return fallback;
}
