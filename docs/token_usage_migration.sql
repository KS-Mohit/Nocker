-- Token Usage Table Migration

-- Create token_usage table
CREATE TABLE IF NOT EXISTS token_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    application_id INTEGER REFERENCES applications(id) ON DELETE SET NULL,
    
    -- Operation details
    operation_type VARCHAR(100) NOT NULL,
    endpoint VARCHAR(255),
    model_name VARCHAR(100) NOT NULL DEFAULT 'llama3',
    
    -- Token counts
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    
    -- Context information
    rag_used VARCHAR(10) DEFAULT 'false',
    rag_chunks_retrieved INTEGER,
    context_length INTEGER,
    
    -- Performance metrics
    response_time_ms DOUBLE PRECISION,
    success VARCHAR(10) NOT NULL DEFAULT 'true',
    error_message TEXT,
    
    -- Cost tracking
    estimated_cost DOUBLE PRECISION DEFAULT 0.0,
    
    -- Additional metadata
    extra_metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_token_usage_user_id ON token_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_job_id ON token_usage(job_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_application_id ON token_usage(application_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_operation_type ON token_usage(operation_type);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_token_usage_user_created ON token_usage(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_token_usage_extra_metadata ON token_usage USING GIN (extra_metadata);

-- Add comments for documentation
COMMENT ON TABLE token_usage IS 'Tracks token usage for all AI operations';
COMMENT ON COLUMN token_usage.operation_type IS 'Type of operation: chat, rag_answer, cover_letter, resume_parse, question_answer, etc.';
COMMENT ON COLUMN token_usage.rag_used IS 'Whether RAG was used: true/false';
COMMENT ON COLUMN token_usage.success IS 'Whether operation succeeded: true/false';
COMMENT ON COLUMN token_usage.estimated_cost IS 'Estimated cost in USD (0 for Ollama)';
COMMENT ON COLUMN token_usage.metadata IS 'Additional metadata in JSON format';