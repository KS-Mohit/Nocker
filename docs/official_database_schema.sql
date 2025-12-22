--
-- LinkedIn Job Application Agent - Official Database Schema
-- PostgreSQL database dump (Generated from production database)
-- This is the EXACT schema - run this file to replicate the entire database
--

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: applications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.applications (
    id integer NOT NULL,
    user_id integer,
    job_id integer,
    status character varying DEFAULT 'pending'::character varying,
    cover_letter text,
    resume_used character varying,
    form_responses jsonb,
    applied_at timestamp without time zone,
    error_message text,
    screenshot_path character varying,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);


ALTER TABLE public.applications OWNER TO postgres;

--
-- Name: applications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.applications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.applications_id_seq OWNER TO postgres;

--
-- Name: applications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.applications_id_seq OWNED BY public.applications.id;


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jobs (
    id integer NOT NULL,
    user_id integer,
    url character varying NOT NULL,
    title character varying,
    company character varying,
    location character varying,
    job_type character varying,
    workplace_type character varying,
    description text,
    requirements text,
    status character varying DEFAULT 'pending'::character varying,
    scraped_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);


ALTER TABLE public.jobs OWNER TO postgres;

--
-- Name: jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.jobs_id_seq OWNER TO postgres;

--
-- Name: jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.jobs_id_seq OWNED BY public.jobs.id;


--
-- Name: knowledge_base; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.knowledge_base (
    id integer NOT NULL,
    user_id integer,
    full_name character varying,
    email character varying,
    phone character varying,
    location character varying,
    linkedin_url character varying,
    portfolio_url character varying,
    summary text,
    work_experience jsonb,
    education jsonb,
    skills jsonb,
    certifications jsonb,
    projects jsonb,
    preferences jsonb,
    qa_pairs jsonb,
    resume_path character varying,
    cover_letter_template text,
    embedding_id character varying,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);


ALTER TABLE public.knowledge_base OWNER TO postgres;

--
-- Name: knowledge_base_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.knowledge_base_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.knowledge_base_id_seq OWNER TO postgres;

--
-- Name: knowledge_base_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.knowledge_base_id_seq OWNED BY public.knowledge_base.id;


