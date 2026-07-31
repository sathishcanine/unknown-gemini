-- Track which practice batch a session belongs to.
ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS batch VARCHAR(100);

-- Backfill from answered practice questions (most common batch per session).
UPDATE test_sessions ts
SET batch = src.batch
FROM (
    SELECT
        ua.session_id,
        MODE() WITHIN GROUP (ORDER BY NULLIF(TRIM(q.batch), '')) AS batch
    FROM user_answers ua
    JOIN questions q ON q.id = ua.question_id
    WHERE LOWER(COALESCE(q.type, '')) <> 'pyq'
      AND NULLIF(TRIM(q.batch), '') IS NOT NULL
    GROUP BY ua.session_id
) src
WHERE ts.id = src.session_id
  AND (ts.batch IS NULL OR TRIM(ts.batch) = '');
