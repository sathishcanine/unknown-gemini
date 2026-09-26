-- Learn Mode shared tip/trick cards (precomputed for all users)
ALTER TABLE questions ADD COLUMN IF NOT EXISTS learning_tip TEXT DEFAULT '';
ALTER TABLE questions ADD COLUMN IF NOT EXISTS learning_tip_ta TEXT DEFAULT '';
ALTER TABLE questions ADD COLUMN IF NOT EXISTS exam_trick TEXT DEFAULT '';
ALTER TABLE questions ADD COLUMN IF NOT EXISTS exam_trick_ta TEXT DEFAULT '';