--
-- Name: response_evaluations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.response_evaluations (
    id integer NOT NULL,
    token_usage_id integer NOT NULL,
    user_id integer NOT NULL,
    relevance_score double precision,
    accuracy_score double precision,
    completeness_score double precision,
    conciseness_score double precision,
    professionalism_score double precision,
    overall_score double precision NOT NULL,
    evaluation_method character varying(50) NOT NULL,
    evaluator_notes text,
    expected_answer text,
    needs_improvement boolean DEFAULT false,
    is_hallucination boolean DEFAULT false,
    is_inappropriate boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.response_evaluations OWNER TO postgres;

--
-- Name: TABLE response_evaluations; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.response_evaluations IS 'Quality evaluations of AI-generated responses';


--
-- Name: COLUMN response_evaluations.overall_score; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.response_evaluations.overall_score IS 'Overall quality score (1-5 scale)';


--
-- Name: COLUMN response_evaluations.evaluation_method; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.response_evaluations.evaluation_method IS 'How evaluation was done: manual, auto_llm, auto_keyword, auto_similarity';


--
-- Name: response_evaluations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.response_evaluations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.response_evaluations_id_seq OWNER TO postgres;

--
-- Name: response_evaluations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.response_evaluations_id_seq OWNED BY public.response_evaluations.id;


--
-- Name: token_usage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.token_usage (
    id integer NOT NULL,
    user_id integer NOT NULL,
    job_id integer,
    application_id integer,
    operation_type character varying(100) NOT NULL,
    endpoint character varying(255),
    model_name character varying(100) DEFAULT 'llama3'::character varying NOT NULL,
    prompt_tokens integer DEFAULT 0 NOT NULL,
    completion_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer DEFAULT 0 NOT NULL,
    rag_used character varying(10) DEFAULT 'false'::character varying,
    rag_chunks_retrieved integer,
    context_length integer,
    response_time_ms double precision,
    success character varying(10) DEFAULT 'true'::character varying NOT NULL,
    error_message text,
    estimated_cost double precision DEFAULT 0.0,
    extra_metadata jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    prompt_text text,
    completion_text text
);


ALTER TABLE public.token_usage OWNER TO postgres;

--
-- Name: TABLE token_usage; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.token_usage IS 'Tracks token usage for all AI operations';


--
-- Name: COLUMN token_usage.operation_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.token_usage.operation_type IS 'Type of operation: chat, rag_answer, cover_letter, resume_parse, question_answer, etc.';


--
-- Name: COLUMN token_usage.rag_used; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.token_usage.rag_used IS 'Whether RAG was used: true/false';


--
-- Name: COLUMN token_usage.success; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.token_usage.success IS 'Whether operation succeeded: true/false';


--
-- Name: COLUMN token_usage.estimated_cost; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.token_usage.estimated_cost IS 'Estimated cost in USD (0 for Ollama)';


--
-- Name: token_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.token_usage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.token_usage_id_seq OWNER TO postgres;

--
-- Name: token_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.token_usage_id_seq OWNED BY public.token_usage.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying NOT NULL,
    hashed_password character varying NOT NULL,
    full_name character varying,
    is_active boolean DEFAULT true,
    is_superuser boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: applications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.applications ALTER COLUMN id SET DEFAULT nextval('public.applications_id_seq'::regclass);


--
-- Name: jobs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs ALTER COLUMN id SET DEFAULT nextval('public.jobs_id_seq'::regclass);


--
-- Name: knowledge_base id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_base ALTER COLUMN id SET DEFAULT nextval('public.knowledge_base_id_seq'::regclass);


--
-- Name: response_evaluations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.response_evaluations ALTER COLUMN id SET DEFAULT nextval('public.response_evaluations_id_seq'::regclass);


--
-- Name: token_usage id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.token_usage ALTER COLUMN id SET DEFAULT nextval('public.token_usage_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: applications applications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: knowledge_base knowledge_base_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_base
    ADD CONSTRAINT knowledge_base_pkey PRIMARY KEY (id);


--
-- Name: response_evaluations response_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.response_evaluations
    ADD CONSTRAINT response_evaluations_pkey PRIMARY KEY (id);


--
-- Name: token_usage token_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_response_eval_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_response_eval_created ON public.response_evaluations USING btree (created_at DESC);


--
-- Name: idx_response_eval_method; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_response_eval_method ON public.response_evaluations USING btree (evaluation_method);


--
-- Name: idx_response_eval_overall_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_response_eval_overall_score ON public.response_evaluations USING btree (overall_score);


--
-- Name: idx_response_eval_token_usage; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_response_eval_token_usage ON public.response_evaluations USING btree (token_usage_id);


--
-- Name: idx_response_eval_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_response_eval_user ON public.response_evaluations USING btree (user_id);


--
-- Name: idx_token_usage_application_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_application_id ON public.token_usage USING btree (application_id);


--
-- Name: idx_token_usage_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_created_at ON public.token_usage USING btree (created_at DESC);


--
-- Name: idx_token_usage_extra_metadata; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_extra_metadata ON public.token_usage USING gin (extra_metadata);


--
-- Name: idx_token_usage_job_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_job_id ON public.token_usage USING btree (job_id);


--
-- Name: idx_token_usage_operation_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_operation_type ON public.token_usage USING btree (operation_type);


--
-- Name: idx_token_usage_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_user_created ON public.token_usage USING btree (user_id, created_at DESC);


--
-- Name: idx_token_usage_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_token_usage_user_id ON public.token_usage USING btree (user_id);


--
-- Name: applications applications_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: applications applications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: jobs jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: knowledge_base knowledge_base_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_base
    ADD CONSTRAINT knowledge_base_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: response_evaluations response_evaluations_token_usage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.response_evaluations
    ADD CONSTRAINT response_evaluations_token_usage_id_fkey FOREIGN KEY (token_usage_id) REFERENCES public.token_usage(id) ON DELETE CASCADE;


--
-- Name: response_evaluations response_evaluations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.response_evaluations
    ADD CONSTRAINT response_evaluations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: token_usage token_usage_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE SET NULL;


--
-- Name: token_usage token_usage_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE SET NULL;


--
-- Name: token_usage token_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.token_usage
    ADD CONSTRAINT token_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--
