/**
 * Result helpers for deterministic error handling.
 */
export type Result<T, E> =
  | { readonly ok: true; readonly value: T }
  | { readonly ok: false; readonly error: E };

/**
 * Wrap a successful value.
 */
export const ok = <T>(value: T): Result<T, never> => ({
  ok: true,
  value
});

/**
 * Wrap an error value.
 */
export const err = <E>(error: E): Result<never, E> => ({
  ok: false,
  error
});
