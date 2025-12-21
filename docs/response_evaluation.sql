-- Response Evaluation Table Migration

CREATE TABLE IF NOT EXISTS response_evaluations (
    id SERIAL PRIMARY KEY,
    token_usage_id INTEGER NOT NULL REFERENCES token_usage(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Scores (1-5 scale)
    relevance_score DOUBLE PRECISION,
    accuracy_score DOUBLE PRECISION,
    completeness_score DOUBLE PRECISION,
    conciseness_score DOUBLE PRECISION,
    professionalism_score DOUBLE PRECISION,
    overall_score DOUBLE PRECISION NOT NULL,
    
    -- Evaluation metadata
    evaluation_method VARCHAR(50) NOT NULL,
    evaluator_notes TEXT,
    expected_answer TEXT,
    
    -- Quality flags
    needs_improvement BOOLEAN DEFAULT FALSE,
    is_hallucination BOOLEAN DEFAULT FALSE,
    is_inappropriate BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_response_eval_token_usage ON response_evaluations(token_usage_id);
CREATE INDEX IF NOT EXISTS idx_response_eval_user ON response_evaluations(user_id);
CREATE INDEX IF NOT EXISTS idx_response_eval_overall_score ON response_evaluations(overall_score);
CREATE INDEX IF NOT EXISTS idx_response_eval_method ON response_evaluations(evaluation_method);
CREATE INDEX IF NOT EXISTS idx_response_eval_created ON response_evaluations(created_at DESC);

-- Comments
COMMENT ON TABLE response_evaluations IS 'Quality evaluations of AI-generated responses';
COMMENT ON COLUMN response_evaluations.evaluation_method IS 'How evaluation was done: manual, auto_llm, auto_keyword, auto_similarity';
COMMENT ON COLUMN response_evaluations.overall_score IS 'Overall quality score (1-5 scale)';